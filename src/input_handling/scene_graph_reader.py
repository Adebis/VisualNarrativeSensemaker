import json
import os

from nltk.corpus import wordnet as wn

import constants as const
from constants import ConceptType

from commonsense import querier
from commonsense.commonsense_data import Synset
from commonsense.querier import CommonSenseQuerier
from knowledge_graph.graph import KnowledgeGraph 
from knowledge_graph.items import (Node, Concept, Object, Action, Edge, 
                                   EdgeRelationship)

from input_handling.scene_graph_data import (Image, BoundingBox,
                                             SceneGraphObject, 
                                             SceneGraphRelationship)

class SceneGraphReader:
    """
    Handles reading scene graphs and producing a knowledge graph.

    Attributes
    ----------
    _commonsense_querier : CommonSenseQuerier
        A CommonSenseQuerier for interacting with commonsense data. 
        Initialization of a CommonSenseQuerier takes some time, so an existing 
        CommonSenseQuerier should be given to this object on initialization.
    """
    def __init__(self, commonsense_querier: CommonSenseQuerier):
        print("Initializing scene graph reader")
        self._commonsense_querier = commonsense_querier
    # end __init__

    def read_scene_graphs(self, image_ids: int):
        """
        Reads the scene graphs for an image set.

        Parameters
        ----------
        image_ids : int
            An ordered list of image ids to read the scene graphs of. Each id
            corresponds to the name of an image and of its scene graph 
            annotations file in Visual Genome. 

        Returns
        -------
        KnowledgeGraph
            The knowledge graph generated from all of the set's scene graphs.
        """

        knowledge_graph = KnowledgeGraph(self._commonsense_querier)
        # Read each image's scene graph.
        index_counter = 0
        for image_id in image_ids:
            # Make an object representing the image.
            image_file_path = (f'{const.IMAGES_DIRECTORY}/{image_id}.jpg')
            # If the jpeg doesn't exist, try a png
            if not os.path.isfile(image_file_path):
                image_file_path = (f'{const.IMAGES_DIRECTORY}/{image_id}.png')
            # If that still doesn't work, give up.
            if not os.path.isfile(image_file_path):
                print(f'SceneGraphReader.read_scene_graphs : Could not find ' +
                      f'image file for image {image_id}.')
            # end if

            image = Image(id=image_id, index=index_counter, 
                          file_path=image_file_path)
            index_counter += 1
            # Read the scene graph for the image. This will populate the
            # knowledge graph with Nodes and Edges from the Image's scene graph.
            self._read_scene_graph(image, knowledge_graph)
        # end for

        return knowledge_graph
    # end read_scene_graphs

    def _read_scene_graph(self, image: Image, knowledge_graph: KnowledgeGraph):
        """
        Read the scene graph for the Image passed in. 
        
        Populates the knowledge graph passed in with Nodes and Edges made from 
        the scene graph. Does so in-place, so doesn't return anything.
        """

        annotations_file_path = (f'{const.ANNOTATIONS_DIRECTORY}/{image.id}.json')
        scene_graph_json = json.load(open(annotations_file_path, 'r'))

        # Populate Object nodes in the knowlede graph from the scene graph.
        id_map = self._populate_objects(knowledge_graph, image, 
                                        scene_graph_json)

        # Populate Action nodes in the knowledge graph from the scene graph.
        self._populate_actions(knowledge_graph, image, scene_graph_json, id_map)

        # Populate Edges between Instance nodes.
        self._populate_edges(knowledge_graph, image)

        # Determine and set focal instances.
        self._set_focal_instances(knowledge_graph, image)

        return knowledge_graph
    # end read_scene_graph

    def _populate_objects(self, knowledge_graph: KnowledgeGraph, image: Image,
                          scene_graph_json: dict):
        """
        Generates Object nodes by reading the object entries in a scene graph, 
        then adds them to the knowledge graph in-place. 

        Parameters
        ----------
        knowledge_graph : KnowledgeGraph
            The knowledge graph to populate with Objects. Adds them in-place.
        image : Image
            The image whose scene graph is being parsed.
        scene_graph_json : dict
            The JSON dictionary for the scene graph for this image.
        
        Returns
        -------
        id_map : dict[int, int]
            A dictionary mapping scene graph object_ids to Node ids.
        """
        # Look through the 'objects' of the scene graph json dictionary.
        for object_entry in scene_graph_json['objects']:
            # Make a scene graph object object for each object entry.
            # Make a BoundingBox object for the h, w, x, y data.
            bounding_box = BoundingBox(object_entry['h'],
                                       object_entry['w'],
                                       object_entry['x'],
                                       object_entry['y'])
            # For each synset in the synset list, make a Synset object.
            synsets = [Synset(synset_name) for synset_name in 
                       object_entry['synsets']]
            # If there are no synsets in this scene graph object's annotations,
            # try to find one.
            # Looks specifically for noun senses of the word.
            if len(synsets) == 0:
                wn_synsets = list()
                for name in object_entry['names']:
                    wn_synset = querier.find_synset(name, 
                                                    pos=wn.NOUN)
                    if not wn_synset is None:
                        wn_synsets.append(wn_synset)
                # end for
                synsets = [Synset(wn_synset.name()) for wn_synset in wn_synsets]
            # end if
            # Filter out any synsets that are of filtered object words.
            synsets = [synset for synset in synsets 
                       if not synset.word in const.FILTERED_OBJECTS]
            # If there are no synsets at this point, skip this object.
            if len(synsets) == 0:
                #print(f'scene_graph_reader.populate_objects() : no synsets ' +
                #      f'found for \'{object_entry["names"][0]}\'.')
                continue
            # end if
            # Remove any duplicate synsets.
            synsets_dedupe = list()
            for synset in synsets:
                if not synset in synsets_dedupe:
                    synsets_dedupe.append(synset)
            # end for
            synsets = synsets_dedupe

            # Get or make the Concepts for this node.
            concepts = list()
            for synset in synsets:
                concept = knowledge_graph.get_or_make_concept(synset,
                                                            ConceptType.OBJECT)
                concepts.append(concept)
            # end for

            # Object annotations may not have any attributes, so we have
            # to check. 
            sg_object = (
                SceneGraphObject(names=object_entry['names'], 
                                 synsets=synsets,
                                 object_id=object_entry['object_id'],
                                 bounding_box=bounding_box,
                                 image=image,
                                 attributes=object_entry['attributes'])
                if 'attributes' in object_entry else
                SceneGraphObject(names=object_entry['names'], 
                                 synsets=synsets,
                                 object_id=object_entry['object_id'],
                                 bounding_box=bounding_box,
                                 image=image))
            
            # Make an Object node for this object.
            # The word for Object's first synset is its label.
            object_node = Object(label=sg_object.synsets[0].word,
                                 image=image,
                                 scene_graph_objects=[sg_object],
                                 concepts=concepts)
            # Add it to the knowledge graph.
            knowledge_graph.add_node(object_node)
        # end for

        # Handle any overlaps.
        self._merge_overlapping_objects(knowledge_graph=knowledge_graph, 
                                        scene_graph_json=scene_graph_json,
                                        image=image)
        
        # Build the map of scene graph object_ids to Object node ids.
        id_map = dict()
        for object_node in knowledge_graph.objects.values():
            for sg_object in object_node.scene_graph_objects:
                # No scene graph object should be mapped to more than one Object
                # node, so error check for that here.
                if sg_object.object_id in id_map:
                    print("Error! Scene graph object already mapped to node!")
                id_map[sg_object.object_id] = object_node.id
        # end for

        return id_map
    # end _populate_objects

    def _merge_overlapping_objects(self, knowledge_graph: KnowledgeGraph,
                                   scene_graph_json: dict, image: Image):
        """
        Merges the Object nodes for all overlapping Objects in the 
        KnowledgeGraph in-place. 

        Objects are overlapping if they represent the same visual object
        in a scene graph. 
        
        Overlapping Objects are merged such that any unique information from 
        their different annotations are preserved.

        Only merges Objects that appear in the scene graph for the Image passed
        in.
        """
        # Merge object nodes whose bounding boxes overlap. 
        # Uses NMS (non-maximum suppression) bounding box selection algorithm.
        # 1. Sort Objects by confidence scores. Since we don't have those, 
        # instead score every Object by: 
        #   a. Number of times the node's object_id appears in a relationship.
        #   b. Number of attributes.
        # Store Object scores here, keyed by their node ID. 
        object_scores = dict()
        for object_node in knowledge_graph.objects.values():
            # Skip any Object that doesn't appear in the scene graph of the
            # Image passed in.
            if not object_node.get_image() == image:
                continue
            score = 0
            # Count how many times its object_ids appears in a relationship in
            # the scene graph.
            for sg_object in object_node.scene_graph_objects:
                object_id = sg_object.object_id
                for rel_entry in scene_graph_json['relationships']:
                    if (rel_entry['object_id'] == object_id or 
                        rel_entry['subject_id'] == object_id):
                        score += 1
                # end for
            # end for
            # Count how many attributes it has
            score += len(object_node.get_attributes())
            # Store the score for this Object node.
            object_scores[object_node.id] = score
        # end for
        # Now that we have all the scores, sort the Object node ids by score.
        object_scores_sorted = sorted(object_scores.items(),
                                      key=lambda item_pair: item_pair[1],
                                      reverse=True)
        object_ids_sorted = [item_pair[0] for item_pair in object_scores_sorted]
        # Loop until there are no more Object nodes to check for overlaps.
        while len(object_ids_sorted) > 0:
            overlapping_node_ids = list()
            # Pop the best scoring node.
            best_node = knowledge_graph.objects[object_ids_sorted.pop(0)]
            # Go through every other node and gather any that overlap.
            # Since the first node in the sorted list is the one with the 
            # highest score, every other node left in the list must have a lower 
            # score.
            for other_node_id in object_ids_sorted:
                other_node = knowledge_graph.objects[other_node_id]
                if determine_overlap(best_node, other_node):
                    overlapping_node_ids.append(other_node_id)
            # end for
            # Merge every overlapping node into the best scoring node and then
            # remove it from both the knowledge graph and from the list of
            # sorted object ids.
            # That way we won't consider them for merging again.
            for overlapping_node_id in overlapping_node_ids:
                overlapping_node = knowledge_graph.nodes[overlapping_node_id]
                best_node.merge_in(overlapping_node)
                knowledge_graph.remove_node(overlapping_node)
                object_ids_sorted.remove(overlapping_node_id)
            # end for
        # end while
    # end _merge_overlapping_objects

    def _populate_actions(self, knowledge_graph: KnowledgeGraph, image: Image,
                         scene_graph_json: dict, id_map: dict[int, int]):
        """
        Generates Action nodes by reading the relationship entries in a scene 
        graph, then adds them to the knowledge graph in-place. 

        Then, calls _actions_from_attributes to generate Action nodes from
        Object attributes that are actions (e.g. cooking).

        Parameters
        ----------
        knowledge_graph : KnowledgeGraph
            The knowledge graph to populate with Actions and their Concepts. 
            Adds them in-place.
        image : Image
            The image whose scene graph is being parsed.
        scene_graph_json : dict
            The JSON dictionary for the scene graph for this image.
        id_map : dict[int, int]
            A dictionary mapping scene graph object_ids to Node ids.
            
        Returns
        -------
        None
        """
        self._make_actions_from_relationships(knowledge_graph=knowledge_graph,
                                              image=image,
                                              scene_graph_json=scene_graph_json,
                                              id_map=id_map)
        self._make_actions_from_attributes(knowledge_graph=knowledge_graph,
                                           image=image)
    # end populate_actions
    def _make_actions_from_relationships(self, knowledge_graph: KnowledgeGraph, 
                                         image: Image, scene_graph_json: dict, 
                                         id_map: dict[int, int]):
        """
        Makes Actions out of scene graph relationship 
        entries and adds them to the knowledge graph.

        Parameters
        ----------
        knowledge_graph : KnowledgeGraph
            The knowledge graph to populate with Actions. Adds them in-place.
        image : Image
            The image whose scene graph is being parsed.
        scene_graph_json : dict
            The JSON dictionary for the scene graph for this image.
        id_map : dict[int, int]
            A dictionary mapping scene graph object_ids to Node ids.

        Returns
        -------
        None
        """
        # Go through the 'relationships' of the scene graph dictionary and make
        # Actions out of them. 
        for rel_entry in scene_graph_json['relationships']:
            # For each synset in the synset list, make a Synset object.
            # Action synsets aren't reliable, so we always have to look for
            # synsets based on the predicate.
            #synsets = [Synset(synset_name) for synset_name 
            #           in rel_entry['synsets']]
            synsets = list()
            wn_synset = querier.find_synset(rel_entry['predicate'], 
                                            wn.VERB)
            if not wn_synset is None:
                synsets = [Synset(wn_synset.name())]
            # Filter out any synsets that are of filtered action words.
            synsets = [synset for synset in synsets 
                       if not synset.word in const.FILTERED_ACTIONS]
            # If there are no synsets, skip this action.
            if len(synsets) == 0:
                continue
            # end if
            # Remove any duplicate synsets.
            synsets_dedupe = list()
            for synset in synsets:
                if not synset in synsets_dedupe:
                    synsets_dedupe.append(synset)
            # end for
            synsets = synsets_dedupe
            # Make a scene graph relationship object for each relationship 
            # entry.
            sg_rel = SceneGraphRelationship(predicate=rel_entry['predicate'],
                                            synsets=synsets,
                                            relationship_id=
                                                rel_entry['relationship_id'],
                                            object_id=rel_entry['object_id'],
                                            subject_id=rel_entry['subject_id'],
                                            image=image)

            # Get or make the Concepts for this node.
            concepts = list()
            for synset in synsets:
                concept = knowledge_graph.get_or_make_concept(synset,
                                                              ConceptType.ACTION)
                concepts.append(concept)
            # end for

            # Get the object nodes for this relationship's object and subject.
            object_node = knowledge_graph.nodes[id_map[sg_rel.object_id]]
            subject_node = knowledge_graph.nodes[id_map[sg_rel.subject_id]]

            # Make the action node.
            # Let the word for its first synset be the Action's label.
            action_node = Action(label=sg_rel.synsets[0].word,
                                 image=sg_rel.image,
                                 subject=subject_node,
                                 object=object_node,
                                 scene_graph_rel=sg_rel,
                                 concepts=concepts)
            # Add the action node to the knowledge graph.
            knowledge_graph.add_node(action_node)
        # end for
    # end _make_actions_from_relationships
    def _make_actions_from_attributes(self, knowledge_graph: KnowledgeGraph,
                                      image: Image):
        """
        Makes Actions out of Object attributes, adds them 
        to the knowledge graph, and removes those attributes from their Objects.

        Only does so for Objects that appear in the scene graph of the Image
        passed in.
        """
        # Go through object attributes and make Actions out of any that
        # are actually actions.
        for object_node in knowledge_graph.objects.values():
            # Skip any Object not from the scene graph of the Image passed in.
            if not object_node.get_image() == image:
                continue
            # Look through the object's attributes
            # If any are turned into actions, remove them from the object later.
            attributes_to_remove = list()
            for attribute in object_node.get_attributes():
                if not attribute.endswith('ing'):
                    continue
                # If the attribute ends with '-ing', make an action out of it
                # with this object node as the subject.
                # Find a synset using the attribute.
                # Look specifically for a verb.
                wn_synset = querier.find_synset(attribute, 'v')
                synset = Synset(wn_synset.name())
                # Filter out any synsets that are of filtered action words.
                if synset.word in const.FILTERED_ACTIONS:
                    continue
                # Get or make the node's Concept.
                concept = knowledge_graph.get_or_make_concept(synset,
                                                            ConceptType.ACTION)
                # Make the action node.
                action_node = Action(label=attribute,
                                     image=object_node.get_image(),
                                     subject=object_node,
                                     concepts=[concept])
                knowledge_graph.add_node(action_node)
                attributes_to_remove.append(attribute)
            # end for
            # Remove the attributes that were turned into actions from the 
            # object.
            for attribute in attributes_to_remove:
                object_node.remove_attribute(attribute)
            # end for
        # end for
    # end _make_actions_from_attributes

    def _populate_edges(self, knowledge_graph: KnowledgeGraph, image: Image):
        """
        Populate the knowledge graph with Edges for its Instance nodes.

        Does so in-place. Only populates actions that appear in the image
        passed in.
        """
        # Make edges between the nodes. 
        # Go through each Action and make an object-of and subject-of edge
        # from each Object node to each Action node its a part of.
        for action in knowledge_graph.actions.values():
            if not action.get_image() == image:
                continue
            # Make the edge from the subject.
            knowledge_graph.make_and_add_edge(source=action.subject,
                                              target=action,
                                              relationship=str(EdgeRelationship.SUBJECT_OF))
            # This action may not have an object, so we have to check.
            if not action.object is None:
                # Make the edge from the object.
                knowledge_graph.make_and_add_edge(source=action.object,
                                                  target=action,
                                                  relationship=str(EdgeRelationship.OBJECT_OF))
                # If there is an object, additionally make a co-actor edge
                # between the subject and the object.
                knowledge_graph.make_and_add_edge(source=action.subject,
                                                  target=action.object,
                                                  relationship=str(EdgeRelationship.CO_ACTOR))
            # end if
        # end for
    # end populate_edges

    def _set_focal_instances(self, knowledge_graph: KnowledgeGraph, 
                             image: Image):
        """
        Determine and set the focal instances for the knowledge graph passed in.

        Does so in-place. Only does so for the Instances in the image passed in.
        """
        # See what character has the most edges in the knowledge graph.
        edge_counts = dict()
        scene_objects = [node for node in knowledge_graph.objects.values()
                         if node.get_image() == image]
        for object_node in scene_objects:
            # First, make sure this Object can be a character
            if not self._is_character(object_node):
                continue
            # If so, count its edges.
            edge_counts[object_node.id] = len(object_node.edges)
        # end for

        # Pick the character with the most edges and set it as the focal node.
        focal_node_scores = dict()
        highest_edge_count = 0
        highest_edge_node_id = -1
        for node_id, edge_count in edge_counts.items():
            if edge_count > highest_edge_count:
                highest_edge_count = edge_count
                highest_edge_node_id = node_id
            # end if
        # end for
        focal_node_scores[highest_edge_node_id] = const.DEFAULT_FOCAL_SCORE

        # Set the chosen focal nodes.
        for node_id, focal_score in focal_node_scores.items():
            knowledge_graph.set_focal_node(node_id, focal_score)
        # end for
    # end _set_focal_instances

    def _is_character(self, object_node: Object):
        """
        Returns whether or not the Object passed in is capable of being a
        character or not.
        """
        # If one of the Object's inherited hypernyms is organism/being, then
        # we consider it a character.
        char_synset = wn.synset('organism.n.01')
        # Get its synsets.
        for synset in object_node.get_synsets():
            wn_synset = wn.synset(synset.name)
            # Check if there's a hypernym path from this synset to its root
            # that includes the character synset.
            # If so, this Object is a character.
            for h_path in wn_synset.hypernym_paths():
                if char_synset in h_path:
                    return True
            # end for
        # end for
        return False
    # end _is_character

# end class SceneGraphReader

def determine_overlap(object_1: Object, object_2: Object):
    """
    Determines whether two Object nodes represent visually overlapping objects.

    Two Objects are overlapping if they represent the same Concept and
    their bounding boxes have an IOU (Intersection Over Union) greater
    than the IOU threshold set in constants.

    IOU thresholds of >= 0.5 are usually used. 
    """

    # See if at least one of the synsets matches between the two Objects.
    # If not, do not consider them overlapping.
    has_shared_synset = False
    for synset in object_1.get_synsets():
        if synset in object_2.get_synsets():
            has_shared_synset = True
            break
    # end for
    if not has_shared_synset:
        return False
    # Calculate the IOU of their bounding boxes.
    # Intersection area.
    # The x, y coordinates in a bounding box is their upper-left corner.
    # We can get the coordinates of the bottom-right corner from h, w.
    # So we have x1, y1 in the top-left and x2, y2 in the bottom-right.
    # The top-left corner of the intersection area is:
    #   The right-most (largest) x1
    #   The bottom-most (smallest) y1
    # The bottom-right corner of the intersection area is:
    #   The left-most (smallest) x2
    #   The top-most (largest) y2
    bbox_1 = object_1.scene_graph_objects[0].bounding_box
    obj_1_x1 = bbox_1.x
    obj_1_y1 = bbox_1.y
    obj_1_x2 = bbox_1.x + bbox_1.w
    obj_1_y2 = bbox_1.y + bbox_1.h

    bbox_2 = object_2.scene_graph_objects[0].bounding_box
    obj_2_x1 = bbox_2.x
    obj_2_y1 = bbox_2.y
    obj_2_x2 = bbox_2.x + bbox_2.w
    obj_2_y2 = bbox_2.y + bbox_2.h

    int_x1 = max(obj_1_x1, obj_2_x1)
    int_y1 = min(obj_1_y1, obj_2_y1)
    int_x2 = min(obj_1_x2, obj_2_x2)
    int_y2 = max(obj_1_y2, obj_2_y2)

    int_area = (int_x2 - int_x1) * (int_y2 - int_y1)

    # Union area
    # The area of the union of the two bounding boxes is the sum of their
    # areas minus the area of their intersection.
    union_area = bbox_1.w * bbox_1.h + bbox_2.w * bbox_2.h - int_area

    # Intersection Over Union
    iou = int_area / union_area

    # If the IOU is over the threshold, these two Objects are considered 
    # overlapping.
    if iou > const.IOU_THRESHOLD:
        return True
    else:
        return False
# end determine_overlap