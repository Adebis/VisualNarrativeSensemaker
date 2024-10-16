import os
import sqlite3
import json
from sqlite3 import Error
from timeit import default_timer as timer
import random
import csv
import pickle
import sys
from collections import OrderedDict
import cv2
from skimage.metrics import structural_similarity
from dataclasses import dataclass

from knowledge_graph.graph import KnowledgeGraph
from commonsense.commonsense_data import Synset, CommonSenseNode, CommonSenseEdge
from commonsense.cskg_querier import CommonSenseQuerier, CSKGQuerier
from input_handling.scene_graph_reader import SceneGraphReader

import constants as const
from constants import CausalFlowDirection

from image_set_generation.links import CausalLink, MultiCausalLink, ActionLink
from image_set_generation.items import (ActionConcept, ObjectConcept, 
                                        CommonSenseNodeCluster,
                                        ActionInstance, ObjectInstance,
                                        ImageInstance, ActionObjectPair)
from image_set_generation.data_handler import DataHandler

from openai import OpenAI
import base64
import requests

class ImageSetGenerator:
    """
    Handles image set generation.

    Attributes
    ----------
    _commonsense_querier : CommonSenseQuerier
        A CommonSenseQuerier for interacting with commonsense data. 
        Initialization of a CommonSenseQuerier takes some time. 
    """

    # For handling the generator's caches.
    _data_handler: DataHandler

    _annotations_directory: str
    _images_directory: str
    _causal_links_directory: str

    def __init__(self, annotations_directory: str,
                 images_directory: str,
                 load_caches = True):
        print("Initializing image set generator.")
        self._causal_links_directory = 'C:/Users/zevsm/Documents/GitHub/VisualNarrativeSensemaker/data/inputs/causal_links'
        self._data_handler = DataHandler(load_caches=load_caches)

        #self._commonsense_querier = CSKGQuerier()
        #self._scene_graph_reader = SceneGraphReader(self._commonsense_querier)
        self._database_file_path = (f'{const.DATA_DIRECTORY}/image_set_generation.db')
        self._images_directory = images_directory
        self._annotations_directory = annotations_directory

    # end __init__

    def generate_object_linked_image_sets(self, number_to_generate: int):
        '''
        Generates image sets where each image in the set shares two
        action-connected objects with the other two images in the set. 

        Outputs a list of image sets, where each image set is a list of three
        image ids. 
        '''
        print('Generating object linked image sets.')
        # Seed to get the same random sets each time.
        random.seed(10)
        image_sets = list()
        used_image_ids = set()

        # Get the ids of all image that have an object paired with an action.
        # There are ~70,000 of these
        query = ('''
            SELECT DISTINCT image_id FROM image_action_object_pairs
        ''')
        unused_image_ids = [result[0] for result in self._execute_query(query)]

        # Randomly choose a starting image id that hasn't already been used.
        # Make sets until we've made the number we want to generate.
        start_time = timer()
        while len(image_sets) < number_to_generate:
            image_id_1 = random.choice(unused_image_ids)

            # Get all the objects paired with actions for this image. 
            pairs_1 = self._data_handler.get_image_action_object_pairs(image_id_1)
            # Get all the unique paired object concept ids for this image.
            object_concept_ids_1 = {pair.object_concept_id for pair in pairs_1}

            # Now we need to get two more images such that every image has two
            # objects paired with actions which appear in the other two images
            # in some combination. 
            image_set_found = False
            for object_concept_id_1 in object_concept_ids_1:
                # Count how many objects each image matches with the other images.
                image_1_match_count = 0
                # Get the id of every image that has this object concept id
                # as part of an action-object pair.
                query = ('''
                    SELECT DISTINCT image_id FROM image_action_object_pairs
                    WHERE object_concept_id = ?
                ''')
                rows = self._execute_query(query, [object_concept_id_1])
                object_1_paired_image_ids = set(row[0] for row in rows)
                # Go through them one at a time.
                for image_id_2 in object_1_paired_image_ids:
                    if image_id_2 == image_id_1:
                        continue
                    if image_id_2 in used_image_ids:
                        continue
                    image_2_match_count = 0
                    # Get all of this image's action object pairs.
                    pairs_2 = self._data_handler.get_image_action_object_pairs(image_id_2)
                    # Get all the unique paired object concept ids for this image.
                    object_concept_ids_2 = {pair.object_concept_id for pair in pairs_2}
                    # See how many of them overlap. 
                    image_2_match_count = len(object_concept_ids_1.intersection(object_concept_ids_2))
                    image_1_match_count = image_2_match_count
                    # If there are no overlapping objects, go on to the next 2nd image.
                    if image_2_match_count == 0:
                        continue
                    # Get a third image that overlaps with at least one of the
                    # objects that appears in either image 1 or 2.
                    object_concept_ids_1_2 = object_concept_ids_1.union(object_concept_ids_2)
                    for object_concept_id_1_2 in object_concept_ids_1_2:
                        query = ('''
                            SELECT DISTINCT image_id FROM image_action_object_pairs
                            WHERE object_concept_id = ?
                        ''')
                        rows = self._execute_query(query, [object_concept_id_1])
                        object_1_2_paired_image_ids = set(row[0] for row in rows)
                        for image_id_3 in object_1_2_paired_image_ids:
                            image_3_match_count = 0
                            # Don't repeat image ids.
                            if image_id_3 == image_id_1 or image_id_3 == image_id_2:
                                continue
                            if image_id_3 in used_image_ids:
                                continue
                            # Get all of this image's action object pairs.
                            pairs_3 = self._data_handler.get_image_action_object_pairs(image_id_3)
                            # Get all the unique paired object concept ids for this image.
                            object_concept_ids_3 = {pair.object_concept_id for pair in pairs_3}
                            # See how many of them overlap with image 1.
                            image_1_3_overlap = len(object_concept_ids_1.intersection(object_concept_ids_3))
                            image_3_match_count += image_1_3_overlap
                            image_1_match_count += image_1_3_overlap
                            # See how many of them overlap with image 2.
                            image_2_3_overlap = len(object_concept_ids_2.intersection(object_concept_ids_3))
                            image_3_match_count += image_2_3_overlap
                            image_2_match_count += image_2_3_overlap
                            # If all three images now have 2 overlapping objects
                            # with the other images, this is a valid set.
                            if (image_1_match_count >= 2
                                and image_2_match_count >= 2
                                and image_3_match_count >= 2):
                                image_set = [image_id_1, image_id_2, image_id_3]
                                image_sets.append(image_set)
                                # Remove these image ids from the set of
                                # unused image ids.
                                unused_image_ids.remove(image_id_1)
                                unused_image_ids.remove(image_id_2)
                                unused_image_ids.remove(image_id_3)
                                # Add them to the used image ids set.
                                used_image_ids.add(image_id_1)
                                used_image_ids.add(image_id_2)
                                used_image_ids.add(image_id_3)
                                image_set_found = True
                                break
                            # end if
                        # end for image_id_3
                        if image_set_found:
                            break
                    # end for object_concept_id_1_2
                    if image_set_found:
                        break
                # end for image_id_2
                if image_set_found:
                    break
            # end for object_concept_1

            if (len(image_sets) % 10 == 0):
                print(f'Sets left to generate: {number_to_generate - len(image_sets)}. '
                    + f'Elapsed time: {timer() - start_time}s. ' 
                    + f'Average time per image set: {(timer() - start_time)/len(image_sets)}s.')
            # end if
            
        # end while
        
        return image_sets
    # end generate_object_linked_image_sets

    def generate_image_sets(self, action_terms: list[str]):
        print("Generating image sets...")
        #all_image_sets = list()

        start_time = timer()
        # Get the cs node cluster for this URI.
        #cs_node_cluster = self._data_handler.get_cs_node_cluster(search_uri)

        image_sets = self._make_image_sets(
            action_terms=action_terms
        )
        #all_image_sets.extend(image_sets)
        print(f'Number of image sets: {len(image_sets)}.')

        # Write image sets out to the output file. 
        image_sets_str = ""
        for image_set in image_sets:
            for id in list(image_set):
                image_sets_str += str(id) + ','
            # end for
            image_sets_str = image_sets_str.rstrip(',')
            image_sets_str += '\n'
        # end for
        image_sets_str = image_sets_str.rstrip('\n')
        #image_sets_json = json.dumps([list(image_set) for image_set in image_sets])
        output_file_directory = const.DATA_DIRECTORY + '/inputs/image_sets/'
        output_file_name = 'image_sets'
        for action_term in action_terms:
            output_file_name += f'_{action_term}'
        # end for
        #output_file_name += f'_{number_of_sets_to_generate}'
        output_file_name += '.csv'

        output_file_path = output_file_directory + output_file_name
        with open(output_file_path, 'w') as output_file:
            output_file.write(image_sets_str)

        elapsed_time = timer() - start_time
        print(f'Done generating image sets for {action_terms}.'
                + f' Time taken: {elapsed_time}s.')
        return image_sets
    # end generate_image_sets 

    def _make_image_sets(self, action_terms: list[str]):
        '''
        Make image sets for a set of action terms.

        Each image set has one image for each term. 
        '''
        #print(f'Making image sets for causal link {causal_link}.')

        # Input: action 1, action 2 terms
        # cook, eat.
        term_1 = action_terms[0]
        term_2 = action_terms[1]
        # Get the third action if one was passed in.
        term_3 = None
        if len(action_terms) > 2:
            term_3 = action_terms[2]

        # Find triplets of images s.t.:
        #   Each action instance shares a subject/object with at least one
        #   of the other action instances. 
        # Prioritize images with fewer objects.

        # Issues:
        # There are some images where the object of the action isn't paired
        # with the action...
        # Buy images are sometimes about buying the finished food that you
        # then eat, rather than buying the food that you then cook and
        # eat. 

        # Make all action instances for action 1.
        # 56 action instances for buy
        # 11 subject concepts
        # 21 object concepts
        # 38 images
        action_instances_1, subject_map_1, object_map_1, image_map_1 = self._get_action_instances_and_maps(term_1)
        # Make a sorted dict of all the images by the number of objects in them.
        # Key: image id.
        # Value: number of object instances in the image.
        image_object_counts_1 = {image_id: self._data_handler.get_image_objects_count(image_id)
                                 for image_id in image_map_1.keys()}
        # Make a sorted dict of all the images by the number of actions in them.
        images_by_object_count_1 = dict(sorted(image_object_counts_1.items(), key=lambda item: item[1]))


        # Make all action instances for action 2.
        # 1862 action instances for cook
        # 335 subject concepts
        # 307 object concepts
        # 1226 images
        action_instances_2, subject_map_2, object_map_2, image_map_2 = self._get_action_instances_and_maps(term_2)
        # Make a sorted dict of all the images by the number of objects in them.
        # Key: image id.
        # Value: number of object instances in the image.
        image_object_counts_2 = {image_id: self._data_handler.get_image_objects_count(image_id)
                                 for image_id in image_map_2.keys()}
        images_by_object_count_2 = dict(sorted(image_object_counts_2.items(), key=lambda item: item[1]))

        # Make all action instances for action 3.
        # 7033 action instances for eat
        # 159 subject concepts
        # 195 object concepts
        # 3362 images
        # If there was a third action passed in.
        if term_3 is not None:
            action_instances_3, subject_map_3, object_map_3, image_map_3 = self._get_action_instances_and_maps(term_3)
            # Make a sorted dict of all the images by the number of objects in them.
            # Key: image id.
            # Value: number of object instances in the image.
            image_object_counts_3 = {image_id: self._data_handler.get_image_objects_count(image_id)
                                    for image_id in image_map_3.keys()}
            images_by_object_count_3 = dict(sorted(image_object_counts_3.items(), key=lambda item: item[1]))
        # If there wasn't a third action passed in.
        else:
            # Get all action 3's from all the actions causally linked to action 2.
            action_concept_2 = self._data_handler.get_action_concept(list(action_instances_2.values())[0].action_concept_id)
            # Get the instances of all actions forward causally linked with action 2.
            action_concept_ids_3 = action_concept_2.get_forward_linked_action_concept_ids()
            action_concepts_3 = [self._data_handler.get_action_concept(id)
                                for id in action_concept_ids_3]
            action_instances_3 = dict()
            for concept in action_concepts_3:
                action_instances_3.update(self._data_handler.get_action_instances_for_concept(concept))
            # end for
            subject_map_3, object_map_3, image_map_3 = self._get_action_maps(action_instances_3)
            image_object_counts_3 = {image_id: self._data_handler.get_image_objects_count(image_id)
                                    for image_id in image_map_3.keys()}
        # end else

        
        #action_instances_3, subject_map_3, object_map_3, image_map_3 = self._get_action_instances_and_maps(term_3)
        # Make a sorted dict of all the images by the number of objects in them.
        # Key: image id.
        # Value: number of object instances in the image.
        #image_object_counts_3 = {image_id: self._data_handler.get_image_objects_count(image_id)
        #                         for image_id in image_map_3.keys()}
        #images_by_object_count_3 = dict(sorted(image_object_counts_3.items(), key=lambda item: item[1]))

        # Figure the total number of image triplets there are.
        # 1,323,739 triplets. 
        number_of_sets = 0
        iteration_count = 0
        # List of lists of image ids.
        sets_to_make = 100
        image_ids_used = set()
        image_sets = list()
        # Pick the lowest object image for action image_1.
        for image_id_1 in images_by_object_count_1.keys():
            if image_id_1 in image_ids_used:
                continue
            actions_1 = [action_instances_1[id]
                         for id in image_map_1[image_id_1]]
            image_ids_2 = set()
            image_ids_3 = set()
            for action_1 in actions_1:
                # The best actions have a subject and an object.
                # If the action does not have an object, skip it.
                if action_1.object_concept_id is None:
                    continue

                # Get all the ids of image 2s with an action that shares this
                # subject.
                shared_subj_image_2_ids = set()
                if action_1.subject_concept_id in subject_map_2:
                    shared_subj_image_2_ids = set(subject_map_2[action_1.subject_concept_id].keys())
                # Get all the ids of images 2s with an action that shares this
                # object.
                shared_obj_image_2_ids = set()
                if action_1.object_concept_id in object_map_2:
                    shared_obj_image_2_ids = set(object_map_2[action_1.object_concept_id].keys())
                # See if there are any images that have both.
                shared_roles_image_2_ids = shared_subj_image_2_ids.intersection(shared_obj_image_2_ids)
                # If there are, add those as viable image 2s.
                if len(shared_roles_image_2_ids) > 0:
                    image_ids_2.update(shared_roles_image_2_ids)
                # If there are not, prioritize those that share an object.
                elif len(shared_obj_image_2_ids) > 0:
                    image_ids_2.update(shared_obj_image_2_ids)
                # If not, prioritize those that share a subject.
                else:
                    image_ids_2.update(shared_subj_image_2_ids)

                # Get all the ids of image 3s with an action that shares this
                # subject.
                shared_subj_image_3_ids = set()
                if action_1.subject_concept_id in subject_map_3:
                    shared_subj_image_3_ids = set(subject_map_3[action_1.subject_concept_id].keys())
                # Get all the ids of images 3s with an action that shares this
                # object.
                shared_obj_image_3_ids = set()
                if action_1.object_concept_id in object_map_3:
                    shared_obj_image_3_ids = set(object_map_3[action_1.object_concept_id].keys())
                # See if there are any images that have both.
                shared_roles_image_3_ids = shared_subj_image_3_ids.intersection(shared_obj_image_3_ids)
                # If there are, add those as viable image 3s.
                if len(shared_roles_image_3_ids) > 0:
                    image_ids_3.update(shared_roles_image_3_ids)
                # If there are not, prioritize those that share an object.
                elif len(shared_obj_image_3_ids) > 0:
                    image_ids_3.update(shared_obj_image_3_ids)
                # If not, prioritize those that share a subject.
                else:
                    image_ids_3.update(shared_subj_image_3_ids)

                iteration_count += 1
            # end for
            number_of_sets += len(image_ids_2) * len(image_ids_3)
            # If there are no possible sets, continue to the next image 1.
            if len(image_ids_2) == 0 or len(image_ids_3) == 0:
                continue
            # Pick the lowest object-count image 2.
            image_2_counts = {id: image_object_counts_2[id]
                              for id in image_ids_2}
            sorted_image_ids_2 = dict(sorted(image_2_counts.items(), key=lambda item: item[1]))
            # Pick the loweset object-count image 3.
            image_3_counts = {id: image_object_counts_3[id]
                              for id in image_ids_3}
            sorted_image_ids_3 = dict(sorted(image_3_counts.items(), key=lambda item: item[1]))

            # Build the image set without re-using images.
            image_set = list()
            image_set.append(image_id_1)
            for image_id_2 in sorted_image_ids_2.keys():
                if (not image_id_2 in image_ids_used
                    and not image_id_2 in image_set):
                    image_set.append(image_id_2)
                    break
                # end if
            # end for
            for image_id_3 in sorted_image_ids_3.keys():
                if (not image_id_3 in image_ids_used
                    and not image_id_3 in image_set):
                    image_set.append(image_id_3)
                    break
                # end if
            # end for
            if len(image_set) < 3:
                continue
            image_sets.append(image_set)
            image_ids_used.update(set(image_set))
            if len(image_sets) >= sets_to_make:
                break
        # end for

        # Results in 33 image sets.
        return image_sets

        print('okay :)')


        # Go through all subject object concept ids for action 1.
        # Go through all the action 1 instances with that subject.
        # Go through all action 2 instances with that subject.
        # Find an action 3 instance with one of:
        #   action 1 instance's subject
        #   action 1 instance's object
        #   action 2 instance's subject
        #   action 2 instance's object
        # Go through all action 3 instances with that subject.
        # Find an action 2 instance with one of:
        #   action 1 instance's subject
        #   action 1 instance's object
        #   action 3 instance's subject
        #   action 3 instance's object
        # Do the same for all object object concept ids for action 1.

        # Get all rows from image_action_object_pairs for action 1.
        search_word_1 = 'buy'
        action_pairs_1 = self._data_handler.get_action_object_pairs(search_word_1)
        image_ids_1 = set()
        # Group them by object_concept_id.
        # Key 1: object role, 'subject' or 'object'
        # Key 2: object_concept_id.
        # Value: list of action object pairs.
        pairs_by_object_1: dict[str, dict[int, list[ActionObjectPair]]] = dict()
        pairs_by_object_1['subject'] = dict()
        pairs_by_object_1['object'] = dict()
        for pair in action_pairs_1:
            if not pair.object_concept_id in pairs_by_object_1[pair.object_role]:
                pairs_by_object_1[pair.object_role][pair.object_concept_id] = list()
            pairs_by_object_1[pair.object_role][pair.object_concept_id].append(pair)
            image_ids_1.add(pair.image_id)
        # end for

        # Do the same for the other two actions.
        search_word_2 = 'cook'
        action_pairs_2 = self._data_handler.get_action_object_pairs(search_word_2)
        image_ids_2 = set()
        # Group them by object_concept_id.
        # Key 2: object role, 'subject' or 'object'
        # Key 2: object_concept_id.
        # Value: list of action object pairs.
        pairs_by_object_2: dict[str, dict[int, list[ActionObjectPair]]] = dict()
        pairs_by_object_2['subject'] = dict()
        pairs_by_object_2['object'] = dict()
        for pair in action_pairs_2:
            if not pair.object_concept_id in pairs_by_object_2[pair.object_role]:
                pairs_by_object_2[pair.object_role][pair.object_concept_id] = list()
            pairs_by_object_2[pair.object_role][pair.object_concept_id].append(pair)
            image_ids_2.add(pair.image_id)
        # end for

        search_word_3 = 'eat'
        action_pairs_3 = self._data_handler.get_action_object_pairs(search_word_3)
        image_ids_3 = set()
        # Group them by object_concept_id.
        # Key 3: object role, 'subject' or 'object'
        # Key 2: object_concept_id.
        # Value: list of action object pairs.
        pairs_by_object_3: dict[str, dict[int, list[ActionObjectPair]]] = dict()
        pairs_by_object_3['subject'] = dict()
        pairs_by_object_3['object'] = dict()
        for pair in action_pairs_3:
            if not pair.object_concept_id in pairs_by_object_3[pair.object_role]:
                pairs_by_object_3[pair.object_role][pair.object_concept_id] = list()
            pairs_by_object_3[pair.object_role][pair.object_concept_id].append(pair)
            image_ids_3.add(pair.image_id)
        # end for


        # Get the cs node cluster for this URI.
        cs_node_cluster = self._data_handler.get_cs_node_cluster(cs_node_uri)
        # Get the parsed causal links for this cs node uri's cluster.
        causal_links = self._read_causal_links(cs_node_cluster)

        # For each causal link, get cs node that's in the cluster and the
        # cs node that's not in the cluster. 
        
        # Get all unique image ids for cs nodes in the cluster. 
        image_ids_1 = set()
        # First, get all cluster cs nodes with a causal link.
        cluster_nodes_with_links = list()
        for link in causal_links:
            cs_node = None
            if link.source_cs_node in cs_node_cluster.cs_nodes.values():
                cs_node = link.source_cs_node
            elif link.target_cs_node in cs_node_cluster.cs_nodes.values():
                cs_node = link.target_cs_node
            # end if
            if not cs_node in cluster_nodes_with_links:
                cluster_nodes_with_links.append(cs_node)
            # end if
        # end for

        # For each cluster node with a link, get its ActionConcepts.
        action_concepts_1: list[ActionConcept] = list()
        for cs_node in cluster_nodes_with_links:
            concepts = self._data_handler.get_cs_node_action_concepts(cs_node)
            # Only get the ones with action links.
            for concept in concepts:
                if not len(concept.action_links) > 0:
                    continue
                action_concepts_1.append(concept)
            # end for
        # end for

        # For each action concept, get the ids of the images that it's in.
        for concept in action_concepts_1:
            concept_image_ids = concept.get_image_ids()
            image_ids_1.update(concept_image_ids)
        # end for

        # Now, for each image, look for an image to pair with.
        # Number of images 1's:
        # 3358

        all_image_pairs = set()
        start_time = timer()
        print(f'Finding pairs for {len(image_ids_1)} images.')
        image_counter = 0
        used_image_ids = set()
        for image_id in image_ids_1:
            image_counter += 1
            image_start_time = timer()
            print(f'Finding pairs for image {image_counter}/{len(image_ids_1)}.')
            image = self._data_handler.get_image_instance(image_id)
            image_pairs = self._find_pairs_for_image(
                image=image,
                cs_nodes=cluster_nodes_with_links,
                causal_links=causal_links,
                used_image_ids=used_image_ids,
                number_of_pairs=100
            )
            # Note all the used image ids so we don't pair them with other
            # images again.
            # Don't accept pairs where the second image id is already in the
            # used iamge ids set. 
            image_pairs_to_add = set()
            for image_pair in image_pairs:
                ids = list(image_pair)
                if not ids[0] in image_ids_1:
                    if ids[0] in used_image_ids:
                        continue
                    used_image_ids.add(ids[0])
                elif not ids[1] in image_ids_1:
                    if ids[1] in used_image_ids:
                        continue
                    used_image_ids.add(ids[1])
                # end if
                image_pairs_to_add.add(image_pair)
            # end for
            all_image_pairs.update(image_pairs_to_add)
            image_elapsed_time = timer() - image_start_time
            total_elapsed_time = timer() - start_time
            print(f'Done finding image pairs. Time taken: {image_elapsed_time:.3f}s.'
                  + f' Elapsed time: {total_elapsed_time:.3f}s.' 
                  + f' Avg. time/image: {total_elapsed_time/image_counter:.3f}s.'
                  + f'\nValid pairs: {len(image_pairs)}.'
                  + f' Valid pairs added: {len(image_pairs_to_add)}.'
                  + f' All valid pairs: {len(all_image_pairs)}.')
            
            # Only get as many pairs as the maximum number of image sets we're
            # going to make.
            if len(all_image_pairs) >= number_of_sets:
                break
        # end for
        elapsed_time = timer() - start_time
        print(f'Time taken to find pairs for all images: {elapsed_time}s.')

        # For each pair, find a third image. 

        image_sets = list()
        #used_image_ids = set()
        for image_pair in all_image_pairs:
            image_pair_ids = list(image_pair)
            image_1_id = image_pair_ids[0]
            image_2_id = image_pair_ids[1]
            image_3_id = self._find_third_image(image_pair_ids, used_image_ids)
            image_set = [image_1_id, image_2_id, image_3_id]
            image_sets.append(image_set)
            used_image_ids.add(image_3_id)
        # end for

        # Then, return the image sets. 
        return image_sets
    # end _make_image_sets

    # Get the action instances, subject_action_map, and object_action_map
    # for a search term.
    def _get_action_instances_and_maps(self, search_term: str):
        '''
        Get the action instances, subject_image_action_map, 
        object_image_action_map, and image_action_map for a set of action
        instances.
        '''
        actions = self._data_handler.get_action_instances(search_term)
        subjects_map, objects_map, images_map = self._get_action_maps(actions)
        return actions, subjects_map, objects_map, images_map
    # end _get_action_instances_and_maps

    def _get_action_maps(self, actions: dict[int, ActionInstance]):
        '''
        Get the subject_image_action_map, 
        object_image_action_map, and image_action_map for a set of action
        instances.
        '''
        # Map action instance ids to subject and object concept ids, then to
        # image ids.
        # Key 1: object concept id
        # Key 2: image_id
        subject_image_action_map: dict[int, dict[int, list[int]]] = dict()
        object_image_action_map: dict[int, dict[int, list[int]]] = dict()
        # Map action instance ids to image ids.
        image_action_map: dict[int, list[int]] = dict()
        for action in actions.values():
            subj_id = action.subject_concept_id
            image_id = action.image_id
            if not subj_id in subject_image_action_map:
                subject_image_action_map[subj_id] = dict()
            if not image_id in subject_image_action_map[subj_id]:
                subject_image_action_map[subj_id][image_id] = list()
            subject_image_action_map[subj_id][image_id].append(action.id)
            # Action's don't have to have objects, so make sure this one does
            # before checking anything about it.
            if not action.object_concept_id is None:
                obj_id = action.object_concept_id
                if not obj_id in object_image_action_map:
                    object_image_action_map[obj_id] = dict()
                if not image_id in object_image_action_map[obj_id]:
                    object_image_action_map[obj_id][image_id] = list()
                object_image_action_map[obj_id][image_id].append(action.id)
            # end if
            if not action.image_id in image_action_map:
                image_action_map[action.image_id] = list()
            image_action_map[action.image_id].append(action.id)
        # end for
        return subject_image_action_map, object_image_action_map, image_action_map
    # end _get_action_instances_and_maps


    def _find_pairs_for_image(self, image: ImageInstance,
                              cs_nodes: list[CommonSenseNode],
                              causal_links: list[CausalLink],
                              used_image_ids: set[int],
                              number_of_pairs: int):
        '''
        Find all the images that pair with an image.

        Doesn't use images in the used image ids list.

        Only returns up to the number of pairs specified. 
        '''
        # With an image id, a bunch of causal links, and the cs nodes
        # for those causal links
        # We can get every action concept from the cs nodes.
        action_concepts_1: list[ActionConcept] = list()
        for cs_node in cs_nodes:
            concepts = self._data_handler.get_cs_node_action_concepts(cs_node)
            action_concepts_1.extend(concepts)
        # end for

        # We can look up those concepts' instances in this image from the
        # action_instance_ids dict in the concept.
        # We can then fetch the action instances themselves to get
        # each instance's subject concept id and/or object concept id.
        # We can get all unique subject and/or object concept ids.
        #instance_ids_1 = set()
        # Action instances in the image passed in grouped by subject id.
        instances_by_subject: dict[int, list[ActionInstance]] = dict()
        # Action instances in the image passsed in grouped by object id.
        instances_by_object: dict[int, list[ActionInstance]] = dict()
        for concept in action_concepts_1:
            # Not every of the cs nodes' action concepts has an instance in this 
            # image.
            if not image.id in concept.action_instance_ids:
                continue
            instance_ids = concept.action_instance_ids[image.id]
            instances = [self._data_handler.get_action_instance(id)
                         for id in instance_ids]
            for instance in instances:
                if instance.subject is not None:
                    subject_concept_id = instance.subject.object_concept_id
                    if not subject_concept_id in instances_by_subject:
                        instances_by_subject[subject_concept_id] = list()
                    instances_by_subject[subject_concept_id].append(instance)
                # end if
                if instance.object_ is not None:
                    object_concept_id = instance.object_.object_concept_id
                    if not object_concept_id in instances_by_object:
                        instances_by_object[object_concept_id] = list()
                    instances_by_object[object_concept_id].append(instance)
                # end if
            # end for
        # end for

        # Using those, we can use this query:
        # Data: object_concept_id, object_role, object_concept_id, image_id
        query = ('''
            WITH occurence_counts
            AS (
                SELECT image_id, occurrence_count FROM (
                    SELECT *, count(*) AS occurrence_count
                    FROM image_objects
                    WHERE object_concept_id = ?
                    GROUP BY image_id, object_concept_id
                )
                WHERE occurrence_count > 1
            )

            SELECT * FROM image_action_object_pairs
            INNER JOIN occurence_counts
            ON image_action_object_pairs.image_id = occurence_counts.image_id
            WHERE object_role = ?
            AND object_concept_id = ?
            AND image_action_object_pairs.image_id != ?
        ''')
        # To get all the action-object pairs that also have that object concept
        # in that role, are in different images, and where the object concept
        # occurs at least two times. 

        # Query takes about 500ms on first time, 100ms on subsequent.
        # Grouping those rows by image, we can get all the unique image ids
        # of other images to check against this one.
        # Key 1: image id, int.
        # Key 2: role, str. Either 'subject' or 'object'.
        # Key 3: object_concept_id, int.
        # Value: List of rows from image_action_object_pairs
        rows_by_image: dict[int, dict[str, dict[int, list]]] = dict()
        row_counter = 0
        for subject_id, instances_1 in instances_by_subject.items():
            role = 'subject'
            #query_role = '\'subject\''
            query_data = [subject_id, role, subject_id, image.id]
            rows = self._execute_query(query, query_data)
            for row in rows:
                # 0 - image_id
                image_id = row[0]
                # 7 - object concept id
                object_concept_id = row[7]
                if not image_id in rows_by_image:
                    rows_by_image[image_id] = dict()
                if not role in rows_by_image[image_id]:
                    rows_by_image[image_id][role] = dict()
                # end if
                if not object_concept_id in rows_by_image[image_id][role]:
                    rows_by_image[image_id][role][object_concept_id] = list()
                rows_by_image[image_id][role][object_concept_id].append(row)
                row_counter += 1
            # end for row
        # end for subject_id
        for object_id, instances_1 in instances_by_object.items():
            role = 'object'
            #query_role = '\'object\''
            query_data = [object_id, role, object_id, image.id]
            rows = self._execute_query(query, query_data)
            for row in rows:
                # 0 - image_id
                image_id = row[0]
                # 7 - object concept id
                object_concept_id = row[7]
                if not image_id in rows_by_image:
                    rows_by_image[image_id] = dict()
                if not role in rows_by_image[image_id]:
                    rows_by_image[image_id][role] = dict()
                # end if
                if not object_concept_id in rows_by_image[image_id][role]:
                    rows_by_image[image_id][role][object_concept_id] = list()
                rows_by_image[image_id][role][object_concept_id].append(row)
                row_counter += 1
            # end for row
        # end for subject_id

        # TODO: Break this into functions.

        # Then, we can go through each row for that other image, get the image's
        # instance as image_2, get the action instance as action_2, and do our 
        # valid image pair checks.
        visual_sim_total_time = 0
        visual_sim_counter = 0
        valid_image_2_counter = 0

        # 5467 image 2s and 13159 rows.
        print(f'Number of image 2s: {len(rows_by_image)}. '
              + f' Number of rows: {row_counter}. ')

        start_time = timer()
        valid_image_pairs = set()
        for image_2_id, rows_by_role in rows_by_image.items():
            # If this image has been used before, don't pair it again.
            if image_2_id in used_image_ids:
                continue
            # There's still too many images, so we have to do some more 
            # filtering.
            # Before parsing anything else about image 2, try to find out if 
            # there's at least one forward and at least one backward causal link
            # between the two images.
            image_causal_links = self._data_handler.get_image_causal_links(
                image.id, image_2_id
            )
            # Tally the forward weight by summing the weight of all the causal
            # links from image 1 to image 2.
            forward_weight = 0
            # Tally the backward weight by summing the weight of all the
            # causal links from image 2 to image 1.
            backward_weight = 0
            for link in image_causal_links:
                if link.get_true_direction() == CausalFlowDirection.FORWARD:
                    forward_weight += link.weight
                else:
                    backward_weight += link.weight
            # end for

            # If either forward or backward weights are 0, there are only
            # causal links between the images in one direction. Skip this
            # image 2.
            if forward_weight == 0 or backward_weight == 0:
                continue

            # When determining the causal direction dominance, take into
            # account the weights of the multi causal links as well. 
            '''
            image_multi_causal_links = self._data_handler.get_image_multi_causal_links(
                image.id, image_2_id
            )
            for link in image_multi_causal_links:
                if link.get_true_direction() == CausalFlowDirection.FORWARD:
                    forward_weight += link.get_weight()
                else:
                    backward_weight += link.get_weight()
            # end for
            '''
            
            # Determine the dominant causal direction between these two images.
            # Forward is from image 1 to image 2
            # Backward is from image 2 to image 1
            dominant_causal_direction = (CausalFlowDirection.FORWARD
                                         if forward_weight > backward_weight
                                         else CausalFlowDirection.BACKWARD)
            
            valid_image_2_counter += 1
            image_2 = self._data_handler.get_image_instance(image_2_id)
            is_valid_pair = False
            # Now we can look at each subject/object matching causally linked
            # action instance pair. 
            for role, rows_by_object_id in rows_by_role.items():
                # The instances from image 1, keyed by the object concept id
                # for the object they're paired with.
                instances_1_by_object_id = dict()
                if role == 'subject':
                    instances_1_by_object_id = instances_by_subject
                elif role == 'object':
                    instances_1_by_object_id = instances_by_object
                # Now we go through each object concept id for this role.
                for object_concept_id, instances_1 in instances_1_by_object_id.items():
                    # See if there are any rows for this object concept in image 2.
                    # If not, skip it.
                    if not object_concept_id in rows_by_object_id:
                        continue
                    # If there are, we're going to be comparing the visual
                    # similarity of every of this object in image 1
                    # to every of this object in image 2. 
                    # Key 1: image 1 object instance id
                    # Key 2: image 2 object instance id
                    # Value: visual similarity, float
                    visual_sim_start_time = timer()
                    visual_sims = dict()
                    # Keep track of the object instance id of the highest
                    # similarity object in the other image.
                    # Key: image 1 object instance id
                    # Value: dict with:
                    #   'sim', float 
                    #   'object_instance_id', int, from image 2
                    highest_sim_1 = dict()
                    # Key: image 2 object instance id
                    # Value: dict with:
                    #   'sim', float 
                    #   'object_instance_id', int, from image 2
                    highest_sim_2 = dict()
                    for object_instance_1 in image.objects_by_concept[object_concept_id]:
                        id_1 = object_instance_1.id
                        if not id_1 in highest_sim_1:
                            highest_sim_1[id_1] = {
                                'sim': 0,
                                'object_instance_id': -1
                            }
                        # end if
                        for object_instance_2 in image_2.objects_by_concept[object_concept_id]:
                            id_2 = object_instance_2.id
                            if not id_2 in highest_sim_2:
                                highest_sim_2[id_2] = {
                                    'sim': 0,
                                    'object_instance_id': -1
                                }
                            # end if
                            sim = self._get_visual_similarity(
                                object_1=object_instance_1,
                                object_2=object_instance_2,
                                image_1=image,
                                image_2=image_2
                            )
                            if not id_1 in visual_sims:
                                visual_sims[id_1] = dict()
                            visual_sims[id_1][id_2] = sim
                            # Populate highest sims for both object instances.
                            if sim > highest_sim_1[id_1]['sim']:
                                highest_sim_1[id_1]['sim'] = sim
                                highest_sim_1[id_1]['object_instance_id'] = id_2
                            # end if
                            if sim > highest_sim_2[id_2]['sim']:
                                highest_sim_2[id_2]['sim'] = sim
                                highest_sim_2[id_2]['object_instance_id'] = id_1
                            # end if
                            visual_sim_counter += 1
                        # end for object_instance_2
                    # end for object_instance_1
                    visual_sim_total_time += timer() - visual_sim_start_time

                    # Compare each action instance 1 with each action instance 2.
                    # They share an object. See if they're causally linked.
                    for instance_1 in instances_1:
                        # Get concept_1, then get the ids of all linked concepts
                        # where one of the causal links passed in links the
                        # concepts. 
                        concept_1 = self._data_handler.get_action_concept(instance_1.action_concept_id)
                        linked_concept_ids = concept_1.get_linked_action_concept_ids(
                            causal_links=causal_links
                        )
                        for row in rows_by_object_id[object_concept_id]:
                            # This is an image_action_object_pair row.
                            # 6 - action_concept_id
                            # See if this row is for an action concept that's
                            # causally linked to concept_1.
                            if not row[6] in linked_concept_ids:
                                continue
                            concept_2 = self._data_handler.get_action_concept(row[6])
                            # If it is causally linked, see if there's an
                            # alternate causal link that the system could choose.
                            # If it is causally linked, get the dominant 
                            # direction of the link between these two. 
                            dominant_link_direction = concept_1.get_dominant_action_link_direction(row[6])
                            
                            # If it's in the same direction as the dominant
                            # causal direction between the images, there likely
                            # won't be an alternate causal link chosen over
                            # this one.

                            if dominant_link_direction == dominant_causal_direction:
                                continue

                            # See if there are alternate options
                            # for object equivalence. 
                            # How do we tell?
                            # Well, see if instance 1's matching object is
                            # instance 2's matching object's highest sim
                            # object. If not, then there must exist a different
                            # object in image 2 with a higher similarity to
                            # instance 1's matching object, i.e. an alternate
                            # object to equate with. 
                            object_instance_1 = None
                            if role == 'subject':
                                object_instance_1 = instance_1.subject
                            else:
                                object_instance_1 = instance_1.object_
                            
                            # 3 - object_instance_id
                            object_instance_2 = self._data_handler.get_object_instance(row[3])

                            id_1 = object_instance_1.id
                            id_2 = object_instance_2.id
                            if not highest_sim_1[id_1]['object_instance_id'] == id_2:
                                is_valid_pair = True
                                break
                            # end if
                            # Check in reverse too.
                            if not highest_sim_2[id_2]['object_instance_id'] == id_1:
                                is_valid_pair = True
                                break
                            # end if
                        # end for
                        if is_valid_pair:
                            break
                    # end for instance_1
                    if is_valid_pair:
                        break
                # end for object_concept_id
                if is_valid_pair:
                    break
            # end for role
            if is_valid_pair:
                valid_image_pairs.add(frozenset([image.id, image_2_id]))
                # Only take the first number_of_pairs valid image pairs.
                if len(valid_image_pairs) == number_of_pairs:
                    break
                # end if
            # end if
        # end for image_id
        elapsed_time = timer() - start_time
        print(f'Done parsing image 2s. Total time taken: {elapsed_time}s.'
              + f' Double causally linked image 2s: {valid_image_2_counter}.')
              #+ f'\nNumber of valid image pairs: {len(valid_image_pairs)}')
              #+ f'\nTime spent calculating {visual_sim_counter} visual sims: {visual_sim_total_time}s.'
              #+ f' Average time per calc: {visual_sim_total_time/visual_sim_counter}s.'
              #+ f'\nNumber of bidirectionally causally linked image 2s: {valid_image_2_counter}.')

        return valid_image_pairs
    # end _find_pairs_for_image

    def _find_third_image(self, image_id_pair: frozenset[int], 
                          used_image_ids: set[int]) -> int | None:
        '''
        Find a third image to go with a pair of images to make an image set.

        Returns None if there are no valid images. 
        '''
        image_ids = list(image_id_pair)
        image_1 = self._data_handler.get_image_instance(image_ids[0])
        image_2 = self._data_handler.get_image_instance(image_ids[1])
        # The third image must:
        #   Share at least one object with one of the other images.
        #   Share a causal link with at least one of the other images.
        #   Have not been used as a third image before. 
        # Query gets the image ids of all the images that share an object
        # with image 1 or image 2 and which are causally linked to image 1
        # or image 2. 
        # Test image ids: 1203, 2088
        # Query takes about 1 second.
        # Data is image id 1, image id 2, image id 1, image id 2.
        query = ('''
            -- The object concepts in the search images.
            WITH search_object_concepts AS (
                SELECT object_concept_id FROM image_object_concepts
                WHERE image_id = ?
                OR image_id = ?
            ),
            -- All the cs nodes for the action concepts in the search images.
            search_action_cs_nodes AS (
                -- All of the action concepts in the search images.
                SELECT * FROM (
                    SELECT action_concept_id FROM image_action_concepts
                    WHERE image_id = ?
                    OR image_id = ?
                ) AS search_image_actions
                INNER JOIN action_cs_nodes
                ON search_image_actions.action_concept_id = action_cs_nodes.action_concept_id
            ),
            -- All the cs nodes causally linked to cs nodes for the actions
            -- in the search images.
            linked_cs_nodes AS (
                SELECT DISTINCT linked_node_id
                FROM (
                    SELECT * FROM causal_links
                    INNER JOIN search_action_cs_nodes
                    ON search_action_cs_nodes.cs_node_id = causal_links.source_node_id
                    INNER JOIN (
                        SELECT cs_node_id AS linked_node_id
                        FROM action_cs_nodes
                    )
                    ON linked_node_id = causal_links.target_node_id
                    UNION
                    SELECT * FROM causal_links
                    INNER JOIN search_action_cs_nodes
                    ON search_action_cs_nodes.cs_node_id = causal_links.target_node_id
                    INNER JOIN (
                        SELECT cs_node_id AS linked_node_id
                        FROM action_cs_nodes
                    )
                    ON linked_node_id = causal_links.source_node_id
                )
            ),
            -- Action concepts causally linked to actions in the search images.
            linked_action_concepts AS (
                SELECT DISTINCT action_concept_id FROM action_cs_nodes
                INNER JOIN linked_cs_nodes
                ON action_cs_nodes.cs_node_id = linked_cs_nodes.linked_node_id
            ),
            -- Images with a causal link to one of the search images.
            linked_action_images AS (
                SELECT DISTINCT image_id FROM image_action_concepts
                INNER JOIN linked_action_concepts
                ON image_action_concepts.action_concept_id = linked_action_concepts.action_concept_id
            ),
            -- Linked action images with the object concepts in those images
            linked_action_image_objects AS (
                SELECT * FROM image_object_concepts
                INNER JOIN linked_action_images
                ON image_object_concepts.image_id = linked_action_images.image_id
            )

            SELECT image_id FROM linked_action_image_objects
            INNER JOIN search_object_concepts
            ON linked_action_image_objects.object_concept_id = search_object_concepts.object_concept_id
        ''')
        data = [image_1.id, image_2.id, image_1.id, image_2.id]
        rows = self._execute_query(query, data)
        # Pick the first valid image that hasn't been used before
        # and which isn't either of the images in the set.
        for row in rows:
            image_3_id = row[0]
            if (not image_3_id in used_image_ids
                and not image_3_id == image_1.id
                and not image_3_id == image_2.id):
                return image_3_id
        # end for
        return None
    # end _find_third_image

    # end _compare_images

    def _compare_paired_objects(self, 
        action_1: ActionInstance, 
        action_2: ActionInstance, 
        image_1: ImageInstance, 
        image_2: ImageInstance, 
        role: str) -> bool:
        '''
        Compare either the subject or object of a pair of actions instances from 
        different image instances and see if they are valid.

        Returns True if they are valid. Returns False otherwise.

        To be valid, the paired objects must:

            1. Have the same object concept.

            2. Not share a color attribute with one another.

            3. For one of them, there must be another object instance with the
            same concept in the other image.

            4. It must share a color attribute with the other object instance. 
        '''
        object_1 = action_1.subject if role == 'subject' else action_1.object_
        object_2 = action_2.subject if role == 'subject' else action_2.object_
        # If either of the actions didn't have that role filled, it'll be None.
        # Return False if either didn't have the role filled.
        if object_1 is None or object_2 is None:
            return False
        # Make sure the two objects share an object concept.
        if not object_1.object_concept_id == object_2.object_concept_id:
            return False
        
        # DEBUG:
        # Do either of them have colors?
        if len(object_1.color_attributes) > 0:
            print('Object 1 has colors.')
        if len(object_2.color_attributes) > 0:
            print('Object 2 has colors.')

        # Make sure the two objects don't share a color.
        #shared_colors = object_1.color_attributes.intersection(object_2.color_attributes)
        if object_1.shares_colors(object_2):
            return False
        
        # Get the visual similarity between the two main objects.
        paired_object_sim = self._get_visual_similarity(object_1, object_2,
                                                        image_1, image_2)
        
        better_sim = False
        # See if object 1 is more similar to a different object in image 2.

        
        # For each object, check the other image for another matching object
        # which it does share a color attribute with.
        if len(self._get_visually_similar_objects(object_1, image_2)) > 0:
            return True
        if len(self._get_visually_similar_objects(object_2, image_1)) > 0:
            return True
        return False
    # end _compare_paired_objects

    def _get_visual_similarity(self, object_1: ObjectInstance,
                               object_2: ObjectInstance, image_1: ImageInstance,
                               image_2: ImageInstance) -> float:
        '''
        
        '''
        # Get the appearance of each object by slicing its bounding box out
        # of its image.
        box_1 = object_1.bounding_box
        appearance_1 = image_1.image.matrix[box_1.y:box_1.y + box_1.h,
                                            box_1.x:box_1.x + box_1.w]
        box_2 = object_2.bounding_box
        appearance_2 = image_2.image.matrix[box_2.y:box_2.y + box_2.h,
                                            box_2.x:box_2.x + box_2.w]
        # Resize the image regions so that they're the exact same dimensions.
        # Resize both horizontally and vertically down to the smaller of 
        # each dimension between the two.
        height = int(min(appearance_1.shape[0], appearance_2.shape[0]))
        width = int(min(appearance_1.shape[1], appearance_2.shape[1]))
        new_size = (width, height)
        # Change appearances to grayscale.
        #appearance_1 = cv2.cvtColor(cv2.resize(appearance_1, new_size), cv2.COLOR_BAYER_BG2GRAY)
        #appearance_2 = cv2.cvtColor(cv2.resize(appearance_2, new_size), cv2.COLOR_BAYER_BG2GRAY)
        appearance_1 = cv2.resize(appearance_1, new_size)
        appearance_2 = cv2.resize(appearance_2, new_size)
        # Convert both appearances to grayscale.
        appearance_1 = cv2.cvtColor(appearance_1, cv2.COLOR_BGR2GRAY)
        appearance_2 = cv2.cvtColor(appearance_2, cv2.COLOR_BGR2GRAY)
        # Get the similarity between the two image regions.
        # Returns a float.
        # RMSE gives us the difference, so we have to subtract it from 1.
        # FSIM gives us a similarity, so we don't subtract it from 1.
        # SSIM gives us a similarity. Closer to 1 is more similar.
        # win_size is 7, so if any dimension of the image is smaller
        # than that we can't call structural_similarity.
        # Give the similarity a default value of 0. 
        if (height < 7 or width < 7):
            similarity = 0
        else:
            similarity = structural_similarity(appearance_1, appearance_2)
        return similarity
    # _get_visual_similarity

    def _get_visually_similar_objects(self, object_: ObjectInstance, 
                                      image: ImageInstance):
        '''
        Returns a list of all of the ObjectInstances in the ImageInstance
        passed in which are visually similar to the ObjectInstance passed in
        and which have the same ObjectConcept.
        '''
        similar_objects = list()

        image_objects = image.objects_by_concept[object_.object_concept_id]
        for image_object in image_objects:
            if image_object.shares_colors(object_):
                similar_objects.append(image_object)
            # end if
        # end for

        return similar_objects
    # end _get_visually_similar_objects

    def _get_causal_direction_strengths(self, 
            image_1: ImageInstance, 
            image_2: ImageInstance):
        '''
        Gets the strength of the causal links from image 1 to image 2
        and from image 2 to image 1.

        Returns them in a tuple, with the strength of 1 to 2 as the first item
        and the strength of 2 to 1 as the second item.

        Sums the weights of all the causal links between actions in both
        directions.
        '''
        # The total weight of causal links from image 1 to image 2.
        total_forward_weight = 0
        # The total weight of causal links from image 2 to image 1.
        total_backward_weight = 0

        # Sum the total weight of the causal links in that action link in
        # either direction.
        # Multiply the directional weights by the number of image 2 actions, and
        # add them to the sum directional weights. 
        # For each action instance in image 1, get its action concept.
        for action_1 in image_1.action_instances.values():
            action_concept_1 = self._data_handler.get_action_concept(action_1.action_concept_id)
            # For that action concept, go through each of its action links.
            for action_concept_id, link in action_concept_1.action_links.items():
                # Get the action concept at the other end of the link.
                # Count how many actions have that concept in image 2.
                action_2_count = len(image_2.actions_by_concept[action_concept_id])
                # If it's zero, this link doesn't link the two images.
                if action_2_count == 0:
                    continue
                # Get the total weight of the causal links in that action link in
                # either direction, then multiply it by the number of actions in
                # image 2 and add it to their respective directional weights.
                forward_weight, backward_weight = link.get_weight_sums()
                total_forward_weight += action_2_count * forward_weight
                total_backward_weight += action_2_count * backward_weight
            # end for link
        # end for action_1
        return total_forward_weight, total_backward_weight
    # end _get_causal_direction_strengths

    def print_causal_links(self, lower, upper):
        '''
        Print the single-step causal links for each cs node related to an action.
        '''

        # First, determine all cs node clusters.
        # Each cluster has a root whose URI is in the form of /c/en/word
        # The subordinate nodes have URIs in the form of /c/en/word/other/stuff.

        # Get all unique cs node uris from action_to_action_causal_links
        query = ('''
            SELECT source_node_id AS cs_node_id, source_node_uri AS cs_node_uri FROM action_to_action_causal_links
            GROUP BY cs_node_uri
            UNION SELECT target_node_id AS cs_node_id, target_node_uri AS cs_node_uri FROM action_to_action_causal_links
            GROUP BY cs_node_uri
        ''')
        rows = self._data_handler._execute_query(query)
        root_cs_nodes: list[CommonSenseNode] = list()
        sub_cs_nodes: list[CommonSenseNode] = list()
        # 0 - cs_node_id
        # 1 - cs_node_uri
        for row in rows:
            cs_node_id: int = row[0]
            cs_node_uri: str = row[1]
            cs_node = self._data_handler.get_cs_node(cs_node_id)
            # Root nodes will have URIs in the form of /c/en/word,
            # which, when split by '/', should only be 4 items.
            if len(cs_node_uri.split('/')) == 4:
                root_cs_nodes.append(cs_node)
            else:
                sub_cs_nodes.append(cs_node)
            # end if
        # end for

        # Organize all the cs nodes into sets, keyed by the root cs node's id.
        # Key: root cs node id, int
        # Value: set of sub cs nodes (including the root), list[CommonSenseNode]
        cs_node_clusters: dict[int, list[CommonSenseNode]] = dict()
        # Map root words to the id of their root cs node.
        root_words_to_id_map: dict[str, int] = dict()
        for root_cs_node in root_cs_nodes:
            cs_node_clusters[root_cs_node.id] = list()
            # The item in the 3rd index of the split URI should be the 
            # shared word.
            root_word = root_cs_node.uri.split('/')[3]
            root_words_to_id_map[root_word] = root_cs_node.id
            # Add the root cs node to its own cluster.
            cs_node_clusters[root_cs_node.id].append(root_cs_node)
        # end for

        for sub_cs_node in sub_cs_nodes:
            sub_word = sub_cs_node.uri.split('/')[3]
            # If the sub node isn't in the list of root cs nodes, find its
            # root cs node and make a cluster out of it.
            if sub_word not in root_words_to_id_map:
                uri_split = sub_cs_node.uri.split('/')
                root_uri = f'{uri_split[0]}/{uri_split[1]}/{uri_split[2]}/{uri_split[3]}'
                root_cs_node = self._data_handler._commonsense_querier.get_node_by_uri(root_uri)
                cs_node_clusters[root_cs_node.id] = list()
                root_words_to_id_map[sub_word] = root_cs_node.id
            # end if
            root_cs_node_id = root_words_to_id_map[sub_word]
            cs_node_clusters[root_cs_node_id].append(sub_cs_node)
        # end for

        # Results in 201 clusters, 163 root nodes, and 48 sub nodes.
        # For each cluster, get all the causal links for all the nodes in
        # the cluster.
        # All the causal links for each cluster, keyed by cluster root node id.
        # Key: int
        # Value: list[CausalLink]
        cluster_links: dict[int, list[CausalLink]] = dict()
        link_counter = 0
        filtered_link_counter = 0
        for root_cs_node_id, cluster in cs_node_clusters.items():
            cluster_links[root_cs_node_id] = list()
            root_cs_node = self._data_handler.get_cs_node(root_cs_node_id)
            for cs_node in cluster:
                links = self._data_handler.get_causal_links(cs_node)
                # Only include links to cs nodes that appear in an action in
                # an image.
                filtered_links = list()
                for link in links:
                    link_counter += 1
                    source_actions = self._data_handler.get_cs_node_action_concepts(link.source_cs_node)
                    source_has_instances = False
                    for action in source_actions:
                        if len(action.action_instances) > 0:
                            source_has_instances = True
                            break
                        # end if
                    # end for
                    if not source_has_instances:
                        continue

                    target_actions = self._data_handler.get_cs_node_action_concepts(link.target_cs_node)
                    target_has_instances = False
                    for action in target_actions:
                        if len(action.action_instances) > 0:
                            target_has_instances = True
                            break
                        # end if
                    # end for
                    if not target_has_instances:
                        continue
                    filtered_link_counter += 1
                    filtered_links.append(link)
                # end for
                cluster_links[root_cs_node_id].extend(filtered_links)
            # end for
        # end for

        # 4614 non-filtered links
        # 506 filtered links

        # Sort cluster links by descending order to number of causal links.
        sorted_cluster_links = dict(sorted(cluster_links.items(),
                                    key=lambda item: len(item[1]),
                                    reverse=True))

        # Print out the causal links for each cluster to a file with the 
        # cluster's root word in the name. 
        total_file_counter = 0
        for root_cs_node_id, links in sorted_cluster_links.items():
            root_cs_node = self._data_handler.get_cs_node(root_cs_node_id)
            link_strings = list()
            for link in links:
                link_strings.append(link.get_string())
            # end for

            # Print out this cluster's link strings into a text file.
            file_name = f'{total_file_counter}_causal_links_{root_cs_node.labels[0]}'
            file_name += '.txt'
            file_path = self._causal_links_directory + '/' + file_name
            # Writelines doesn't actually write separate lines, so you have to
            # put a newline after each line.
            with open(file_path, 'w') as file:
                file.writelines(s + '\n' for s in link_strings)
            # end with
            total_file_counter += 1
        # end for

        print('Done printing causal links :)')
    # end print_causal_links

    def _read_causal_links(self, cs_node_cluster: CommonSenseNodeCluster) -> list[CausalLink]:
        '''
        Given a CommonSenseNodeCluster, finds the parsed causal links file 
        associated with the root cs node of the cluster.

        Returns all the CausalLinks in that file.        
        '''
        root_cs_node = cs_node_cluster.get_root()
        # Look in the parsed causal links folder for a file whose name ends
        # in the first label of the root cs node.
        root_label = root_cs_node.labels[0]

        # Search all the files prefixed with 'parsed'
        causal_link_strings = list()
        directory = self._causal_links_directory + '/parsed'
        #directory = self._causal_links_directory
        for file_name in os.listdir(directory):
            # Look only for text files.
            if not file_name.split('.')[-1] == 'txt':
                continue
            # First, strip the extension from the filename.
            file_name_split = file_name.removesuffix('.txt')
            # Split the file name and extract information from it.
            # 0 - 'parsed'
            # 1 - file number, int
            # 2, 3 - 'causal' and 'links'
            # 4 - cs node label
            file_name_split = file_name_split.split('_')
            #if not file_name_split[0] == 'parsed':
            #    continue
            # Look only for the cs nodes whose label we're searching for.
            if not file_name_split[-1] == root_label:
                continue

            file_path = f'{directory}/{file_name}'
            with open(file_path, 'r') as file:
                for line in file.readlines():
                    # Skip blank lines.
                    if line == '':
                        continue
                    # Strip newlines.
                    line_stripped = line.rstrip('\n')
                    causal_link_strings.append(line_stripped)
                # end for
            # end with
        # end for

        # Find the causal link for each causal link string.
        # Get the string representations of each causal link for each node in
        # the cluster, then map those string reps to the causal links they
        # came from.
        causal_link_string_map: dict[str, CausalLink] = dict()
        for cs_node in cs_node_cluster.nodes():
            for causal_link in self._data_handler.get_causal_links(cs_node):
                causal_link_string_map[causal_link.get_string()] = causal_link
            # end for
        # end for

        # Get the causal links from the files by using the causal link string
        # map.
        file_causal_links = list()
        for causal_link_string in causal_link_strings:
            file_causal_links.append(causal_link_string_map[causal_link_string])
        # end for

        return file_causal_links
    # end read_causal_links



    def print_multi_causal_links(self, lower, upper):
        '''
        Prints all multi-step causal links between action cs nodes where there 
        aren't also single-step causal links.
        '''
        print('Printing exclusively multi-step causal links...')
        start_time = timer()
        cs_node_ids = self._data_handler.get_all_action_cs_node_ids()

        # Keep track of which pairs of cs node ids we've already parsed.
        parsed_cs_node_id_pairs: set[frozenset[int]] = set()

        # Keep track of each pair of cs nodes that meet our criteria, as well
        # as the multi causal links between them. 
        # Key: frozenset(int, int) of cs_node_id pairs.
        # Value: list of valid multi causal links.
        valid_cs_node_links_by_pair: dict[frozenset[int], list[MultiCausalLink]] = dict()
        # For each cs node with a valid multi-causal link, keep a list of all
        # such valid links related to them.
        # Key: cs node id, int
        # Value: list of MultiCausalLinks
        valid_cs_node_links: dict[int, list[MultiCausalLink]] = dict()
        
        valid_causal_link_counter = 0
        valid_cs_node_counter = 0
        for cs_node_id in cs_node_ids:
            cs_node = self._data_handler.get_cs_node(cs_node_id)

            # Get the set of ids of cs nodes that have at least one single-step 
            # causal link with this cs node.
            causally_linked_cs_node_ids = set()
            for causal_link in self._data_handler.get_causal_links(cs_node):
                other_cs_node = causal_link.get_other_cs_node(cs_node)
                causally_linked_cs_node_ids.add(other_cs_node.id)
            # end for

            # DEBUG
            #if cs_node.labels[0] == 'approach':
            #    print('Approach')

            parsed_id_pairs_to_add = set()
            # Go through each multi-step causal link this cs node has.
            for multi_causal_link in self._data_handler.get_multi_causal_links(cs_node):
                # Get the other cs node in this link.
                other_cs_node = multi_causal_link.get_other_cs_node(cs_node)
                # Don't consider multi causal links that loop back around to
                # the node.
                if cs_node == other_cs_node:
                    continue
                cs_node_id_pair = frozenset([cs_node.id, other_cs_node.id])
                if cs_node_id_pair in parsed_cs_node_id_pairs:
                    continue
                # Find out if there's any single-step causal links between them. 
                # If so, consider this cs node id pair parsed and stop here.
                if other_cs_node.id in causally_linked_cs_node_ids:
                    parsed_cs_node_id_pairs.add(cs_node_id_pair)
                    continue
                # end if
                # If there aren't any single-step causal links between them,
                # then this pair of cs nodes meets our criteria.
                # Start, or add to, the list for the the multi-causal links 
                # between the two.
                if not cs_node_id_pair in valid_cs_node_links_by_pair:
                    valid_cs_node_links_by_pair[cs_node_id_pair] = list()
                # end if

                is_duplicate = False
                for existing_link in valid_cs_node_links_by_pair[cs_node_id_pair]:
                    if multi_causal_link.is_duplicate(existing_link):
                        #print('Duplicate multi causal link.')
                        is_duplicate = True
                        break
                    # end if
                # end for
                if is_duplicate:
                    continue

                valid_cs_node_links_by_pair[cs_node_id_pair].append(multi_causal_link)
                
                if not cs_node_id in valid_cs_node_links:
                    valid_cs_node_links[cs_node_id] = list()
                if not other_cs_node.id in valid_cs_node_links:
                    valid_cs_node_links[other_cs_node.id] = list()

                valid_cs_node_links[cs_node_id].append(multi_causal_link)
                valid_cs_node_links[other_cs_node.id].append(multi_causal_link)

                valid_causal_link_counter += 1

                # Add valid id pairs after this so that we can keep
                # updating the list of multi causal links between them.
                parsed_id_pairs_to_add.add(cs_node_id_pair)
            # end for multi_causal_link
            parsed_cs_node_id_pairs.update(parsed_id_pairs_to_add)
            if len(parsed_id_pairs_to_add) > 0:
                valid_cs_node_counter += 1
        # end for cs_node_id

        # When grouped by cs node, results in 5673 multi-causal links across 
        # 423 cs nodes.

        # When grouped by action, Results in 28607 valid action links for 
        # 2046 actions, with 90836 multi-step causal links.

        #causal_links_directory = 'C:/Users/zevsm/Documents/GitHub/VisualNarrativeSensemaker/data/inputs/causal_links'

        # We now have multi causal links for each cs node.

        # For each cs node, print out its multi-causal links into its own
        # text file.
        #cs_node_links_to_parse = list(valid_cs_node_links.values())
        # Sort by how many multi-causal links each cs node has.
        sorted_cs_node_links = dict(sorted(valid_cs_node_links.items(),
                                    key=lambda item: len(item[1]),
                                    reverse=True))
        # There are 415 of these with 5209 valid causal links.
        # Think has the most multi-causal links with 256.
        cs_node_ids_to_parse = list(sorted_cs_node_links.keys())
        # Take the specified slice out of the list.
        cs_node_ids_to_parse = cs_node_ids_to_parse[lower:upper]

        # The maximum number of multi-step causal links' query strings 
        # we're allowed to place in a single text file.
        max_query_strings = 100
        file_counter = 0
        total_file_counter = 0

        for cs_node_id in cs_node_ids_to_parse:
            cs_node = self._data_handler.get_cs_node(cs_node_id)
            multi_links = valid_cs_node_links[cs_node_id]
            cs_node_query_strings = list()
            for multi_link in multi_links:
                # If we've reached the query string max per file, print the
                # file out.
                if len(cs_node_query_strings) >= max_query_strings:
                    file_name = f'{total_file_counter}_multi_causal_links_{cs_node.labels[0]}_{file_counter}.txt'
                    file_path = self._causal_links_directory + '/' + file_name
                    # Writelines doesn't actually write separate lines, so you have to
                    # put a newline after each line.
                    with open(file_path, 'w') as file:
                        file.writelines(s + '\n' for s in cs_node_query_strings)
                    # end with
                    file_counter += 1
                    total_file_counter += 1
                    cs_node_query_strings = list()
                # end if
                query_string = multi_link.get_query_string()
                # Prepend the multi-link's id to the start of the query string.
                #query_string = f'{multi_link.id} {query_string}'
                cs_node_query_strings.append(query_string)
            # end for multi_link
            # Print out this cs node's query strings into a text file.
            file_name = f'{total_file_counter}_multi_causal_links_{cs_node.labels[0]}'
            # If multiple files have been printed, add the file count to the
            # file name.
            if file_counter > 0:
                file_name += f'_{file_counter}'
            # end if
            file_name += '.txt'
            file_path = self._causal_links_directory + '/' + file_name
            # Writelines doesn't actually write separate lines, so you have to
            # put a newline after each line.
            with open(file_path, 'w') as file:
                file.writelines(s + '\n' for s in cs_node_query_strings)
            # end with
            total_file_counter += 1
            file_counter = 0
        # end for cs_node_id
        
        elapsed_time = timer() - start_time
        print(f'Done printing exclusively multi-step causal links.'
              + f' Time taken: {elapsed_time}s.'
              + f' \nNumber of cs nodes with valid links: {valid_cs_node_counter}.'
              + f' Number of valid causal links: {valid_causal_link_counter}.')

    # end print_multi_causal_links

    def read_multi_causal_links(self, search_labels: list[str]) -> list[MultiCausalLink]:
        '''
        Read parsed multi causal link files.
        '''
        #search_labels = ['eat']
        # Read in all the files prefixed with 'parsed' in the causal links
        # directory.
        all_link_strings = list()
        directory = self._causal_links_directory + '/parsed'
        # Maximum number of files to read
        file_count_max = 10
        file_count = 0
        for file_name in os.listdir(directory):
            # Split the file name and extract information from it.
            # 0 - 'parsed'
            # 1 - file number, int
            # 2, 3, 4 - 'multi_causal_links'
            # 5 - cs node label
            # 6 - cs node file number, int
            file_name_split = file_name.split('_')
            if not file_name_split[0] == 'parsed':
                continue
            # Look only for the cs nodes whose labels we're searching for.
            if not file_name_split[5] in search_labels:
                continue

            file_path = f'{directory}/{file_name}'
            with open(file_path, 'r') as file:
                for line in file.readlines():
                    # Skip blank lines.
                    if line == '':
                        continue
                    # Strip newlines.
                    line_stripped = line.rstrip('\n')
                    all_link_strings.append(line_stripped)
                # end for
            # end with
            file_count += 1
            if file_count >= file_count_max:
                break
            # end if
        # end for
        # Find a multi causal link for each link string.
        all_links = list()
        for link_string in all_link_strings:
            link_id = self._data_handler._multi_query_string_to_id_map[link_string]
            link = self._data_handler.get_multi_causal_link(link_id)
            if link is None:
                print('uh oh')
            all_links.append(link)
        # end for
        print('Done reading multi causal links :)')

        return all_links
    # end read_multi_causal_links
        
    # Utility functions

    def save_caches(self):
        self._data_handler._save_dynamic_caches()

    def _try_load_dict_cache(self, dict_name):
        '''
        Try and load a pickle cache of an image set generation dict from file.
        Returns an empty dict if the file is not found. 
        '''
        # Load from cache if possible.
        cache_dict_file_name = f'{dict_name}.pickle'
        cache_dict_file_directory = 'C:/Users/zevsm/Documents/GitHub/VisualNarrativeSensemaker/data/'
        cache_dict_file_path = cache_dict_file_directory + cache_dict_file_name
        cache_dict = dict()
        # Check if the cache file exists before trying to read it.
        if os.path.exists(cache_dict_file_path):
            cache_dict = pickle.load(open(cache_dict_file_path, 'rb'))
            return cache_dict
        # end if
        else:
            return dict()
    # end _try_load_dict_cache

    def _write_dict_cache(self, dict_name, dict_to_cache):
        '''
        Write a pickle cache of an image set generation dict to file.
        '''
        cache_dict_file_name = f'{dict_name}.pickle'
        cache_dict_file_directory = 'C:/Users/zevsm/Documents/GitHub/VisualNarrativeSensemaker/data/'
        cache_dict_file_path = cache_dict_file_directory + cache_dict_file_name
        with open(cache_dict_file_path, 'wb') as output_file:
            pickle.dump(dict_to_cache, output_file)
        # end with
    # end _write_dict_cache

    def _execute_query(self, query_string: str, query_data=None):
        """
        Execute a sql query in the concept_data database.

        Parameters
        ----------
        query_string : str
            The full string for the query.
        query_data : List, optional
            Any data used in the query. Default value is None.

            e.g., data to be inserted into a row.
        
        Returns
        -------
        list[tuple] | None
            The return values of the query as a list of tuples. If the operation 
            failed, returns None.
        """
        return_value = None
        # Open a connection to the database
        connection = sqlite3.connect(self._database_file_path)
        try:
            # Get a cursor to the database
            cursor = connection.cursor()
            # Execute the given sql command.
            if query_data == None:
                cursor.execute(query_string)
            else:
                cursor.execute(query_string, query_data)
            return_value = cursor.fetchall()
            # end if
            # Commit the changes to the database
            connection.commit()
        except Error as e:
            print(f'database_manager.execute_query : Error executing sql ' +
                f'query \"{query_string}\": {e}' +
                f'\ndata:{query_data}')
            return_value = None
        # end try
        # Whether the command was executed successfully or not,
        # close the connection.
        connection.close()
        return return_value
    # end execute_query

    def _execute_query_batch(self, query_string: str, query_data):
        """
        Execute a batch of queries. 

        Parameters
        ----------
        query_string : str
            The string for the query. Each query has to use the same string.
        
        query_data : list[list]
            A list of lists of data. Each entry is a single list of query data.
        
        Returns
        -------
        list[tuple] | None
            The return values of the as a list of tuples. If the operation 
            failed, returns None.
        """
        return_value = None
        # Open a connection to the database
        connection = sqlite3.connect(self._database_file_path)
        try:
            # Get a cursor to the database
            cursor = connection.cursor()
            # Execute the given sql command.
            if query_data == None:
                cursor.executemany(query_string)
            else:
                cursor.executemany(query_string, query_data)
            return_value = cursor.fetchall()
            # end if
            # Commit the changes to the database
            connection.commit()
        except Error as e:
            #print(f'Querier.execute_query_batch : Error executing sql ' +
            #      f'query \"{query_string}\": {e}' +
            #      f'\ndata:{query_data}')
            print(f'Querier.execute_query_batch : Error executing sql ' +
                  f'query \"{query_string}\": {e}')
            return_value = None
        # end try
        # Whether the command was executed successfully or not,
        # close the connection.
        connection.close()
        return return_value
    # end execute_query_batch

# end class ImageSetGenerator