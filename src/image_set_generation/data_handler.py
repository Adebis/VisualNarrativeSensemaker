import pickle
import os
import sys
import sqlite3
from sqlite3 import Error
from timeit import default_timer as timer

from commonsense.cskg_querier import CSKGQuerier
from commonsense.commonsense_data import CommonSenseNode
from input_handling.scene_graph_reader import SceneGraphReader
from input_handling.scene_graph_data import BoundingBox, Image

from image_set_generation.items import (ActionConcept, ObjectConcept, 
                                        ActionInstance, ObjectInstance,
                                        ImageInstance, CommonSenseNodeCluster,
                                        ActionObjectPair)
from image_set_generation.links import (CausalLink, MultiCausalLink, 
                                        ImageCausalLink, ImageMultiCausalLink)
from image_set_generation.database_table_generator import DatabaseTableGenerator

import constants as const

class DataHandler:

    _commonsense_querier: CSKGQuerier

    # Mapping of CommonSenseNode ids to lists of ActionConcept ids
    _cs_node_actions_map: dict[int, list[int]]

    # Lists of MultiCausalLinks keyed by the cs nodes they belong to.
    _cs_node_multi_causal_links_cache: dict

    # MultiCausalLinks keyed by their ids.
    _multi_causal_links: dict

    _causal_links: dict

    # Mapping of MultiCausalLink query strings to their ids.
    _multi_query_string_to_id_map: dict[str, int]


    # ObjectConcepts keyed by their object_label_id
    _object_concepts: dict[int, ObjectConcept]

    # ActionConcepts keyed by their action_label_id
    _action_concepts: dict[int, ActionConcept]

    # ActionInstances
    _action_instances: dict[int, ActionInstance]

    # ObjectInstances
    _object_instances: dict[int, ObjectInstance]

    # ImageInstances
    _image_instances: dict[int, ImageInstance]


    def __init__(self, load_caches = True):
        print('Initializing data handler...')
        start_time = timer()

        self._database_file_path = (f'{const.DATA_DIRECTORY}/image_set_generation.db')
        self._images_directory = 'C:/Users/zevsm/Documents/GitHub/VisualNarrativeSensemaker/data/inputs/images'
        self._annotations_directory = 'C:/Users/zevsm/Documents/GitHub/VisualNarrativeSensemaker/data/inputs/scene_graphs'
        self._commonsense_querier = CSKGQuerier(use_caches=load_caches)
        self._scene_graph_reader = SceneGraphReader(self._commonsense_querier)
        self._database_table_generator = DatabaseTableGenerator(
            commonsense_querier=self._commonsense_querier,
            scene_graph_reader=self._scene_graph_reader,
            database_file_path=self._database_file_path,
            images_directory=self._images_directory
        )
        #if load_caches:
        #    self._load_or_make_caches()
        if load_caches:
            self._populate_caches()

        elapsed_time = timer() - start_time
        print(f'Done initializing data handler. Time taken: {elapsed_time}s.')
    # end __init__

    # Cached data handling
    
    def _save_dynamic_caches(self):
        '''
        Save caches that are filled or changed over the course of the program.
        '''
        print('Writing dynamic cache dicts to file...')
        start_time = timer()
        self._commonsense_querier.save()

        self._multi_causal_links = self._try_load_dict_cache('multi_causal_links')
        self._causal_links = self._try_load_dict_cache('causal_links')
        
        # Don't write the instance caches.
        # The image instance cache is huge (5k entries == 2gigs), so we don't
        # want to save it.
        # Action and object instances are tied to their image instances anyway,
        # so there's no point in saving their caches separately. 
        #self._write_dict_cache('object_instances', self._object_instances)
        #self._write_dict_cache('action_instances', self._action_instances)
        #self._write_dict_cache('image_instances', self._image_instances)
        
        print(f'Done writing dynamic cache dicts to file.' 
              + f' Time taken: {timer() - start_time}s.')
    # end _save_dynamic_caches

    def _save_static_caches(self):
        '''
        Save caches that are built once and don't change over the course of
        the program.
        '''
        print('Writing static cache dicts to file...')
        start_time = timer()
        self._write_dict_cache('cs_node_actions_map', self._cs_node_actions_map)

        self._write_dict_cache('object_concepts', self._object_concepts)
        

        self._write_dict_cache('action_concepts', self._action_concepts)
        
        #self._write_dict_cache('action_instances', self._action_instances)
        #self._write_dict_cache('object_instances', self._object_instances)
        #self._write_dict_cache('image_instances', self._image_instances)
        elapsed_time = timer() - start_time
        print(f'Done! Time taken: {elapsed_time}s.')
    # end _save_static_caches

    # Cached data generation

    def _populate_caches(self):
        '''
        Tries to load all dynamic and static caches.

        Any static cache that cannot be loaded from file is remade. 
        The static caches are cs node actions map, ObjectConcepts, and 
        ActionConcepts.
        '''

        # Dynamic caches that are made while the program is running and saved
        # at the end.
        self._multi_causal_links = self._try_load_dict_cache('multi_causal_links')
        self._causal_links = self._try_load_dict_cache('causal_links')

        # We aren't saving the instance caches, so don't try to load them.
        # Just set them to the empty dict.
        #self._object_instances = self._try_load_dict_cache('object_instances')
        #self._action_instances = self._try_load_dict_cache('action_instances')
        #self._image_instances = self._try_load_dict_cache('image_instances')

        self._object_instances = dict()
        self._action_instances = dict()
        self._image_instances = dict()

        # Static caches that are made once and saved to file.
        # A mapping of ids of cs nodes to the ids of the action concepts that 
        # they belong to. 
        cs_node_actions_map = self._try_load_dict_cache('cs_node_actions_map')
        if len(cs_node_actions_map) == 0:
            cs_node_actions_map = self._make_cs_node_actions_map()
            self._write_dict_cache('cs_node_actions_map', cs_node_actions_map)
        # end if
        self._cs_node_actions_map = cs_node_actions_map

        # Get or make all ObjectConcepts.
        # There are 8315 ObjectConcepts from 88919 rows in the object_cs_nodes
        # table.
        object_concepts: dict[int, ObjectConcept] = self._try_load_dict_cache('object_concepts')
        if len(object_concepts) == 0:
            object_concepts = self._make_object_concepts()
            self._write_dict_cache('object_concepts', object_concepts)
        # end if
        self._object_concepts = object_concepts

        # Get or make all ActionConcepts.
        # There are 4426 ActionConcepts from 38675 rows in the action_cs_nodes
        # table.
        action_concepts: dict[int, ActionConcept] = self._try_load_dict_cache('action_concepts')
        if len(action_concepts) == 0:
            action_concepts = self._make_action_concepts()
            self._write_dict_cache('action_concepts', action_concepts)
        # end if
        self._action_concepts = action_concepts

    # end _populate_image_data

    def _make_object_concepts(self) -> dict[int, ObjectConcept]:
        '''
        Makes a dictionary of ObjectConcepts, keyed by their object label id.
        '''
        print('Making object concepts...')
        timers = dict()
        timers['start'] = timer()
        # Key: object_label_id, int
        # Value: ObjectConcept
        object_concepts: dict[int, ObjectConcept] = dict()
        # Get all the rows from object_cs_nodes.
        query = ('''
            SELECT * FROM object_cs_nodes
            GROUP BY object_concept_id
        ''')
        rows = self._execute_query(query)
        # Store the cs nodes for each object.
        # Key: object_concept_id, int
        # Value: list[CommonSenseNode]
        object_cs_nodes: dict[int, list[CommonSenseNode]] = dict()
        # Store the concept names for each object.
        # Key: object_concept_id
        # Value: object_concept_name
        object_concept_names: dict[int, str] = dict()
        # Each row has:
        #   object_concept_id
        #   object_concept_name
        #   cs_node_id
        #   cs_node_uri
        for row in rows:
            object_concept_id = row[0]
            object_concept_name = row[1]
            cs_node_id = row[2]
            # Get all the cs node.
            cs_nodes = self._commonsense_querier.get_node(cs_node_id)
            # Populate object_cs_nodes
            if not object_concept_id in object_cs_nodes:
                object_cs_nodes[object_concept_id] = list()
            # end if
            object_cs_nodes[object_concept_id].append(cs_nodes)
            # Populate object_concept_names
            if not object_concept_id in object_concept_names:
                object_concept_names[object_concept_id] = object_concept_name
            # end if
        # end for

        # For each object concept id and name, make an ObjectConcept.
        for object_concept_id, object_concept_name in object_concept_names.items():
            # Get all the actions this object's paired with, as well as the
            # ids of the images in which they're paired.
            #paired_actions = self._get_paired_actions(object_label_id)
            # Gets the images that this object label occurs in, as well as the
            # number of times it occurs in each image.
            #image_occurrences = self._get_image_object_occurrences(object_label_id)

            object_concept = ObjectConcept(
                id=object_concept_id,
                name=object_concept_name,
                cs_nodes=object_cs_nodes[object_concept_id]
            )
            object_concepts[object_concept_id] = object_concept
        # end for

        elapsed_time = timer() - timers['start']
        print(f'Done making object concepts. Time taken: {elapsed_time}s.')
        return object_concepts
    # end _make_object_concepts

    def _make_cs_node_actions_map(self) -> dict[int, list[int]]:
        '''
        Makes a mapping of cs node ids to lists of action ids.
        '''
        print('Making cs_node_actions_map...')
        print('Reading rows from action_cs_nodes...')
        timers = dict()
        timers['start_rows_time'] = timer()
        # Get all the rows from action_cs_nodes.
        query = ('''
            SELECT * FROM action_cs_nodes
        ''')
        rows = self._execute_query(query)

        # Map cs nodes to the ids of their action concepts.
        # Key: cs node id, int
        # Value: list of action concept ids, list[int]
        cs_node_actions_map: dict[int, list[int]] = dict()
        for row in rows:
            action_concept_id = row[0]
            cs_node_id = row[2]
            
            # Populate cs node actions map.
            if not cs_node_id in cs_node_actions_map:
                cs_node_actions_map[cs_node_id] = list()
            # end if
            cs_node_actions_map[cs_node_id].append(action_concept_id)
        # end for
        elapsed_time = timer() - timers['start_rows_time']
        print(f'Done reading rows from action_cs_nodes.'
              + f' Time taken: {elapsed_time}s.')
        print(f'Number of rows read: {len(rows)}.')
        print(f'Number of cs nodes: {len(cs_node_actions_map)}.')
        print('Done making cs_node_actions_map')
        return cs_node_actions_map
    # end _make_cs_node_actions_map

    def _make_action_concepts(self) -> dict[int, ActionConcept]:
        '''
        Gets all the ActionConcepts in a dictionary, keyed by action_concept_id.

        Uses _cs_node_actions_map.
        '''
        
        # Fetches actions from database.
        print('Making action concepts...')
        timers = dict()
        timers['start_time'] = timer()
        # Key: action_concept_id, int
        # Value: ActionConcept
        action_concepts: dict[int, ActionConcept] = dict()

        print('Reading rows from action_cs_nodes...')
        timers['start_rows_time'] = timer()
        # Get all the rows from action_cs_nodes.
        query = ('''
            SELECT * FROM action_cs_nodes
        ''')
        rows = self._execute_query(query)

        # Each row has:
        #   action_concept_id
        #   action_concept_name
        #   cs_node_id
        #   cs_node_uri
        # Store all the cs nodes for each action.
        # Key 1: action_concept_id, int
        # Key 2: cs_node_id
        # Value: CommonSenseNode
        action_cs_nodes: dict[int, dict[int, CommonSenseNode]] = dict()
        # Store all the names for each action concept.
        # Key: action_concept_id, int
        # Value: action_concept_name, str
        action_concept_names: dict[int, str] = dict()
        for row in rows:
            action_concept_id = row[0]
            action_concept_name = row[1]
            cs_node_id = row[2]
            # Get the cs node for this row.
            cs_node = self._commonsense_querier.get_node(cs_node_id)
            
            # Populate action_cs_nodes.
            if not action_concept_id in action_cs_nodes:
                action_cs_nodes[action_concept_id] = dict()
            # end if
            action_cs_nodes[action_concept_id][cs_node_id] = cs_node

            # Populate action concept names.
            if not action_concept_id in action_concept_names:
                action_concept_names[action_concept_id] = action_concept_name
            # end if
        # end for
        elapsed_time = timer() - timers['start_rows_time']
        print(f'Done reading rows from action_cs_nodes.'
              + f' Time taken: {elapsed_time}s.')
        print(f'Number of rows read: {len(rows)}.')
        print(f'Number of actions: {len(action_concept_names)}.')

        print('Building ActionConcepts...')
        timers['start_action_concepts_time'] = timer()
        action_counter = 0
        causal_links_counter = 0
        multi_causal_links_counter = 0
        # Make an ActionConcepts for each action concept name and id.
        for action_concept_id, cs_nodes in action_cs_nodes.items():
            action_concept_name = action_concept_names[action_concept_id]

            #instances = self._get_action_instances(action_label_id)
            # Get the ids of all of this action's instances, as well as the ids
            # of the images those instances appear in.
            query = ('''
                SELECT DISTINCT image_id, action_instance_id
                FROM image_actions
                WHERE action_concept_id = ?
            ''')
            rows = self._execute_query(query, [action_concept_id])
            # Key: image id
            # Value: set of action concept ids
            action_instance_ids: dict[int, set[int]] = dict()
            for row in rows:
                image_id = row[0]
                action_instance_id = row[1]
                if not image_id in action_instance_ids:
                    action_instance_ids[image_id] = set()
                action_instance_ids[image_id].add(action_instance_id)
            # end for

            # Gets sets of action instance ids keyed by the id of the concept
            # of the action's subject or object and the id of the image that
            # the instance appears in.
            by_subject, by_object = self._get_paired_objects(action_concept_id)

            action = ActionConcept(
                id=action_concept_id,
                name=action_concept_name,
                cs_nodes=cs_nodes,
                action_links=dict(),
                instances_by_subject=by_subject,
                instances_by_object=by_object,
                action_instance_ids=action_instance_ids
            )

            # Get all the single-step causal links for this action.
            # This means getting all the single-step casual links for this
            # action's cs nodes.
            for cs_node in cs_nodes.values():
                cs_node_links = self.get_causal_links(cs_node)
                # Add this cs node's causal links to the action's ActionLinks.
                for causal_link in cs_node_links:
                    # Get the cs node at the other end of each link.
                    other_cs_node = causal_link.get_other_cs_node(cs_node)
                    # If the other cs node is not associated with any actions,
                    # skip this causal link.
                    if not other_cs_node.id in self._cs_node_actions_map:
                        continue
                    other_action_ids = self._cs_node_actions_map[other_cs_node.id]
                    # Determine what the causal direction of the link will be
                    # with the current action as the source and the other action
                    # as the target.
                    direction = causal_link.get_causal_flow_direction(cs_node)

                    for other_action_id in other_action_ids:
                        action.add_causal_link(
                            causal_link=causal_link,
                            other_action_concept_id=other_action_id,
                            direction=direction
                        )
                    # end for other_action_id
                    causal_links_counter += 1
                # end for causal_link
            # end for

            # Get all the multi-step causal links for this action.
            # This means getting all the multi-step causal links for this
            # action's cs nodes.
            for cs_node in cs_nodes.values():
                cs_node_links = self.get_multi_causal_links(cs_node)
                # Add this cs node's multi causal links to the action's 
                # ActionLinks.
                for multi_causal_link in cs_node_links:
                    # Get the cs node at the other end of each link.
                    other_cs_node = multi_causal_link.get_other_cs_node(cs_node)
                    # If the other cs node is not associated with any actions,
                    # skip this causal link.
                    if not other_cs_node.id in self._cs_node_actions_map:
                        continue
                    other_action_ids = self._cs_node_actions_map[other_cs_node.id]
                    # Determine what the causal direction of the link will be
                    # with the current action as the source and the other action
                    # as the target.
                    direction = multi_causal_link.get_causal_flow_direction(cs_node)
                    for other_action_id in other_action_ids:
                        action.add_multi_causal_link(
                            multi_causal_link=multi_causal_link,
                            other_action_concept_id=other_action_id,
                            direction=direction
                        )
                    # end for
                # end for multi_causal_link
                multi_causal_links_counter += 1
            # end for

            # Add the finished action concepts to the dictionary.
            action_concepts[action_concept_id] = action

            action_counter += 1
            if action_counter % 100 == 1:
                elapsed_time = timer() - timers['start_action_concepts_time']
                print(f'Action {action_counter}/{len(action_concept_names)}.'
                      + f' Elapsed time: {elapsed_time}s.')
                print(f'Average time per action: {elapsed_time/action_counter}s.')
                print(f'Causal links: {causal_links_counter}.'
                      + f' Multi-causal links: {multi_causal_links_counter}.')
            # end if
        # end for
        elapsed_time = timer() - timers['start_action_concepts_time']
        print(f'Done making ActionConcepts for {len(action_concepts)} actions.'
              + f' Elapsed time: {elapsed_time}s.')
        print(f'Average time per action: {elapsed_time/action_counter}s.')
        print(f'Causal links: {causal_links_counter}.'
              + f' Multi-causal links: {multi_causal_links_counter}.')

        print(f'Memory size of of actions in bytes: {sys.getsizeof(action_concepts)}')

        return action_concepts
    # end _make_action_concepts

    def _make_image_instance(self, image_id: int) -> ImageInstance:
        '''
        Makes an ImageInstance for a single image, identified by its id.
        Also makes the ImageInstances ObjectInstances and ActionInstances.

        Uses the _object_concepts and _action_concepts caches.

        Returns the ImageInstance.
        '''
        # Make all of the image's ObjectInstances.
        query = ('''
            SELECT * FROM image_objects
            WHERE image_id = ?
        ''')
        rows = self._execute_query(query, [image_id])
        # Key: object_instance_id, int
        # Value: ObjectInstance
        object_instances: dict[int, ObjectInstance] = dict()
        # Key: object_concept_id, int
        # Value: list of object instances.
        objects_by_concept: dict[int, list[ObjectInstance]] = dict()
        for row in rows:
            # 1 - object_instance_id
            object_instance_id = row[1]
            # 2 - object_instance_name
            object_instance_name = row[2]
            # 3 - object_concept_id
            object_concept_id = row[3]
            # 5 - bbox_x
            bbox_x = row[5]
            # 6 - bbox_y
            bbox_y = row[6]
            # 7 - bbox_h
            bbox_h = row[7]
            # 8 - bbox_w
            bbox_w = row[8]
            bounding_box = BoundingBox(
                h=bbox_h,
                w=bbox_w,
                x=bbox_x,
                y=bbox_y
            )
            # 9 - attributes, '|' separated list.
            attributes = set()
            color_attributes = set()
            raw_attributes = row[9].split('|')
            # Normalize the attributes and look for any color attributes. 
            for attribute in raw_attributes:
                # Convert to lower case.
                attribute = str.lower(attribute)
                # Remove leading and trailing spaces.
                attribute = attribute.lstrip()
                attribute = attribute.rstrip()
                # Split the attribute by space and see if it has any color
                # attributes in it.
                split_attribute = attribute.split(' ')
                for part in split_attribute:
                    if part in const.COLOR_ATTRIBUTES:
                        color_attributes.add(part)
                # See if the attribute is a color attribute.
                if attribute in color_attributes:
                    color_attributes.add(attribute)
                attributes.add(attribute)
            # end for

            object_instance = ObjectInstance(
                id=object_instance_id,
                name=object_instance_name,
                object_concept_id=object_concept_id,
                image_id=image_id,
                bounding_box=bounding_box,
                attributes=attributes,
                color_attributes=color_attributes
            )
            object_instances[object_instance_id] = object_instance
            if not object_concept_id in objects_by_concept:
                objects_by_concept[object_concept_id] = list()
            objects_by_concept[object_concept_id].append(object_instance)
        # end for

        # Make all of the image's ActionInstances (without subject or object
        # roles filled in).
        query = ('''
            SELECT * FROM image_actions
            WHERE image_id = ?
        ''')
        rows = self._execute_query(query, [image_id])
        # Key: action_instance_id, int
        # Value: ActionInstance
        action_instances: dict[int, ActionInstance] = dict()
        # Key: action_concept_id, int
        # Value: list[ActionInstance]
        actions_by_concept: dict[int, list[ActionInstance]] = dict()
        for row in rows:
            # 1 - action_instance_id
            action_instance_id = row[1]
            # 2 - action_instance_name
            action_instance_name = row[2]
            # 3 - action_concept_id
            action_concept_id = row[3]

            action_instance = ActionInstance(
                id=action_instance_id,
                name=action_instance_name,
                action_concept_id=action_concept_id,
                image_id=image_id,
                subject=None,
                object_=None,
                subject_concept_id=None,
                object_concept_id=None
            )
            action_instances[action_instance_id] = action_instance

            if not action_concept_id in actions_by_concept:
                actions_by_concept[action_concept_id] = list()
            actions_by_concept[action_concept_id].append(action_instance)
        # end for

        # Fill in subject and object roles for each ActionInstance by reading
        # the image_action_object_pairs table.
        query = ('''
            SELECT * FROM image_action_object_pairs
            WHERE image_id = ?
        ''')
        rows = self._execute_query(query, [image_id])
        # Fill in the action instance ids by subject concept id and object
        # concept id dicts as well.
        actions_by_subject: dict[int, list[int]] = dict()
        actions_by_object: dict[int, list[int]] = dict()
        for row in rows:
            # 1 - action_instance_id
            action_instance_id = row[1]
            # 3 - object_instance_id
            object_instance_id = row[3]
            # 5 - object_role, either 'subject' or 'object'
            object_role = row[5]
            if object_role == 'subject':
                action_instances[action_instance_id].subject = object_instances[object_instance_id]
                if not object_instance_id in actions_by_subject:
                    actions_by_subject[object_instance_id] = list()
                actions_by_subject[object_instance_id].append(action_instance_id)
            elif object_role == 'object':
                action_instances[action_instance_id].object_ = object_instances[object_instance_id]
                if not object_instance_id in actions_by_object:
                    actions_by_object[object_instance_id] = list()
                actions_by_object[object_instance_id].append(action_instance_id)
            # end elif
        # end for

        # Make the image instance.
        # Make an Image object for this ImageInstance.
        image_file_path = (f'{const.IMAGES_DIRECTORY}/{image_id}.jpg')
        # If the jpeg doesn't exist, try a png
        if not os.path.isfile(image_file_path):
            image_file_path = (f'{const.IMAGES_DIRECTORY}/{image_id}.png')
        # If that still doesn't work, give up.
        if not os.path.isfile(image_file_path):
            print(f'DataHandler._make_image_instance : Could not find ' +
                    f'image file for image {image_id}.')
        # end if
        image = Image(id=image_id, index=0, file_path=image_file_path)
        
        image_instance = ImageInstance(
            id=image_id,
            object_instances=object_instances,
            objects_by_concept=objects_by_concept,
            action_instances=action_instances,
            actions_by_concept=actions_by_concept,
            actions_by_subject=actions_by_subject,
            actions_by_object=actions_by_object,
            image=image
        )

        return image_instance
    # end _make_image_instance


    def _make_action_instance(self, action_instance_id):
        '''
        
        '''
        return

    # Helper functions for cache making functions.

    def _get_paired_actions(self, object_label_id: int) -> dict[int, list[int]]:
        '''
        Gets all the actions paired with an object label, as well as the
        ids of the images they're paired in.
        '''
        query = ('''
            SELECT * FROM image_object_action_pairs
            WHERE object_label_id = ?
        ''')
        rows = self._execute_query(query, [object_label_id])
        # Key: action_label_id, int
        # Value: list of image_ids
        paired_actions: dict[int, list[int]] = dict()
        # Each row has:
        #   image_id
        #   action_label
        #   action_label_id
        #   object_label
        #   object_label_id
        for row in rows:
            image_id = row[0]
            action_label_id = row[2]
            if not action_label_id in paired_actions:
                paired_actions[action_label_id] = list()
            paired_actions[action_label_id].append(image_id)
        # end for

        return paired_actions
    # end _get_paired_actions

    def _get_image_object_occurrences(self, object_label_id: int) -> dict[int, int]:
        '''
        Gets all of the images that an object occurs in, as well as the number
        of times it occurs in each image.
        '''
        query = ('''
            SELECT * FROM image_object_action_pairs
            WHERE object_label_id = ?
        ''')
        rows = self._execute_query(query, [object_label_id])
        # Key: image_id, int
        # Value: number of times the object label occurs in the image, int
        image_occurrences = dict()
        # Each row has:
        #   image_id
        #   action_label
        #   action_label_id
        #   object_label
        #   object_label_id
        for row in rows:
            image_id = row[0]
            if not image_id in image_occurrences:
                image_occurrences[image_id] = 0
            # end if
            image_occurrences[image_id] += 1
        # end for
        return image_occurrences
    # end _get_image_object_occurrences

    def _get_paired_objects(self, action_concept_id: int):
        '''
        Gets all the objects paired with an action concept id, as well as the
        ids of the images they're paired in. Organize by role ('subject' or
        'object'). 

        The first dict is the subjects dict. The second dict is the objects dict.
        '''
        # Gets all the rows from image_object_action_pairs with an action
        # that's an instance of the action concept whose id was passed in. 
        # Query takes about 600ms.
        query = ('''
            WITH action_lookup AS (
                SELECT DISTINCT action_instance_id, action_concept_id
                FROM image_actions
                WHERE action_concept_id = ?
            )

            SELECT image_id, action_instance_id, object_instance_id, 
                object_role, action_concept_id, object_concept_id 
            FROM (
                SELECT DISTINCT * FROM image_action_object_pairs
                INNER JOIN action_lookup
                ON image_action_object_pairs.action_instance_id = action_lookup.action_instance_id
                INNER JOIN image_objects
                ON image_action_object_pairs.object_instance_id = image_objects.object_instance_id
            )
        ''')
        rows = self._execute_query(query, [action_concept_id])
        # Key 1: object concept id, int
        # Key 2: image id, int
        # Value: set of action instance ids
        paired_subjects: dict[int, dict[int, set[int]]] = dict()
        # Key 1: object concept id, int
        # Key 2: image id, int
        # Value: set of action instance ids
        paired_objects: dict[int, dict[int, set[int]]] = dict()
        for row in rows:
            # 0 - image_id
            image_id = row[0]
            # 1 - action_instance_id
            action_instance_id = row[1]
            # 2 - object_instance_id
            object_instance_id = row[2]
            # 3 - object_role ('subject' or 'object')
            object_role = row[3]
            # 4 - action_concept_id.
            # 5 - object_concept_id.
            object_concept_id = row[5]

            if object_role == 'subject':
                if not object_concept_id in paired_subjects:
                    paired_subjects[object_concept_id] = dict()
                if not image_id in paired_subjects[object_concept_id]:
                    paired_subjects[object_concept_id][image_id] = set()
                paired_subjects[object_concept_id][image_id].add(action_instance_id)
            elif object_role == 'object':
                if not object_concept_id in paired_objects:
                    paired_objects[object_concept_id] = dict()
                if not image_id in paired_objects[object_concept_id]:
                    paired_objects[object_concept_id][image_id] = set()
                paired_objects[object_concept_id][image_id].add(action_instance_id)
            # end if
        # end for

        return paired_subjects, paired_objects
    # end _get_paired_objects

    def _multi_causal_link_from_row(self, row: dict) -> MultiCausalLink:
        '''
        Makes a MultiCausalLink from a row in the multi_causal_links database
        table.
        '''
        source_cs_node = self._commonsense_querier.get_node(row[0])
        middle_cs_node = self._commonsense_querier.get_node(row[2])
        target_cs_node = self._commonsense_querier.get_node(row[4])
        # Fetch the all the cs node's edges. This caches these edges so we can
        # fetch them by id later. 
        source_cs_node_edges = self._commonsense_querier.get_edges(source_cs_node.id)
        middle_cs_node_edges = self._commonsense_querier.get_edges(middle_cs_node.id)
        target_cs_node_edges = self._commonsense_querier.get_edges(target_cs_node.id)

        source_middle_edge = self._commonsense_querier.get_edge(row[6])
        middle_target_edge = self._commonsense_querier.get_edge(row[9])

        # DEBUG
        if source_middle_edge is None or middle_target_edge is None:
            print('Null edges!')

        direction = row[12]
        return MultiCausalLink(
            source_cs_node=source_cs_node,
            middle_cs_node=middle_cs_node,
            target_cs_node=target_cs_node,
            source_middle_edge=source_middle_edge,
            middle_target_edge=middle_target_edge,
            direction=direction
        )
    # end _multi_causal_link_from_row

    def _get_image_action_object_pairs(self, image_id: int):
        """
        Gets all of the image's actions and the the objects paired with those.
        Returns a list of dicts in the following format:
        Keys:
            'action_label' - A tag for the action in the form of {label}.
            'object_label' - A tag for the object in the form of {label}.
            'action_cs_nodes' - A list of the cs nodes for this action.
            'object_cs_nodes' -  A list of the cs nodes for this object.
        """
        action_object_pairs = list()
        knowledge_graph = self._scene_graph_reader.read_scene_graphs([image_id])
        actions = knowledge_graph.actions
        for action in actions.values():
            # Actions are stored as the action's label.
            #action_tag = f'{action.label}_{action.id}_{image_id}'
            action_label = f'{action.label}'
            # Concepts are divided into a dictionary of CommonsenseNodes,
            # keyed by the node's ID (which is its key in the commonsense node
            # database). The value is the string URI of the CommonsenseNode.
            action_cs_nodes = list()
            for concept in action.concepts:
                for cs_node in concept.commonsense_nodes.values():
                    action_cs_nodes.append(cs_node)
                # end for
            # end for

            for object_id, obj_ in action.objects.items():
                #object_tag = f'{obj_.label}_{obj_.id}_{image_id}'
                object_label = f'{obj_.label}'
                object_cs_nodes = list()
                for concept in obj_.concepts:
                    for cs_node in concept.commonsense_nodes.values():
                        object_cs_nodes.append(cs_node)
                    # end for
                # end for

                object_role = ''
                if action.is_subject(obj_):
                    object_role = 'subject'
                elif action.is_object(obj_):
                    object_role = 'object'
                else:
                    print('DataHandler._get_image_action_object_pairs : Error!'
                          + ' object is neither the subject nor object of'
                          + ' its action.')

                action_object_pair = dict()
                action_object_pair['action_label'] = action_label
                action_object_pair['object_label'] = object_label
                action_object_pair['action_cs_nodes'] = action_cs_nodes
                action_object_pair['object_cs_nodes'] = object_cs_nodes
                action_object_pair['action_name'] = action.name
                action_object_pair['object_name'] = obj_.name
                action_object_pair['object_role'] = object_role
                action_object_pairs.append(action_object_pair)
            # end for
        # end for
            
        return action_object_pairs
    # end _get_image_action_object_pairs


    # Accessors

    def get_image_action_object_pairs(self, image_id: int):
        '''
        Gets all of the ActionObjectPairs for this image id from the
        image_action_object_pairs table.
        '''
        query = ('''
            SELECT * FROM image_action_object_pairs
            WHERE image_id = ?
        ''')
        rows = self._execute_query(query, [image_id])
        pairs = [ActionObjectPair(row) for row in rows]
        return pairs
    # end get_image_action_object_pairs

    def get_object_concept(self, object_concept_id: int) -> ObjectConcept:
        return self._object_concepts[object_concept_id]
    # end get_object

    def get_action_concept(self, action_concept_id: int) -> ActionConcept:
        return self._action_concepts[action_concept_id]
    # end get_action

    def get_action_concepts(self, image_instance: ImageInstance) -> list[ActionConcept]:
        '''
        Gets all of the actions concepts for the action instances in the
        image instance passed in.
        '''
        concepts = list()
        for instance in image_instance.action_instances.values():
            concepts.append(self._action_concepts[instance.action_concept_id])
        return concepts
    # end get_action_concepts

    def get_cs_node(self, cs_node_id: int):
        return self._commonsense_querier.get_node(cs_node_id)
    # end get_cs_node

    def get_all_action_concept_ids(self) -> list[int]:
        return list(self._action_concepts.keys())
    # end get_all_action_ids

    def get_cs_node_action_concepts(self, cs_node: CommonSenseNode) -> list[ActionConcept]:
        '''
        Gets a list of all the ActionConcepts for a cs node.
        '''
        if not cs_node.id in self._cs_node_actions_map:
            return list()
        action_ids = self._cs_node_actions_map[cs_node.id]
        actions = [self._action_concepts[id] for id in action_ids]
        return actions
    # end get_cs_node_actions

    def get_action_concept_from_instance(self, action_instance_id: int):
        '''
        Gets the ActionConcept for an ActionInstance identified by its id.
        '''
        # Get the action instance's concept's id.
        query = ('''
            SELECT DISTINCT action_concept_id
            FROM image_actions
            WHERE action_instance_id = ?
        ''')
        # Query takes <10ms
        row = self._execute_query(query, [action_instance_id])
        action_concept_id = row[0][0]
        action_concept = self._action_concepts[action_concept_id]
        return action_concept
    # end get_action_instance_action_concept

    def get_all_action_cs_node_ids(self) -> list[int]:
        '''
        Gets a list of the ids of all the cs nodes associated with actions. 
        '''
        return list(self._cs_node_actions_map.keys())
    # end get_all_action_cs_node_ids

    def get_causal_links(self, cs_node: CommonSenseNode) -> list[CausalLink]:
        '''
        Get all the causal links for a CommonSenseNode.

        Checks the _causal_links cache first. If it's not there, checks all
        of the node's edges for causal edges and makes a causal link for each
        one of them.
        '''
        if cs_node.id in self._causal_links:
            return self._causal_links[cs_node.id]
        # end if
        self._causal_links[cs_node.id] = list()
        edges = self._commonsense_querier.get_edges(cs_node.id)
        for edge in edges:
            if edge.get_relationship() in const.COHERENCE_TO_RELATIONSHIP['causal']:
                # Use the edge's source and target nodes as the source and
                # target nodes of the CausalLink
                source_cs_node = self._commonsense_querier.get_node(edge.start_node_id)
                target_cs_node = self._commonsense_querier.get_node(edge.end_node_id)
                # The edge direction is the causal relationship direction of the edge.
                direction = const.CAUSAL_RELATIONSHIP_DIRECTION[edge.get_relationship()]
                link = CausalLink(source_cs_node=source_cs_node,
                                  target_cs_node=target_cs_node,
                                  edge=edge,
                                  direction=direction)
                self._causal_links[cs_node.id].append(link)
        # end for
        return self._causal_links[cs_node.id]
    # end _get_causal_links

    def get_multi_causal_links(self, cs_node: CommonSenseNode) -> list[MultiCausalLink]:
        '''
        Gets all the multi-step causal links involving this cs node.

        This gets all the multi causal links where the cs node is either the
        source or the target cs node of the link.

        Checks the multi_causal_links cache first. If it's not there, fetches
        them from the multi_causal_links table in the database.
        '''
        if cs_node.id in self._multi_causal_links:
            return self._multi_causal_links[cs_node.id]
        self._multi_causal_links[cs_node.id] = list()
        query = ('''
            SELECT * FROM multi_causal_links
            WHERE source_cs_node_id = ?
            OR target_cs_node_id = ?
        ''')
        links: list[MultiCausalLink] = list()
        rows = self._execute_query(query, [cs_node.id, cs_node.id])
        for row in rows:
            links.append(self._multi_causal_link_from_row(row))
        # end for
        self._multi_causal_links[cs_node.id] = links

        return self._multi_causal_links[cs_node.id]
    # end _get_multi_causal_links

    def get_image_instance(self, image_id: int):
        '''
        Returns the ImageInstance for an image identified by its id.

        Tries to fetch it from the _image_instances cache first. If it's not
        there, calls _make_image_instance to make it, then caches the
        ImageInstance.
         
        Since ObjectInstances and ActionInstances only appear in their 
        ImageInstance, also caches the ImageInstance's ObjectInstances and 
        ActionInstances.
        '''
        if not image_id in self._image_instances:
            image_instance = self._make_image_instance(image_id)
            self._image_instances[image_id] = image_instance
            # Cache the object and action instances as well.
            for object_instance in image_instance.object_instances.values():
                self._object_instances[object_instance.id] = object_instance
            for action_instance in image_instance.action_instances.values():
                self._action_instances[action_instance.id] = action_instance
            # end for
        # end if
        return self._image_instances[image_id]
    # end _get_image_instance

    def get_action_instances(self, search_term: str):
        '''
        Get all action instances for a search term. 
        '''
        # First, get all the action-object pairs for that term's actions.
        pairs = self.get_action_object_pairs(search_term)
        return self.get_action_instances_from_pairs(pairs)
    # get_action_instances

    def get_action_instances_for_concept(self, action_concept: ActionConcept):
        '''
        Gets all the ActionInstances for an ActionConcept.
        '''
        pairs = self.get_action_object_pairs_for_concept(action_concept.id)
        return self.get_action_instances_from_pairs(pairs)
    # end get_action_instances_from_concept

    def get_action_instances_from_pairs(self, pairs: list[ActionObjectPair]):
        '''
        Gets or makes all the action instances from a set of ActionObjectPairs.
        '''
        # Key: action instance id.
        # Value: ActionInstance object.
        new_instances: dict[int, ActionInstance] = dict()
        return_instances: dict[int, ActionInstance] = dict()
        # Go through each one.
        for pair in pairs:
            id = pair.action_instance_id
            # If it's already in the action instances map, don't make it again.
            if id in self._action_instances:
                return_instances[id] = self._action_instances[id]
                continue
            if not id in new_instances:
                new_instances[id] = ActionInstance(
                    id=id,
                    name=pair.action_instance_name,
                    action_concept_id=pair.action_concept_id,
                    image_id=pair.image_id,
                    subject=None,
                    object_=None,
                    subject_concept_id=None,
                    object_concept_id=None
                )
            # Fill the action instance's subject or object role according to
            # what's in the pair.
            if pair.object_role == 'subject':
                new_instances[id].subject_concept_id = pair.object_concept_id
            elif pair.object_role == 'object':
                new_instances[id].object_concept_id = pair.object_concept_id
        # end for
        # Update the overall dict of action instances with the ones made here.
        self._action_instances.update(new_instances)
        # Update the return dict as well.
        return_instances.update(new_instances)
        return return_instances
    # end make_action_instances_from_pairs

    def get_action_instance(self, action_instance_id: int) -> ActionInstance | None:
        '''
        Returns the ActionInstance identified by its id.

        Fetches it from the _action_instances cache. If it's not there,
        returns None.
        '''
        if action_instance_id in self._action_instances:
            return self._action_instances[action_instance_id]
        else:
            return None
    # end get_action_instance

    def get_object_instance(self, object_instance_id: int) -> ObjectInstance | None:
        '''
        Returns the ObjectInstance identified by its id.

        Fetches it from the _object_instances cache. If it's not there,
        returns None.
        '''
        if object_instance_id in self._object_instances:
            return self._object_instances[object_instance_id]
        else:
            return None
    # end get_object_instance

    def get_cs_node_cluster(self, uri: str) -> CommonSenseNodeCluster:
        '''
        Makes a CommonSenseNodeCluster from a cs node uri.
        '''
        # Get any cs node that starts with the search uri.
        # These are all the cs nodes in the search uri's cs node's cluster.
        query = (
            'SELECT DISTINCT cs_node_id, cs_node_uri FROM action_cs_nodes'
            + f'\nWHERE cs_node_uri LIKE \'{uri}%\''
        )
        rows = self._execute_query(query)
        cluster_cs_nodes: dict[int, CommonSenseNode] = dict()
        # The root node is the one that exactly matches the search uri.
        root_cs_node_id = None
        for row in rows:
            cs_node_id = row[0]
            cs_node = self.get_cs_node(cs_node_id)
            cluster_cs_nodes[cs_node_id] = cs_node
            if cs_node.uri == uri:
                root_cs_node_id = cs_node_id
            # end if
        # end for
        cs_node_cluster = CommonSenseNodeCluster(
            root_id=root_cs_node_id,
            cs_nodes=cluster_cs_nodes
        )
        return cs_node_cluster
    # end get_cs_node_cluster

    def get_cs_node_images(self, cs_node: CommonSenseNode):
        '''
        Get all of the image instances whose actions' concepts include the
        cs node passed in.
        '''
        # First, get all the ActionConcepts that include the cs node.
        action_concepts = self.get_cs_node_action_concepts(cs_node)
        # Then, get the image ids for each action concept.
        image_ids = list()
        for action_concept in action_concepts:
            image_ids.extend(action_concept.get_image_ids())
        # end for
        # Finally, get all the image instances for those image ids.
        image_instances = [self.get_image_instance(id)
                           for id in image_ids]
        return image_instances
    # end get_cs_node_image_instances

    def get_action_concept_images(self, action_concept: ActionConcept,
                                  only_object_paired: bool = False):
        '''
        Get all of the image instances whose action instances include the
        action concept passed in.

        If only_object_paired is true, only gets those image instances where
        the action has an action instance that is paired with an object as
        either its subject or its object.
        '''
        #image_instances = list()
        image_ids = list()
        if only_object_paired:
            image_ids = action_concept.get_object_paired_image_ids()
        else:
            image_ids = action_concept.get_image_ids()
        image_instances = [self.get_image_instance(id)
                           for id in image_ids]
        return image_instances
    # end get_action_concept_image_instances

    def get_cs_node_action_instances(self, cs_node: CommonSenseNode, 
                             image_instance: ImageInstance) -> list[ActionInstance]:
        '''
        Gets all the ActionInstances in an ImageInstance whose concept
        includes the cs node passed in.
        '''
        action_instances = list()
        action_concept_ids = set(self._cs_node_actions_map[cs_node.id])
        for action_instance in image_instance.action_instances.values():
            if action_instance.action_concept_id in action_concept_ids:
                action_instances.append(action_instance)
            # end if
        # end for

        return action_instances
    # end get_cs_node_action_instances

    #def get_multi_causal_link(self, multi_causal_link_id: int) -> MultiCausalLink:
    #    '''
    #    Gets a MultiCausalLink from the cache by its id.
    #
    #    Returns None if it's not in the cache.
    #    '''
    #    if multi_causal_link_id in self._multi_causal_links:
    #        return self._multi_causal_links[multi_causal_link_id]
    #    else:
    #        return None
    ## end _get_multi_causal_link

    def get_image_causal_links(self, image_1_id: int, image_2_id: int):
        '''
        Gets rows of causal links between actions in image 1 and actions
        in image 2, as well as the action instances and concepts that are
        linked, from the database.

        Then, makes ImageCausalLink objects from each row.

        Returns a list of ImageCausalLink objects.
        '''
        # This query gets every causal link between every action instance
        # in image 1 and image 2.
        # Test image 1 id: 1203
        # Test image 2 id: 2088
        query = ('''
            WITH image_1_cs_nodes AS (
                SELECT action_cs_nodes.action_concept_id AS action_concept_id_1, 
                action_instance_id AS action_instance_id_1, cs_node_id AS cs_node_id_1
                FROM (
                    SELECT DISTINCT action_concept_id, action_instance_id
                    FROM image_actions
                    WHERE image_id=?
                ) AS image_1_actions
                INNER JOIN action_cs_nodes
                ON image_1_actions.action_concept_id = action_cs_nodes.action_concept_id
            ),
            image_2_cs_nodes AS (
                SELECT action_cs_nodes.action_concept_id AS action_concept_id_2, 
                action_instance_id AS action_instance_id_2, cs_node_id As cs_node_id_2
                FROM (
                    SELECT DISTINCT action_concept_id, action_instance_id
                    FROM image_actions
                    WHERE image_id=?
                ) AS image_2_actions
                INNER JOIN action_cs_nodes
                ON image_2_actions.action_concept_id = action_cs_nodes.action_concept_id
            )

            SELECT * 
            FROM causal_links
            INNER JOIN image_1_cs_nodes
            ON causal_links.source_node_id = image_1_cs_nodes.cs_node_id_1
            INNER JOIN image_2_cs_nodes
            ON causal_links.target_node_id = image_2_cs_nodes.cs_node_id_2
            UNION
            SELECT * 
            FROM causal_links
            INNER JOIN image_1_cs_nodes
            ON causal_links.target_node_id = image_1_cs_nodes.cs_node_id_1
            INNER JOIN image_2_cs_nodes
            ON causal_links.source_node_id = image_2_cs_nodes.cs_node_id_2
        ''')
        rows = self._execute_query(query, [image_1_id, image_2_id])
        image_causal_links = [ImageCausalLink(row)
                              for row in rows]

        return image_causal_links
    # end get_image_causal_links

    def get_image_multi_causal_links(self, image_1_id: int, image_2_id: int):
        '''
        Gets rows of multi-causal links between actions in image 1 and actions
        in image 2, as well as the action instances and concepts that are
        linked, from the database.

        Then, makes ImageCausalLink objects from each row.

        Returns a list of ImageCausalLink objects.
        '''
        # This query gets every multi causal link between every action instance
        # in image 1 and image 2.
        # Test image 1 id: 1203
        # Test image 2 id: 2088
        # Takes about 500ms.
        query = ('''
            WITH image_1_cs_nodes AS (
                SELECT action_cs_nodes.action_concept_id AS action_concept_id_1, 
                action_instance_id AS action_instance_id_1, cs_node_id AS cs_node_id_1
                FROM (
                    SELECT DISTINCT action_concept_id, action_instance_id
                    FROM image_actions
                    WHERE image_id=?
                ) AS image_1_actions
                INNER JOIN action_cs_nodes
                ON image_1_actions.action_concept_id = action_cs_nodes.action_concept_id
            ),
            image_2_cs_nodes AS (
                SELECT action_cs_nodes.action_concept_id AS action_concept_id_2, 
                action_instance_id AS action_instance_id_2, cs_node_id As cs_node_id_2
                FROM (
                    SELECT DISTINCT action_concept_id, action_instance_id
                    FROM image_actions
                    WHERE image_id=?
                ) AS image_2_actions
                INNER JOIN action_cs_nodes
                ON image_2_actions.action_concept_id = action_cs_nodes.action_concept_id
            )

            SELECT * 
            FROM multi_causal_links
            INNER JOIN image_1_cs_nodes
            ON multi_causal_links.source_cs_node_id = image_1_cs_nodes.cs_node_id_1
            INNER JOIN image_2_cs_nodes
            ON multi_causal_links.target_cs_node_id = image_2_cs_nodes.cs_node_id_2
            UNION
            SELECT * 
            FROM multi_causal_links
            INNER JOIN image_1_cs_nodes
            ON multi_causal_links.target_cs_node_id = image_1_cs_nodes.cs_node_id_1
            INNER JOIN image_2_cs_nodes
            ON multi_causal_links.source_cs_node_id = image_2_cs_nodes.cs_node_id_2
        ''')
        rows = self._execute_query(query, [image_1_id, image_2_id])
        image_causal_links = [ImageMultiCausalLink(row)
                              for row in rows]

        return image_causal_links
    # end get_image_causal_links

    def get_action_object_pairs(self, search_word) -> list[ActionObjectPair]:
        '''
        Get ActionObjectPairs from the database by cs node uri search word.
        '''
        search_string = f'%/{search_word}/%'
        query = ('''
            WITH action_concepts AS (
                SELECT DISTINCT action_concept_id FROM action_cs_nodes
                WHERE cs_node_uri LIKE ?
            ),
            pairs AS (
                SELECT * FROM image_action_object_pairs
                INNER JOIN action_concepts
                ON image_action_object_pairs.action_concept_id = action_concepts.action_concept_id
            )

            SELECT image_id, action_instance_id, action_instance_name, object_instance_id,
            object_instance_name, object_role, action_concept_id, object_concept_id
            FROM pairs
        ''')
        rows = self._execute_query(query, [search_string])
        pairs = [ActionObjectPair(row) for row in rows]
        return pairs
    # end get_action_object_pairs

    def get_action_object_pairs_for_concept(self, action_concept_id: int):
        '''
        Get ActionObjectPairs from the database for an action concept
        identified by its id.
        '''
        query = ('''
            WITH pairs AS (
                SELECT * FROM image_action_object_pairs
                WHERE image_action_object_pairs.action_concept_id = ?
            )

            SELECT image_id, action_instance_id, action_instance_name, object_instance_id,
            object_instance_name, object_role, action_concept_id, object_concept_id
            FROM pairs
        ''')
        rows = self._execute_query(query, [action_concept_id])
        pairs = [ActionObjectPair(row) for row in rows]
        return pairs
    # end get_action_object_pairs_for_concept

    def get_image_objects_count(self, image_id: int):
        '''
        Returns the number of object instances in a given image.
        '''
        query = ('''
            SELECT COUNT(*)
            FROM image_objects
            WHERE image_id = ?
        ''')
        rows = self._execute_query(query, [image_id])
        return rows[0][0]
    # Database table generation

    def generate_database_tables(self):
        '''
        Generates all database tables using the data handler's
        DatabaseTableGenerator.
        '''
        self._database_table_generator.generate_database_tables()
    # end generate_database_tables

    def write_cs_edge(self, start_node_id: int, end_node_id: int, relation: str):
        '''
        Have the CSKGQuerier write an edge into the commonsense_knowledge
        database.
        '''
        self._commonsense_querier.write_edge(start_node_id, end_node_id, relation)
    # end write_cs_edge

    # Utility

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

    def __repr__(self):
        '''
        
        '''
        repr_string = f'CacheHandler. Number of actions: {len(self.actions)}'
    # end __repr__

# end class DataHandler