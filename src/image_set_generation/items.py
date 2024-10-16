from dataclasses import dataclass

from input_handling.scene_graph_data import BoundingBox, Image
from commonsense.commonsense_data import CommonSenseNode, CommonSenseEdge


from image_set_generation.links import CausalLink, MultiCausalLink, ActionLink

from constants import CausalFlowDirection

@dataclass 
class CommonSenseNodeCluster:
    '''
    A class representing a group of CommonSenseNodes that all start with
    the same URI.

    All CommonSenseNodeClusters have a root CommonSenseNode. The URI of every
    other node in the cluster starts with the URI of the root node.

    Attributes:
        root_id: int
            The cs_node_id of the root cs_node of the cluster.
        cs_nodes: dict[int, CommonSenseNode]
            The CommonSenseNodes in the cluster, keyed by their ids.
    '''
    root_id: int
    cs_nodes: dict[int, CommonSenseNode]

    def nodes(self) -> list[CommonSenseNode]:
        return self.cs_nodes.values()
    # end nodes

    def get_root(self):
        return self.cs_nodes[self.root_id]
    # end get_root
# end class CommonSenseNodeCluster

@dataclass
class ActionConcept:
    '''
    A class representing the concept for an action.

    Coincides with a single action_label in the database, as well as
    all of its CommonSenseNodes.

    Attributes:
        id: int
            A unique identifier for the word representing this action. 
        name: str
            A word or phrase representing this action. 
        cs_nodes: dict[int, CommonSenseNode]
            The CommonSenseNodes associated with this action, keyed by their
            ids.
        action_links: dict[int, ActionLink]
            All of the causal links this action has to other action concepts.
            Key: action_concept_id of the other action concept, int.
            Value: ActionLink.
        instances_by_subject: dict[int, dict[int, set[int]]]
            The object concept ids of all of the subjects this action was paired 
            with in an image, as well as a list of the ids of the images in 
            which they were paired.
            Key 1: object concept id, int.
            Key 2: image id, int.
            Value: Set of ids of action instances.
        instances_by_object: dict[int, dict[int, set[int]]]
            The object concept ids of all of the subjects this action was paired 
            with in an image, as well as a list of the ids of the images in 
            which they were paired.
            Key 1: object concept id, int.
            Key 2: image id, int.
            Value: Set of ids of action instances.
        action_instance_ids: dict[int, set[int]]
            Ids of all of the ActionInstances for this ActionConcept, keyed by
            the ids of the images each instance is in.
            Key: image id, int
            Value: set of action instance ids, set[int]
    '''

    id: int
    name: str
    cs_nodes: dict[int, CommonSenseNode]
    action_links: dict[int, ActionLink]
    instances_by_subject: dict[int, dict[int, set[int]]]
    instances_by_object: dict[int, dict[int, set[int]]]
    action_instance_ids: dict[int, set[int]]

    #paired_objects: dict[int, list[int]]

    def add_causal_link(self, 
                        causal_link: CausalLink, 
                        other_action_concept_id: int,
                        direction: CausalFlowDirection):
        '''
        Adds a CausalLink to another action in the given direction to this
        action's set of ActionLinks.

        Makes an ActionLink to the other action if one does not exist already.
        '''
        if not other_action_concept_id in self.action_links:
            action_link = ActionLink(source_action_id=self.id,
                                     target_action_id=other_action_concept_id,
                                     forward_causal_links=list(),
                                     backward_causal_links=list(),
                                     forward_multi_causal_links=list(),
                                     backward_multi_causal_links=list())
            self.action_links[other_action_concept_id] = action_link
        # end if
        self.action_links[other_action_concept_id].add_causal_link(causal_link,
                                                                   direction)
    # end add_causal_link
    def add_multi_causal_link(self, 
                              multi_causal_link: MultiCausalLink, 
                              other_action_concept_id: int,
                              direction: CausalFlowDirection):
        '''
        Adds a MultiCausalLink to another action in the given direction to this
        action's set of ActionLinks.

        Makes an ActionLink to the other action if one does not exist already.
        '''
        if not other_action_concept_id in self.action_links:
            action_link = ActionLink(source_action_id=self.id,
                                     target_action_id=other_action_concept_id,
                                     forward_causal_links=list(),
                                     backward_causal_links=list(),
                                     forward_multi_causal_links=list(),
                                     backward_multi_causal_links=list())
            self.action_links[other_action_concept_id] = action_link
        # end if
        self.action_links[other_action_concept_id].add_multi_causal_link(
            multi_causal_link, direction)
    # end add_multi_causal_link

    def get_image_ids(self) -> set[int]:
        '''
        Get the ids of all the images that this ActionConcept has an
        ActionInstance in.
        '''
        return set(self.action_instance_ids.keys())
    # end get_image_ids

    def get_object_paired_image_ids(self):
        '''
        Gets the ids of all the images where this action concept has an
        action instance that has either a subject or an object.
        '''
        image_ids = set()
        for id, inner_dict in self.instances_by_subject.items():
            image_ids.update(set(inner_dict.keys()))
        for id, inner_dict in self.instances_by_object.items():
            image_ids.update(set(inner_dict.keys()))
        
        return image_ids
    # end get_object_paired_image_ids

    def get_linked_action_concept_ids(self, causal_links: list[CausalLink] = list()):
        '''
        Gets the ids of all the action concepts that have an action link
        with this action concept.

        Optionally only counts those action links which include at least one
        of the causal links in the list.
        '''
        if len(causal_links) == 0:
            return set(self.action_links.keys())
        ids = set()
        for action_concept_id, action_link in self.action_links.items():
            if action_link.contains_one_of(causal_links):
                ids.add(action_concept_id)
        # end for
        return ids
    # end get_linked_action_concept_ids

    def get_forward_linked_action_concept_ids(self):
        '''
        Gets the ids of all the action concept that this action concept
        has a forward causal link with.
        '''
        ids = set()
        for action_concept_id, action_link in self.action_links.items():
            if len(action_link.forward_causal_links) > 0:
                ids.add(action_concept_id)
        # end for
        return ids
    # end get_forward_linked_action_concept_ids

    def get_dominant_action_link_direction(self, other_action_concept_id):
        '''
        Get the dominant direction of the action link between this action 
        concept and another action concept, where this concept -> other concept 
        is forward and other concept -> this concept is backward.

        A direction is dominant if the sum of the weights of the causal links
        and multi causal links in that direction is greater than that of the 
        other direction. 
        '''
        action_link = self.action_links[other_action_concept_id]
        forward_sum, backward_sum = action_link.get_weight_sums()
        causal_direction = (CausalFlowDirection.FORWARD if forward_sum > backward_sum
                            else CausalFlowDirection.BACKWARD)
        return causal_direction
    # end get_true_action_link_direction

    '''
    def get_shared_object_ids(self, other_action) -> list[int]:
        
        Returns a list of the ids of all of the objects paired with both
        this action and the action passed in.

        Returns the empty list of there are no shared objects.
        
        shared_object_ids = list(set(self.paired_objects.keys()).intersection(
            set(other_action.paired_objects.keys())
        ))
        return shared_object_ids
    # end get_shared_object_ids

    def get_paired_object_image_ids(self, 
                                    object_label_id: int) -> list[int]:
        
        Returns a list of the ids of all the images where this action is paired
        with the object label.
        
        return self.paired_objects[object_label_id]
    # end get_paired_object_image_ids
    '''

    def __repr__(self):
        repr_string = f'action {self.id}: {self.name}'
        return repr_string
    # end __repr__

# end class ActionConcept

@dataclass
class ObjectConcept:
    '''
    A class representing the concept for an object.

    Coincides with a single object_concept_id and object_concept_name in the 
    database.

    Attributes:
        object_concept_id: int
        object_concept_name: str
        cs_nodes: list[CommonSenseNode]

        paired_actions: dict[int, list[int]]
        image_occurrences: dict[int, int]
            The images that this object occurs in, as well as the number of
            times it occurs in that image.
    '''
    id: int
    name: str
    cs_nodes: list[CommonSenseNode]
    #paired_actions: dict[int, list[int]]
    #image_occurrences: dict[int, int]


    #def get_images(self, min_occurrence_count: int=1) -> list[int]:
    #    '''
    #    Get the ids of all the images where this object occurs the
    #    specified minimum number of times or greater.
    #    '''
    #    image_ids = [id for id, count in self.image_occurrences.items()
    #                 if count >= min_occurrence_count]
    #    return image_ids
    ## end get_images

    def __repr__(self):
        repr_string = f'object {self.id}: {self.name}'
        return repr_string
    # end __repr__

# end class ObjectConcept

@dataclass
class ObjectInstance:
    '''
    A class representing an instance of an ObjectConcept.

    Attributes:        
        id: int
            A unique int identifier. Derived from the last part of the object's
            name after splitting by '_'.
        name: str
        object_concept_id: int
            The id of the ObjectConcept corresponding to this action's 
            action_label.
        image_id: int
        bounding_box: BoundingBox
        attributes: set[str]
        color_attributes: set[str]
    '''
    id: int
    name: str
    object_concept_id: int
    image_id: int
    bounding_box: BoundingBox
    attributes: set[str]
    color_attributes: set[str]

    def shares_colors(self, other_object_instance):
        '''
        Returns True if this object instance shares at least one color
        attribute with the object instance passed in.

        Returns False otherwise.
        '''
        shared_colors = self.color_attributes.intersection(other_object_instance.color_attributes)
        return True if len(shared_colors) > 0 else False
    # end shares_colors

# end class ObjectInstance

@dataclass
class ActionInstance:
    '''
    A class representing an instance of an ActionConcept.

    Corresponds to either one (if it only has a subject) or two (if it has a
    subject and an object) rows in the image_object_action_pairs table.

    Attributes:
        id: int
            A unique int identifier. Derived from the last part of the action's
            name after splitting by '_'.
        name: str
        action_concept: int
            The id of the ActionConcept corresponding to this action's 
            action_label.
        image_id: int
        subject: ObjectInstance | None
        object_: ObjectInstance | None
        subject_concept_id: int | None
        object_concept_id: int | None
    '''
    
    id: int
    name: str
    action_concept_id: int
    image_id: int
    subject: ObjectInstance | None
    object_: ObjectInstance | None
    subject_concept_id: int | None
    object_concept_id: int | None

# end class ActionInstance

@dataclass
class ImageInstance:
    '''
    
    Attributes:
        id: int
        object_instances: dict[int, ObjectInstance]
        objects_by_concept: dict[int, ObjectInstance]
            The object instances in this ImageInstance keyed by the id its
            object concept.
        action_instances: dict[int, ActionInstance]
        actions_by_concept: dict[int, list[ActionInstance]]
        actions_by_subject: dict[int, ActionInstance]
            The ids of action instances in this ImageInstance keyed by the id 
            of the concept of their subject instance.
        actions_by_object: dict[int, ActionInstance]
            The ids of action instances in this ImageInstance keyed by the id of 
            the concept of their object instance.
        image: Image
    '''
    id: int
    object_instances: dict[int, ObjectInstance]
    objects_by_concept: dict[int, list[ObjectInstance]]
    action_instances: dict[int, ActionInstance]
    actions_by_concept: dict[int, list[ActionInstance]]
    actions_by_subject: dict[int, list[int]]
    actions_by_object: dict[int, list[int]]
    image: Image

    def add_object_instance(self, object_instance: ObjectInstance):
        if not object_instance.id in self.object_instances:
            self.object_instances[object_instance.id] = object_instance
            # Populate the objects by concept dict as well.
            id = object_instance.object_concept_id
            if not id in self.objects_by_concept:
                self.objects_by_concept[id] = list()
            self.objects_by_concept[id].append(object_instance)
        # end if
    # end add_object_instance
    
    def add_action_instance(self, action_instance: ActionInstance):
        if not action_instance.id in self.action_instances:
            self.action_instances[action_instance.id] = action_instance
            # Populate the actions by subject and object dicts as well.
            if action_instance.subject is not None:
                id = action_instance.subject.object_concept_id
                #self.actions_by_subject[id] = action_instance
            if action_instance.object_ is not None:
                id = action_instance.object_.object_concept_id
                #self.actions_by_object[id] = action_instance
            # end if
            # Populate the actions by concept dict as well.
            id = action_instance.action_concept_id
            if not id in self.actions_by_concept:
                self.actions_by_concept[id] = list()
            self.actions_by_concept[id].append(action_instance)
        # end if
    # end add_action_instance
# end ImageInstance

class ActionObjectPair:
    '''
    A class representing a row from the image_action_object_pairs table.

    Attributes:
        image_id: int
        action_instance_id: int
        action_instance_name: str
        object_instance_id: int
        object_instance_name: str
        object_role: str
        action_concept_id: int
        object_concept_id: int
    '''

    image_id: int
    action_instance_id: int
    action_instance_name: str
    object_instance_id: int
    object_instance_name: str
    object_role: str
    action_concept_id: int
    object_concept_id: int

    def __init__(self, row):
        self.image_id = row[0]
        self.action_instance_id = row[1]
        self.action_instance_name = row[2]
        self.object_instance_id = row[3]
        self.object_instance_name = row[4]
        self.object_role = row[5]
        self.action_concept_id = row[6]
        self.object_concept_id = row[7]
    # end __init__

# end ActionObjectPair