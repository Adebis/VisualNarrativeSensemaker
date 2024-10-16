from dataclasses import dataclass
from typing import Optional

from commonsense.commonsense_data import CommonSenseNode, CommonSenseEdge
from constants import CausalFlowDirection

@dataclass
class CausalLink:
    '''
    Class representing a single-step causal link between two CommonSenseNodes.

    Attributes:
        source_cs_node: CommonSenseNode
            The start cs node of the edge.
        target_cs_node: CommonSenseNode
            The end cs node of the edge
        edge: CommonSenseEdge
            The edge containing the causal relationship for this causal link.
        direction: CausalFlowDirection
            The causal flow direction of the edge. Since this link shares
            a source and target node with the edge, this is also the causal
            flow direction for this causal link.
    '''
    source_cs_node: CommonSenseNode
    target_cs_node: CommonSenseNode
    edge: CommonSenseEdge
    direction: CausalFlowDirection

    def get_other_cs_node(self, cs_node: CommonSenseNode) -> CommonSenseNode | None:
        '''
        Gets the cs node which does not match the cs node passed in.
        Returns none if the cs node passed in matches neither source nor target.
        '''
        if self.source_cs_node == cs_node:
            return self.target_cs_node
        elif self.target_cs_node == cs_node:
            return self.source_cs_node
        else:
            print(f'CausalLink.get_other_cs_node: Error, cs node {cs_node}'
                  + ' is neither source nor target cs node.')
            return None
        # end if else
    # end get_other_cs_node

    def get_causal_flow_direction(self, source_node: CommonSenseNode) -> CausalFlowDirection | None:
        '''
        Get the causal flow direction using the cs node passed in as the
        source node.

        Returns None if the node passed in is neither the source nor the target
        node. 
        '''
        if self.source_cs_node == source_node:
            return self.direction
        elif self.target_cs_node == source_node:
            return CausalFlowDirection.reverse(self.direction)
        else:
            print(f'CausalLink.get_causal_flow_direction: Error, cs node {source_node}'
                  + ' is neither source nor target cs node.')
            return None
        # end if else
    # end get_causal_flow_direction

    def get_directional_source(self):
        '''
        Gets the cs node that is considered the source node in the direction of
        the link.

        If the direction is forward, source_cs_node is the directional source.
        If the direction is backward, target_cs_node is the directional source.
        '''
        if self.direction == CausalFlowDirection.FORWARD:
            return self.source_cs_node
        elif self.direction == CausalFlowDirection.BACKWARD:
            return self.target_cs_node
        else:
            print('CausalLink.get_directional_source: error! Direction '
                  + f'{self.direction} is neither forward nor backward.')
        # end if else
    # end get_directional_source
    def get_directional_target(self):
        '''
        Gets the cs node that is considered the target node in the direction of
        the link.

        If the direction is forward, target_cs_node is the directional target.
        If the direction is backward, source_cs_node is the directional target.
        '''
        if self.direction == CausalFlowDirection.FORWARD:
            return self.target_cs_node
        elif self.direction == CausalFlowDirection.BACKWARD:
            return self.source_cs_node
        else:
            print('CausalLink.get_directional_target: error! Direction '
                  + f'{self.direction} is neither forward nor backward.')
        # end if else
    # end get_directional_target

    def get_string(self):
        '''
        Gets a string version of this link in the form of:
            action_1 leads to action_2 because edge
        '''
        edge_string = (f'{self.source_cs_node.labels[0]}'
                       + f' {self.edge.get_relationship()}'
                       + f' {self.target_cs_node.labels[0]}')
        # If this link is backwards, switch the order of the triplet strings.
        if self.direction == 'backward':
            triplet_strings = (triplet_strings[1], triplet_strings[0])
        string_rep = (f'{self.get_directional_source().labels[0]} leads to'
                      + f' {self.get_directional_target().labels[0]} because'
                      + f' {edge_string}')
        return string_rep
    # end get_string

    def get_weight(self):
        '''
        Returns the weight of this causal link.

        The weight of this causal link is the weight of its edge.
        '''
        return self.edge.weight
    # end get_weight

    def __repr__(self):
        return self.get_string()
    # end __repr__
    
# end CausalLink

@dataclass
class MultiCausalLink:
    '''
    Class representing a multi-step causal link between two CommonSenseNodes.
    
    Attributes:
        source_cs_node: CommonSenseNode
        middle_cs_node: CommonSenseNode
        target_cs_node: CommonSenseNode
        source_middle_edge: CommonSenseEdge
        middle_target_edge: CommonSenseEdge
        direction: 'forward' or 'backward'
        
        id: Optional[int]
            A unique integer identifier for this link. Set automatically in 
            __post_init__.
    '''
    source_cs_node: CommonSenseNode
    middle_cs_node: CommonSenseNode
    target_cs_node: CommonSenseNode
    source_middle_edge: CommonSenseEdge
    middle_target_edge: CommonSenseEdge
    direction: str

    #id: Optional[int] = -1


    #_next_id = 0
    #def __post_init__(self):
    #    '''
    #    
    #    '''
    #    self.id = MultiCausalLink._next_id
    #    MultiCausalLink._next_id += 1
    ## end __post_init__

    def get_directional_source(self):
        '''
        Gets the cs node that is considered the source node in the direction of
        the link.

        If the direction is forward, source_cs_node is the directional source.
        If the direction is backward, target_cs_node is the directional source.
        '''
        if self.direction == 'forward':
            return self.source_cs_node
        elif self.direction == 'backward':
            return self.target_cs_node
        else:
            print('MultiCausalLink.get_directional_source: error! Direction '
                  + f'{self.direction} is neither forward nor backward.')
        # end if else
    # end get_directional_source
    def get_directional_target(self):
        '''
        Gets the cs node that is considered the target node in the direction of
        the link.

        If the direction is forward, target_cs_node is the directional target.
        If the direction is backward, source_cs_node is the directional target.
        '''
        if self.direction == 'forward':
            return self.target_cs_node
        elif self.direction == 'backward':
            return self.source_cs_node
        else:
            print('MultiCausalLink.get_directional_target: error! Direction '
                  + f'{self.direction} is neither forward nor backward.')
        # end if else
    # end get_directional_target

    def get_other_cs_node(self, cs_node: CommonSenseNode) -> CommonSenseNode | None:
        '''
        Gets the cs node which does not match the cs node passed in.
        Returns none if the cs node passed in matches neither source nor target.
        '''
        if self.source_cs_node == cs_node:
            return self.target_cs_node
        elif self.target_cs_node == cs_node:
            return self.source_cs_node
        else:
            print(f'CausalLink.get_other_cs_node: Error, cs node {cs_node}'
                  + ' is neither source nor target cs node.')
            return None
        # end if else
    # end get_other_cs_node

    def get_causal_flow_direction(self, source_node: CommonSenseNode) -> CausalFlowDirection | None:
        '''
        Get the causal flow direction using the cs node passed in as the
        source node.

        Returns None if the node passed in is neither the source nor the target
        node. 
        '''
        direction = CausalFlowDirection.FORWARD if self.direction == 'forward' else CausalFlowDirection.BACKWARD
        if self.source_cs_node == source_node:
            return direction
        elif self.target_cs_node == source_node:
            return CausalFlowDirection.reverse(direction)
        else:
            print(f'MultiCausalLink.get_causal_flow_direction: Error, cs node {source_node}'
                  + ' is neither source nor target cs node.')
            return None
        # end if else
    # end get_causal_flow_direction

    def get_query_string(self):
        '''
        Gets a string version of this link in the form of:
            action_1 leads to action_2 because edge_1 and edge_2
        '''
        triplet_strings = self.get_triplet_strings()
        # If this link is backwards, switch the order of the triplet strings.
        if self.direction == 'backward':
            triplet_strings = (triplet_strings[1], triplet_strings[0])
        string_rep = (f'{self.get_directional_source().labels[0]} leads to'
                      + f' {self.get_directional_target().labels[0]} because'
                      + f' {triplet_strings[0]} and'
                      + f' {triplet_strings[1]}.')
        return string_rep
    # end get_query_string

    def get_triplet_strings(self) -> tuple[str, str]:
        '''
        Gets a triplet string representation of this link's edges.

        Returns a pair of strings, one for each edge in the link.
        '''
        # Link one.
        # edge's source cs node's first label.
        # then the edge's relationship from get_relationship()
        # then the edge's target cs node's first label.
        source_1 = (
            self.source_cs_node 
            if self.source_middle_edge.start_node_id == self.source_cs_node.id
            else self.middle_cs_node
        )
        target_1 = (
            self.middle_cs_node
            if self.source_middle_edge.end_node_id == self.middle_cs_node.id
            else self.source_cs_node
        )
        triplet_string_1 = (f'{source_1.labels[0]}'
                            + f' {self.source_middle_edge.get_relationship()}'
                            + f' {target_1.labels[0]}')
        
        source_2 = (
            self.middle_cs_node 
            if self.middle_target_edge.start_node_id == self.middle_cs_node.id
            else self.target_cs_node
        )
        target_2 = (
            self.target_cs_node
            if self.middle_target_edge.end_node_id == self.target_cs_node.id
            else self.middle_cs_node
        )
        triplet_string_2 = (f'{source_2.labels[0]}'
                            + f' {self.middle_target_edge.get_relationship()}'
                            + f' {target_2.labels[0]}')
        return (triplet_string_1, triplet_string_2)
    # end get_triplet_strings

    def is_duplicate(self, other_link):
        '''
        Returns true if this link is a duplicate of the other link.

        Two links are duplicates if all of their fields are the same
        OR if their source and targets are opposites and their directions are
        opposites. Then, the two links are actually the same link
        but reversed.
        '''
        if self == other_link:
            return True
        if (self.source_cs_node == other_link.target_cs_node
            and self.target_cs_node == other_link.source_cs_node
            and self.middle_cs_node == other_link.middle_cs_node
            and (self.direction == 'backward' and other_link.direction == 'forward'
                 or self.direction == 'forward' and other_link.direction == 'backward')
            and self.source_middle_edge == other_link.middle_target_edge):
            return True
        return False
    # end is_duplicate

    def get_weight(self):
        '''
        Returns the weight of this multi-causal link.
        The weight is the average of the weights of both edges of this link.
        '''
        weight_sum = self.source_middle_edge.weight + self.middle_target_edge.weight
        weight_average = weight_sum / 2
        return weight_average
    # end  get_weight

    def __repr__(self):
        return self.get_query_string()
        
# end MultiCausalLink

class ImageCausalLink:
    '''
    Class representing a link between two images consisting of a pair of
    action instances, the CausalLink between them, the cs nodes of the link,
    and their action concepts.

    Attributes:
        source_node_id
        source_node_uri
        edge_id
        edge_uri
        weight
        target_node_id
        target_node_uri
        is_forward (0 for backward, 1 for forward)
            Whether the causal link direction is forward, from the source node
            to the target node, or backward, from the target node to the 
            source node.
        action_concept_id_1
        action_instance_id_1
        cs_node_id_1
        action_concept_id_2
        action_instance_id_2
        cs_node_id_2
    '''

    source_node_id: int
    source_node_uri: str
    edge_id: int
    edge_uri: str
    weight: float
    target_node_id: int
    target_node_uri: str
    is_forward: bool
    action_concept_id_1: int
    action_instance_id_1: int
    cs_node_id_1: int
    action_concept_id_2: int
    action_instance_id_2: int
    cs_node_id_2: int

    def __init__(self, row):
        '''
        Builds this image causal link from a database row.

        Each row has:
            0 - source_node_id
            1 - source_node_uri
            2 - edge_id
            3 - edge_uri
            4 - weight
            5 - target_node_id
            6 - target_node_uri
            7 - is_forward (0 for backward, 1 for forward)
            8 - action_concept_id_1
            9 - action_instance_id_1
            10 - cs_node_id_1
            11 - action_concept_id_2
            12 - action_instance_id_2
            13 - cs_node_id_2
        '''
        self.source_node_id = row[0]
        self.source_node_uri = row[1]
        self.edge_id = row[2]
        self.edge_uri = row[3]
        self.weight = row[4]
        self.target_node_id = row[5]
        self.target_node_uri = row[6]
        self.is_forward = True if row[7] == 1 else False
        self.action_concept_id_1 = row[8]
        self.action_instance_id_1 = row[9]
        self.cs_node_id_1 = row[10]
        self.action_concept_id_2 = row[11]
        self.action_instance_id_2 = row[12]
        self.cs_node_id_2 = row[13]
    # end __init__

    def get_true_direction(self):
        '''
        Get the causal flow direction of this image link, treating image 1 to
        image 2 as forward and image 2 to image 1 as backward.
        '''
        # First, get a direction from the direction of the causal link.
        direction = (CausalFlowDirection.FORWARD if self.is_forward 
                     else CausalFlowDirection.BACKWARD)
        # Reverse the direction if cs node 1 is actually the target of the
        # causal link.
        if self.cs_node_id_1 == self.target_node_id:
            direction = CausalFlowDirection.reverse(direction)
        return direction
# end ImageLink

class ImageMultiCausalLink:
    '''
    Class representing a link between two images consisting of a pair of
    action instances, the MultiCausalLink between them, the cs nodes of the 
    link, and their action concepts.

    Attributes:
        source_cs_node_id
        source_cs_node_uri
        middle_cs_node_id
        middle_cs_node_uri
        target_cs_node_id
        target_cs_node_uri
        source_middle_edge_id
        source_middle_edge_uri
        source_middle_edge_weight
        middle_target_edge_id
        middle_target_edge_uri
        middle_target_edge_weight
        direction ('forward' or 'backward')
        action_concept_id_1
        action_instance_id_1
        cs_node_id_1
        action_concept_id_2
        action_instance_id_2
        cs_node_id_2
    '''

    source_cs_node_id: int
    source_cs_node_uri: str
    middle_cs_node_id: int
    middle_cs_node_uri: str
    target_cs_node_id: int
    target_cs_node_uri: str
    source_middle_edge_id: int
    source_middle_edge_uri: str
    source_middle_edge_weight: float
    middle_target_edge_id: int
    middle_target_edge_uri: str
    middle_target_edge_weight: float
    direction: str
    action_concept_id_1: int
    action_instance_id_1: int
    cs_node_id_1: int
    action_concept_id_2: int
    action_instance_id_2: int
    cs_node_id_2: int

    def __init__(self, row):
        '''
        Builds this image multi causal link from a database row.

        Each row has:
            0 - source_cs_node_id
            1 - source_cs_node_uri
            2 - middle_cs_node_id
            3 - middle_cs_node_uri
            4 - target_cs_node_id
            5 - target_cs_node_uri
            6 - source_middle_edge_id
            7 - source_middle_edge_uri
            8 - source_middle_edge_weight
            9 - middle_target_edge_id
            10 - middle_target_edge_uri
            11 - middle_target_edge_weight
            12 - direction ('forward' or 'backward')
            13 - action_concept_id_1
            14 - action_instance_id_1
            15 - cs_node_id_1
            16 - action_concept_id_2
            17 - action_instance_id_2
            18 - cs_node_id_2
        '''
        self.source_cs_node_id = row[0]
        self.source_cs_node_uri = row[1]
        self.middle_cs_node_id = row[2]
        self.middle_cs_node_uri = row[3]
        self.target_cs_node_id = row[4]
        self.target_cs_node_uri = row[5]
        self.source_middle_edge_id = row[6]
        self.source_middle_edge_uri = row[7]
        self.source_middle_edge_weight = row[8]
        self.middle_target_edge_id = row[9]
        self.middle_target_edge_uri = row[10]
        self.middle_target_edge_weight = row[11]
        self.direction = row[12]
        self.action_concept_id_1 = row[13]
        self.action_instance_id_1 = row[14]
        self.cs_node_id_1 = row[15]
        self.action_concept_id_2 = row[16]
        self.action_instance_id_2 = row[17]
        self.cs_node_id_2 = row[18]
    # end __init__

    def get_true_direction(self):
        '''
        Get the causal flow direction of this image link, treating image 1 to
        image 2 as forward and image 2 to image 1 as backward.
        '''
        # First, get a direction from the direction of the causal link.
        direction = (CausalFlowDirection.FORWARD if self.direction == 'forward' 
                     else CausalFlowDirection.BACKWARD)
        # Reverse the direction if cs node 1 is actually the target of the
        # causal link.
        if self.cs_node_id_1 == self.target_cs_node_id:
            direction = CausalFlowDirection.reverse(direction)
        return direction
    # end get_true_direction

    def get_weight(self):
        '''
        Get the average weight of this multi causal link's edges.
        '''
        return (self.source_middle_edge_weight + self.middle_target_edge_weight) / 2
# end ImageMultiCausalLink

@dataclass
class ActionLink:
    '''
    A class representing the causal links between two ActionConcepts.

    Attributes:
        source_action_id: int
            Id of one of the causally linked ActionConcepts.
        target_action_id: int
            Id of of the other causally linked ActionConcept.
        forward_causal_links: list[CausalLink]
            All of the single-step causal links whose causal flow is from the 
            source action to the target action. 
        backward_causal_links: list[CausalLink]
            All of the single-step causal links whose causal flow is from the 
            target action to the source action.
        forward_multi_causal_links: list[MultiCausalLink]
            All of the multi-step causal links whose causal flow is from the 
            source action to the target action. 
        backward_multi_causal_links: list[MultiCausalLink]
            All of the multi-step causal links whose causal flow is from the 
            target action to the source action.
    '''

    source_action_id: int
    target_action_id: int
    forward_causal_links: list[CausalLink]
    backward_causal_links: list[CausalLink]
    forward_multi_causal_links: list[MultiCausalLink]
    backward_multi_causal_links: list[MultiCausalLink]

    def add_causal_link(self, 
                        causal_link: CausalLink, 
                        direction: CausalFlowDirection):
        '''
        Adds a CausalLink to this ActionLink in the direction specified.
        '''
        if direction == CausalFlowDirection.FORWARD:
            self.forward_causal_links.append(causal_link)
        else:
            self.backward_causal_links.append(causal_link)
        # end if
    # end add_causal_link
    def add_multi_causal_link(self,
                              multi_causal_link: MultiCausalLink,
                              direction: CausalFlowDirection):
        '''
        Adds a MultiCausalLink to this ActionLink in the direction specified.
        '''
        if direction == CausalFlowDirection.FORWARD:
            self.forward_multi_causal_links.append(multi_causal_link)
        else:
            self.backward_multi_causal_links.append(multi_causal_link)
        # end if
    # end add_multi_causal_link

    # Accessors
    def get_multi_causal_links(self) -> list[MultiCausalLink]:
        all_multi_causal_links = list()
        all_multi_causal_links.extend(self.forward_multi_causal_links)
        all_multi_causal_links.extend(self.backward_multi_causal_links)
        return all_multi_causal_links
    # end get_multi_causal_links

    def contains_multi_causal_link(self, multi_causal_link: MultiCausalLink):
        '''
        Returns True if the MultiCausalLink passed in is either in the forward
        or backward multi causal links lists for this ActionLink.

        Returns False otherwise.
        '''
        if (multi_causal_link in self.forward_multi_causal_links
            or multi_causal_link in self.backward_multi_causal_links):
            return True
        else:
            return False
        # end else
    # end contains_multi_causal_link

    def contains_causal_link(self, causal_link: CausalLink):
        '''
        Returns True if the CausalLink passed in is either in the forward
        or backward causal links lists for this ActionLink.

        Returns False otherwise.
        '''
        if (causal_link in self.forward_causal_links 
            or causal_link in self.backward_causal_links):
            return True
        else:
            return False
    # end contains_causal_link

    def has_causal_link(self):
        '''
        Returns True if this ActionLink has any single-step causal links
        in either direction. Returns False otherwise.
        '''
        if (len(self.forward_causal_links) > 0
            or len(self.backward_causal_links) > 0):
            return True
        else:
            return False
    # end has_causal_link

    def has_multi_causal_link(self):
        '''
        Returns true if this ActionLink has any multi-step causal links
        in either direction. Returns False otherwise.
        '''
        if (len(self.forward_multi_causal_links) > 0
            or len(self.backward_multi_causal_links) > 0):
            return True
        else:
            return False
    # end has_multi_causal_link

    def multi_causal_link_count(self):
        '''
        Returns the number of forward and backward multi-step causal links.
        '''
        return len(self.forward_multi_causal_links) + len(self.backward_multi_causal_links)
    # end multi_causal_link_count

    def get_weight_sums(self):
        '''
        Get the sum of the weights of the causal links in both directions.
        Returns them in a tuple, with the forward weight sum as the first item
        and the backwards weight sum as the second item.
        '''
        forward_weight = 0
        backward_weight = 0
        for link in self.forward_causal_links:
            forward_weight += link.get_weight()
        for link in self.backward_causal_links:
            backward_weight += link.get_weight()
        '''
        for link in self.forward_multi_causal_links:
            forward_weight += link.get_weight()
        for link in self.backward_multi_causal_links:
            backward_weight += link.get_weight()
        '''
        return forward_weight, backward_weight
    # end get_weight_sums

    def get_causal_direction(self):
        '''
        Gets the direction of this link.

        If there are only causal links in one direction, gets that direction.
        If there are causal links in both direction or no causal links in either
        direction, returns CausalFlowDirection.NEUTRAL
        '''
        if len(self.forward_causal_links) > 0:
            if len(self.backward_causal_links) > 0:
                return CausalFlowDirection.NEUTRAL
            else:
                return CausalFlowDirection.FORWARD
        elif len(self.backward_causal_links) > 0:
            return CausalFlowDirection.BACKWARD
        else:
            return CausalFlowDirection.NEUTRAL
    # end get_causal_link_direction

    def contains_one_of(self, causal_links: list[CausalLink]):
        '''
        Returns True if this action link contains one of the causal links in
        the list passed in. Returns False otherwise.
        '''
        for causal_link in causal_links:
            if causal_link in self.forward_causal_links:
                return True
            if causal_link in self.backward_causal_links:
                return True
        # end for
        return False
    # end contains_one_of

    def __repr__(self):
        '''
        
        '''
        return (f'Action Link {self.source_action_id}-{self.target_action_id}')
    # end __repr__
# end ActionLink