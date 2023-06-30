from functools import singledispatchmethod
from typing import Union
from timeit import default_timer as timer
from enum import Enum

import cv2
import sys

import constants as const
from input_handling.scene_graph_data import (Image, BoundingBox, SceneGraphObject, 
                                             SceneGraphRelationship)
from commonsense.commonsense_data import (CommonSenseNode, CommonSenseEdge,
                                          Synset)

from constants import ConceptType

class EdgeRelationship(Enum):
    """
    An enum for Edge relationships.
    """
    SUBJECT_OF = 'subject-of'
    OBJECT_OF = 'object-of'
    CO_ACTOR = 'co-actor'
    DUPLICATE_OF = 'duplicate-of'
# end enum EdgeRelationship

class Node:
    """ 
    Base class for a node in the knowledge graph.

    ...

    Parameters
    ----------
    label : str
        The node's word or phrase label.
    name : str
        The node's string identifier. 

    Attributes
    ----------
    id : int
        Unique integer identifier for this node. 
    label : str
        Single word or phrase describing the thing this Node represents. 
        
        Examples: 'bike', 'running', 'dogs'.
    name : str
        Human-readable string identifier for this node. Should be unique per
        Node, but is not guaranteed to be. For a unique identifier, use the
        Node's id.
        
        Examples: 'bike-0-10', 'running-9-10', 'dogs-o'.
    edges : dict[int, Edge]
        All of the Edges incident on this node. Includes both incoming and
        outgoing Edges. Keyed by Edge id.
    hypothesized : bool
        Whether or not this Node came from a Hypothesis. Default value is False.

    Methods
    -------
    add_edge(edge: Edge)
        Adds an Edge to this Node. 
    """

    # Class variable to make unique IDs when a new node is made.
    _next_id = 0
    def __init__(self, label: str, name: str, hypothesized: bool=False):
        self.id = Node._next_id
        # Make sure to increment the next id class variable each time a new
        # id is assigned.
        Node._next_id += 1
        self.label = label
        self.name = name
        self.edges = dict()
        self.hypothesized = hypothesized
    # end __init__

    def __eq__(self, __obj):
        """
        Nodes are considered equal if they have the same id.
        """
        # If the other object is not the same type as this Node, it can't be
        # equal to it.
        if not type(__obj) == type(self):
            return False
        elif self.id == __obj.id:
            return True
        else:
            return False
    # end __eq__

    def __repr__(self):
        """
        Nodes are represented by their name.
        """
        return (f'{self.name}')
    # end __str__

    def add_edge(self, edge):
        """
        Adds an Edge to this Node's dictionary of Edges.

        Prevents duplicate Edges by checking the Edge's id.
        """
        if edge.id in self.edges:
            return
        self.edges[edge.id] = edge
    # end add_edge

    def get_edges_with(self, node):
        """
        Gets a list of all of this Node's Edges with another Node.
        """
        return [edge for edge in self.edges.values() if edge.has_node(node)]
    # end get_edges_with
# end class Node

class Concept(Node):
    """
    The node for a concept in the knowledge graph.

    Represents a concept, distinct from an instance of a concept. For example,
    the Concept 'dog' represents the fluffy creature with a tail that barks.
    A dog observed in an image, 'dog_1_0', is an instance of the Concept 'dog'.
    
    Concepts have a type that mirrors the type of its instances. For
    example, the Concept 'dog' is an OBJECT type, and all of its instances
    would be represented by Object nodes. The Concept 'run' is an
    ACTION type, and its instances would be represented by Action nodes. Concept 
    types are defined in constants.

    ...

    Attributes
    ----------
    concept_type : ConceptType
        What type of concept this is. Concept types are defined in constants.
    synset : Synset
        The synset this concept represents, if any. Default value is None.
    commonsense_nodes : dict[int, CommonSenseNode]
        A dictionary of the CommonSenseNode objects that matched this concept. 
        Keyed by CommonSenseNode id. Default value is the empty dict.
    commonsense_edges : dict[int, CommonSenseEdge]
        A dictionary of the CommonSenseEdge objects incident on the 
        CommonSenseNode objects this Concept represents. Keyed by 
        CommonsenseEdge id. Default is the empty dict.
    """
    concept_type: ConceptType
    synset: Synset
    commonsense_nodes: dict[int, CommonSenseNode]
    commonsense_edges: dict[int, CommonSenseEdge]

    def __init__(self, label: str, concept_type: ConceptType, 
                 synset: Synset = None):
        # Concept names are {concept}_{type_letter}_{id}, where type_letter is 
        # the first letter of the Concept's ConceptType.
        #   Examples: bicycle_o, run_a
        type_letter = 'c'
        if concept_type == ConceptType.OBJECT:
            type_letter = 'o'
        elif concept_type == ConceptType.ACTION:
            type_letter = 'a'
        name = (f'{label}_{type_letter}_{Node._next_id}')
        super().__init__(label=label, 
                         name=name, 
                         hypothesized=False)
        self.concept_type = concept_type
        self.synset = synset
        self.commonsense_nodes = dict()
        self.commonsense_edges = dict()
    # end __init__

    def add_commonsense_node(self, commonsense_node: CommonSenseNode):
        """
        Adds a commonsense node to this Concept. Avoids duplicates.
        """
        if not commonsense_node.id in self.commonsense_nodes:
            self.commonsense_nodes[commonsense_node.id] = commonsense_node
    # end add_commonsense_node

    def add_commonsense_edge(self, commonsense_edge: CommonSenseEdge):
        """
        Adds a commonsense edge to this Concept. Avoids duplicates.
        """
        if not commonsense_edge.id in self.commonsense_edges:
            self.commonsense_edges[commonsense_edge.id] = commonsense_edge
    # end add_commonsense_edge

    def get_commonsense_node(self, commonsense_node_id: int):
        """
        Gets a CommonSenseNode from this Concept by id.

        Returns
        -------
        CommonSenseNode | None
            The CommonSenseNode with the given id. None if this Concept does
            not have a CommonSenseNode with the given id.
        """
        if commonsense_node_id in self.commonsense_nodes:
            return self.commonsense_nodes[commonsense_node_id]
        else:
            return None
    # end get_commonsense_node

    def get_commonsense_nodes(self):
        """
        Gets all the CommonSenseNodes this Concept represents.
        """
        return self.commonsense_nodes.values()
    # end get_commonsense_node_ids

    def get_concept_edges(self):
        """
        Gets all Edges between this Concept and another Concept.
        """
        return [edge for edge in self.edges.values() 
                if (type(edge.source)==Concept and type(edge.target)==Concept)]
    # end get_concept_edges

# end class Concept

class Instance(Node):
    """
    Base class for a node for an instance of a Concept in the knowledge graph.

    Concepts are abstract definitions of things. Instances of Concepts are
    specific examples of those Concepts in the real world.

    Attributes
    ----------
    concepts : list[Concept]
        All of the Concepts that this is an Instance of. Default value
        is the empty list. 

        Something may be an Instance of multiple Concepts, especially in the 
        case where multiple labels describe the same thing or are subcategories 
        of other labels.

        The first item in this list should be considered the main Concept.
    images : dict[int, Image]
        The Images this Instance is grounded in, keyed by Image id. Default 
        value is the empty dict.
    focal_score : float
        A score indicating how much focus this Instance should be given. 
        The focal score is independent of the Instance's neighbors, and radiates
        centrality outwards from itself. 
    """

    concepts: list[Concept]
    images: dict[int, Image]
    focal_score: float
    # The focal nodes that affect this node.
    _focal_nodes: dict[int, Node]
    # The Instance's distances to each focal node.
    # From these distances and the centrality decay factor, the node's 
    # centrality can be calculated.
    _focal_node_distances: dict[int, int]

    def __init__(self, name: str, label: str, concepts: list[Concept], 
                 image: Image, hypothesized: bool=False):
        super().__init__(name=name, 
                         label=label,
                         hypothesized=hypothesized)
        self.concepts = concepts
        self.images = dict()
        self.images[image.id] = image
        self.focal_score = 0
        self._focal_nodes = dict()
        self._focal_node_distances = dict()
    # end __init__

    def __repr__(self):
        # Add [f] if this is a focal node.
        return (f'{super().__repr__()}_f' if not self.focal_score == 0
                else super().__repr__())
    # end __repr__

    def has_concept(self, concept: Concept):
        """
        Whether or not this Instance has the Concept passed in as one of its
        Concepts.
        """
        for existing_concept in self.concepts:
            if existing_concept == concept:
                return True
        # end for
        return False
    # end has_concept

    def get_image(self) -> Union[Image, None]:
        """
        Gets one of the Images this Instance is grounded in.

        Picks one randomly from this Instance's dictionary of Images.

        If there are no images in the dictionary, returns None.
        """
        if len(self.images) == 0:
            return None
        else:
            return list(self.images.values())[0]
    # end get_image

    def get_commonsense_nodes(self) -> list[CommonSenseNode]:
        """
        Gets the CommonSenseNodes the Concepts of this Instance represent.
        """
        cs_nodes = list()
        for concept in self.concepts:
            cs_nodes.extend(concept.get_commonsense_nodes())
        return cs_nodes
    # end get_commonsense_node_ids

    def get_commonsense_edges(self) -> list[CommonSenseEdge]:
        """
        Gets the CommonSenseEdges incident on the CommonSenseNodes of the
        Concepts of this Instnace.
        """
        cs_edges = list()
        for concept in self.concepts:
            for cs_edge in concept.commonsense_edges.values():
                cs_edges.append(cs_edge)
        # end for
        return cs_edges
    # end get_commonsense_edges

    def get_neighboring_instances(self):
        """
        Gets a list of all the Instance nodes with an edge to this Instance.
        """
        neighboring_instances = list()
        for edge in self.edges.values():
            other_node = edge.get_other_node(self)
            if issubclass(type(other_node), Instance):
                neighboring_instances.append(other_node)
        # end for
        return neighboring_instances
    # end get_neighboring_instances

    def add_focal_node(self, focal_node: Node, distance: int):
        """
        Adds a focal node to this node and sets its distance.
        """
        self._focal_nodes[focal_node.id] = focal_node
        self._focal_node_distances[focal_node.id] = distance
    # end add_focal_node

    def get_centrality(self):
        """
        Returns the node's centrality, calculated from the focal scores of each
        of its focal nodes.
        """
        # Start with this node's own focal score.
        centrality = self.focal_score
        for focal_node in self._focal_nodes.values():
            focal_score = focal_node.focal_score
            distance = self._focal_node_distances[focal_node.id]
            centrality += focal_score * pow(const.CENTRALITY_DECAY, distance)
        # end for
        return centrality
    # end get_centrality
# end class Instance

class Object(Instance):
    """
    The node for an Instance of an object in the knowledge graph.

    Here, object refers to a specific material thing in the world, such as a dog
    passing by your window.

    An Object represents an instance of a Concept. The dog passing by your window
    is an instance of the Concept 'dog'. The Object for the dog passing
    by your window represents that specific instance of a dog alone, not any 
    other dogs.
    
    Objects can be instances of more than one Concept. The dog walking by your
    window can be an instance of the Concepts 'dog', 'mammal', and 'pet'.

    ...

    Attributes
    ----------
    scene_graph_objects : list[SceneGraphObject]
        All of the data from the scene graph for this node's objects.

        Most Objects only represent a single scene graph object, but some may
        represent multiple, especially if multiple scene graph objects were
        merged together due to overlapping bounding boxes.

        The first item in this list should be considered the main scene graph
        object.

        Default value is the empty list.
    attributes : list[str]
        A list of the Objects attributes, as they would appear in a scene graph 
        annotation.
    appearance : Mat
        A cv2 matrix representing the Object's visual appearance. 
    """
    def __init__(self, label: str, image: Image, attributes: list[str] = list(), 
                 appearance: cv2.Mat = None,
                 scene_graph_objects: list[SceneGraphObject] = list(),
                 concepts: list[Concept] = list(),
                 hypothesized: bool=False):
        """
        Initializes an Object node with a label, a list of the SceneGraphObjects 
        it's based off of, and a list of the Concepts it's an instance of.

        If no appearance is given, gets its appearance from the scene graph 
        object with the smallest bounding box.

        Adds all of the scene graph objects' attributes to the attributes given.
        """
        # Object node names are {word}_{image_index}_{id}
        #   e.g. for bicycle_0_24, the object was named 'bicycle' in the scene
        #   graph, its Node's id is 24, and it appeared in the 1st image in
        #   the image sequence.
        name = (f'{label}_{image.index}_{Node._next_id}')
        # Put an 'h' in the name if this is a hypothesized Object.
        if hypothesized:
            name = (f'{label}_h_{image.index}_{Node._next_id}')
        super().__init__(label=label, 
                         name=name, 
                         concepts=concepts,
                         image=image,
                         hypothesized=hypothesized)
        self.scene_graph_objects = scene_graph_objects
        # Adds its scene graph objects' attributes to the ones passed in.
        self.attributes = list()
        self.attributes.extend(attributes)
        for scene_graph_object in self.scene_graph_objects:
            for attribute in scene_graph_object.attributes:
                if not attribute in self.attributes:
                    self.attributes.append(attribute)
        # end for
        # Set its appearance from the scene graph objects if an appearance
        # wasn't given.
        if appearance is None and len(scene_graph_objects) > 0:
            smallest_sg_object = None
            smallest_bbox_size = sys.maxsize
            for scene_graph_object in self.scene_graph_objects:
                bbox = scene_graph_object.bounding_box
                if (bbox.w * bbox.h < smallest_bbox_size):
                    smallest_sg_object = scene_graph_object
                    smallest_bbox_size = bbox.w * bbox.h
                # end if
            # end for
            self.appearance = smallest_sg_object.get_matrix()
        else:
            self.appearance = appearance
    # end __init__

    def __repr__(self):
        return super().__repr__()
    # end __repr__

    def get_attributes(self):
        """
        Gets the attributes for this Object.
        """
        return self.attributes
    # end get_attributes

    def remove_attribute(self, attribute: str):
        """
        Removes an attribute from this Object.

        Removes it from all of this Object's SceneGraphObjects.
        """
        for sg_object in self.scene_graph_objects:
            if attribute in sg_object.attributes:
                sg_object.attributes.remove(attribute)
    # end remove_attribute

    def get_synsets(self):
        """
        Gets all of the Object's synsets.
        
        Returns all Synsets from this Object's SceneGraphObjects 
        without duplicates. 
        """
        synsets = list()
        for sg_object in self.scene_graph_objects:
            for synset in sg_object.synsets:
                if not synset in synsets:
                    synsets.append(synset)
            # end for
        # end for
        return synsets
    # end get_synsets

    def merge_in(self, object_node):
        """
        Merges another Object into this Object.
        
        This Object adds all of the other Object's SceneGraphObjects,
        attributes, and Concepts onto its own, avoiding duplicates.

        The other Object's appearance will be lost.
        """
        # Don't merge non-Objects.
        if not type(object_node) == Object:
            return
        # Avoid duplicates
        for sg_object in object_node.scene_graph_objects:
            if not sg_object in self.scene_graph_objects:
                self.scene_graph_objects.append(sg_object)
        # end for
        for attribute in object_node.attributes:
            if not attribute in self.attributes:
                self.attributes.append(attribute)
        # end for
        for concept in object_node.concepts:
            if not concept in self.concepts:
                self.concepts.append(concept)
        # end for
    # end merge_in
# end class Object

class Action(Instance):
    """
    The node for an Instance of an Action in the knowledge graph.

    ...

    Attributes
    ----------
    objects : dict[int, Object]
        All of the Objects participating in this action, keyed by their IDs. 
        The subject and object are members of the this dict.
    subject : Object, optional
        The node representing the subject of this action. The subject is the
        thing doing the action. Default value is None.
    object : Object, optional
        The node representing the object of this action. The object is the thing
        the action is being done to.

        Some actions do not have an object. Default value is None.
    scene_graph_rel : SceneGraphRelationship, optional
        All of the data from the scene graph for the relationship this node is
        based off of, if any.

        Default value is None.
    """
    def __init__(self, label: str, image: Image,
                 subject: Object = None, 
                 object: Object = None, 
                 scene_graph_rel: SceneGraphRelationship = None,
                 concepts: list[Concept] = list(),
                 hypothesized: bool=False):
        # Action node names are {label}_{image_index}_{id}
        if not subject is None:
            image = subject.get_image()
        name = (f'{label}_{image.index}_{Node._next_id}')
        super().__init__(label=label,
                         name=name, 
                         concepts=concepts,
                         image=image,
                         hypothesized=hypothesized)
        self.objects = dict()
        self.subject = subject
        self.object = object
        # Put the subject and object in the objects dict if they exist.
        if not subject is None:
            self.objects[subject.id] = subject
        if not object is None:
            self.objects[object.id] = object
        self.scene_graph_rel = scene_graph_rel
    # end __init__

    def add_object(self, object: Object):
        """
        Adds an object to this Action's dictionary of participating Objects.
        """
        self.objects[object.id] = object
    # end add_object
# end class Action

class Edge:
    """
    An edge in the knowledge graph between two Nodes.

    Is directional, has a relationship, and is, optionally, weighted.

    ...

    Attributes
    ----------
    id : int
        Unique int identifier for this edge.
    source : Node
        The start Node of the edge.
    target : Node
        The end Node of the edge.
    relationship : str
        The relationship between the source and target this edge represents.
    weight : float, optional
        The weight of the edge. Default value is 1.
    commonsense_edge : CommonSenseEdge, optional
        The CommonSenseEdge this edge came from, if any. Default value is None.
    hypothesized : bool
        Whether or not this Edge is hypothesized or observed. Default value
        is False.
    """
    # Class variable to make unique IDs when a new edge is made.
    _next_id = 0
    def __init__(self, source: Node, target: Node, relationship: str, 
                 weight: float = 1, hypothesized = False):
        self.id = Edge._next_id
        # Make sure to increment the next id class variable each time a new
        # id is assigned.
        Edge._next_id += 1
        self.source = source
        self.target = target
        self.relationship = relationship
        self.weight = weight
        self.commonsense_edge = None
        self.hypothesized = hypothesized
    # end __init__

    def __repr__(self):
        return (f'{self.source}->{self.relationship}->{self.target}' +
                f' ({self.weight})')
    # end __repr__

    def get_other_node(self, node: Node):
        """
        Returns the Node at the opposite side of the edge from the Node passed 
        in. Returns None if the Node passed in is neither the source nor target 
        of this edge.
        """
        if self.source == node:
            return self.target
        elif self.target == node:
            return self.source
        else:
            return None
    # end get_other_node

    def has_node(self, node: Node):
        """
        Checks whether or not this Edge is to or from the given Node.

        Returns True if either the source or target are the Node. Returns False
        if neither the source nor target are the Node.
        """
        if self.source == node or self.target == node:
            return True
        else:
            return False
    # end has_node
# end class Edge