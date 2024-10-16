import cv2
from skimage.metrics import structural_similarity

import constants as const
from constants import (CausalFlowDirection)

from knowledge_graph.items import (Concept, Instance, Object, Action, Edge,
                                   EdgeRelationship)
from knowledge_graph.path import (Step, Path, MultiStep, MultiPath)

class Evidence:
    """
    Base class for a piece of evidence supporting (or refuting) a Hypothesis.

    Attributes
    ----------
    id : int
        A unique int identifier for this evidence.
    score : float
        The Evidence's score. For use in MOOP solving.
    premise_hyp_ids : list[int]
        The IDs of the hypotheses this evidence is premised on, if any. 
    """
    id: int
    score: float
    premise_hyp_ids: list[int]

    # Class variable for making unique ids whenever a new piece of evidence is 
    # made.
    _next_id = 0

    def __init__(self, premise_hyp_ids: list[int]):
        self.id = Evidence._next_id
        Evidence._next_id += 1
        self.score = 0
        premise_hyp_ids = premise_hyp_ids
    # end __init__
# end Evidence

class VisualSimEv(Evidence):
    """
    Evidence consisting of the visual similarity between the appearance of two
    Objects.

    Attributes
    ----------
    object_1 : Object
        One of the Objects.
    object_2 : Object
        The other Object.
    """

    def __init__(self, object_1: Object, object_2: Object):
        """
        Initializes with the two Objects.

        Calculates the visual similarity between them based on their appearance
        attributes. 
        """
        # Pass the IDs of any source hypotheses of the objects passed in
        # as premises for this evidence.
        super().__init__([obj.source_hyp_id for obj in [object_1, object_2]
                          if obj.hypothesized])
        self.object_1 = object_1
        self.object_2 = object_2
        # Calculate the visual similarity between these two Objects' appearances.
        # Uses SSIM, the Structural Similarity Index Measure.
        appearance_1 = object_1.appearance
        appearance_2 = object_2.appearance
        # In the special case that the Objects are exactly the same,
        # just set a similarity of 1.0 without calculating.
        if object_1 == object_2:
            self.score = 1.0
        else:
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
            # The score of this piece of evidence is the similarity between
            # their appearances.
            self.score = similarity
        # end if else
    # end __init__

    def __repr__(self):
        return (f'VisualSimEv: {self.object_1}|{self.object_2}: {self.score}')
    # end __repr__
# end class VisualSimEv

class AttributeSimEv(Evidence):
    """
    Evidence consisting of the similarity between the attributes of two Objects.

    Here, 'attribute' refers to the attributes the Objects are annotated with
    in a scene graph or are given when they are created.

    Attributes
    ----------
    object_1 : Object
        One of the Objects.
    object_2 : Object
        The other Object.
    """

    def __init__(self, object_1: Object, object_2: Object):
        """
        Initializes with the two Objects.

        Calculates the attribute similarity between the by comparing their
        attributes and seeing which ones match.
        """
        # Pass the IDs of any source hypotheses of the objects passed in
        # as premises for this evidence.
        super().__init__([obj.source_hyp_id for obj in [object_1, object_2]
                          if obj.hypothesized])
        self.object_1 = object_1
        self.object_2 = object_2
        # Judge their similarity by seeing how many of the attributes directly
        # match each other. 
        similarity = 0
        for attribute_1 in object_1.attributes:
            if attribute_1 in object_2.attributes:
                similarity += 1
        # end for
        # Normalize for the number of attributes.
        attribute_count = len(object_1.attributes) + len(object_2.attributes)
        if not attribute_count == 0:
            similarity = similarity / (attribute_count / 2)
        # The score for this piece of evidence is the similarity score. 
        self.score = similarity
    # end __init__

    def __repr__(self):
        return (f'AttributeSimEv {self.object_1}|{self.object_2}: {self.score}')
    # end __repr__

# end class AttributeSimEv

class CausalPathEv(Evidence):
    """
    Evidence consisting of a path following causal connections between the Concepts 
    of one Action and the Concepts of another Action. 

    Attributes
    ----------
    source_action : Action
        The Action whose concepts the path starts at.
    target_action : Action
        The Action whose concepts the path ends at.
    source_concept : Concept
        The concept the path starts at.
    target_concept : Concept
        The concept the path ends at.
    concept_path : Path
        The Path from the source Concept to the target Concept.
    direction : CausalFlowDirection
        The direction that the path asserts is the flow of causality.
        Forward means causality flows from the source action to the target
        action, e.g. source_action happens before target_action.
        Backwards means causality flows from the target action to the source
        action, e.g. target_action happens before source_action.
    """

    source_action: Action
    target_action: Action
    source_concept: Concept
    target_concept: Concept
    concept_path: Path
    direction: CausalFlowDirection

    def __init__(self, source_action: Action, target_action: Action,
                 source_concept: Concept, target_concept: Concept,
                 concept_path: Path):
        # Pass the IDs of any source hypotheses of the actions passed in
        # as premises for this evidence.
        super().__init__([action.source_hyp_id for action in [source_action, target_action]
                          if action.hypothesized])
        self.source_action = source_action
        self.target_action = target_action
        self.source_concept = source_concept
        self.target_concept = target_concept
        self.concept_path = concept_path
        
        # Determine the causal flow direction of this piece of evidence by
        # the causal flow direction of each step in the path.
        path_direction = CausalFlowDirection.NONE
        for step in concept_path.steps:
            if step.next_edge is None:
                continue
            next_edge_relationship = step.next_edge.relationship.split('/')[-1]
            # Get the direction of the edge's relationship.
            next_edge_direction = CausalFlowDirection.NEUTRAL
            if next_edge_relationship in const.CAUSAL_RELATIONSHIP_DIRECTION:
                next_edge_direction = const.CAUSAL_RELATIONSHIP_DIRECTION[next_edge_relationship]
            # If the next_edge_direction is either forward or backward, see if
            # the edge is pointing from the current step's node to the next
            # step's node (is forward) or not (is backward).
            # If it's backward, flip the next_edge_direction.
            edge_is_forward = True if step.node == step.next_edge.source else False
            if not edge_is_forward:
                if next_edge_direction == CausalFlowDirection.FORWARD:
                    next_edge_direction = CausalFlowDirection.BACKWARD
                elif next_edge_direction == CausalFlowDirection.BACKWARD:
                    next_edge_direction = CausalFlowDirection.FORWARD
                # end elif
            # end if
                    
            if (path_direction == CausalFlowDirection.NONE
                or path_direction == next_edge_direction):
                path_direction = next_edge_direction
            else:
                path_direction = CausalFlowDirection.NEUTRAL
            
        # end for
        self.direction = path_direction

        # Calculate the score based on the average score of every edge in
        # the path.
        # The number of edges in the path is one less than the length of
        # the path.
        total_score = sum([step.previous_edge.weight for step in self.concept_path.steps
                           if step.previous_edge is not None])
        self.score = total_score / (len(self.concept_path.steps) - 1)
    # end __init__

# end CausalPathEv

class MultiCausalPathEv(Evidence):
    """
    Evidence consisting of a MultiPath following causal connections between the 
    Concepts of one Action and the Concepts of another Action. 

    Attributes
    ----------
    source_action : Action
        The Action whose concepts the path starts at.
    target_action : Action
        The Action whose concepts the path ends at.
    source_concepts : list[Concept]
        The concepts the path starts at.
    target_concepts : list[Concept]
        The concepts the path ends at.
    concept_path : MultiPath
        The MultiPath from the source Concept to the target Concept.
    direction : CausalFlowDirection
        The direction that the path asserts is the flow of causality.
        Forward means causality flows from the source action to the target
        action, e.g. source_action happens before target_action.
        Backwards means causality flows from the target action to the source
        action, e.g. target_action happens before source_action.
    """

    source_action: Action
    target_action: Action
    source_concepts: list[Concept]
    target_concepts: list[Concept]
    concept_path: MultiPath
    direction: CausalFlowDirection

    def __init__(self, source_action: Action, target_action: Action,
                 source_concepts: list[Concept], target_concepts: list[Concept],
                 concept_path: MultiPath):
        # Pass the IDs of any source hypotheses of the actions passed in
        # as premises for this evidence.
        super().__init__([action.source_hyp_id for action in [source_action, target_action]
                          if action.hypothesized])
        self.source_action = source_action
        self.target_action = target_action
        self.source_concepts = source_concepts
        self.target_concepts = target_concepts
        self.concept_path = concept_path
        
        # Determine the causal flow direction of this piece of evidence by
        # the causal flow direction of each step in the path.
        path_direction = CausalFlowDirection.NONE
        for step in concept_path.steps:
            if len(step.next_edges) == 0:
                continue
            for next_edge in step.next_edges:
                next_edge_relationship = next_edge.relationship.split('/')[-1]
                # Get the direction of the edge's relationship.
                next_edge_direction = CausalFlowDirection.NEUTRAL
                if next_edge_relationship in const.CAUSAL_RELATIONSHIP_DIRECTION:
                    next_edge_direction = const.CAUSAL_RELATIONSHIP_DIRECTION[next_edge_relationship]
                # If the next_edge_direction is either forward or backward, see if
                # the edge is pointing from the current step's node to the next
                # step's node (is forward) or not (is backward).
                # If it's backward, flip the next_edge_direction.
                edge_is_forward = False
                for node in step.nodes:
                    if node == next_edge.source:
                        edge_is_forward = True
                        break
                # end for
                
                if not edge_is_forward:
                    if next_edge_direction == CausalFlowDirection.FORWARD:
                        next_edge_direction = CausalFlowDirection.BACKWARD
                    elif next_edge_direction == CausalFlowDirection.BACKWARD:
                        next_edge_direction = CausalFlowDirection.FORWARD
                    # end elif
                # end if
                
                if (path_direction == CausalFlowDirection.NONE
                    or path_direction == next_edge_direction):
                    path_direction = next_edge_direction
                else:
                    # Once we know the path direction is neutral, we can
                    # stop. It won't turn Forward or Back again. 
                    path_direction = CausalFlowDirection.NEUTRAL
                    break
            # end for next_edge
            if path_direction == CausalFlowDirection.NEUTRAL:
                break
        # end for
        self.direction = path_direction

        # Calculate the score based on the average score of every edge in
        # the path.
        # Sum the scores of every edge between two MultiSteps of the path.
        # Also count the total number of edges between every step of the path.
        total_score_sum = 0
        edge_count = 0
        for step in self.concept_path.steps:
            for edge in step.next_edges:
                edge_count += 1
                total_score_sum += edge.weight
            # end for
        # end for

        self.score = total_score_sum / edge_count
    # end __init__

# end MultiCausalPathEv
        
class ContinuityEv(Evidence):
    """
    Evidence consisting of a SameObjectHyp between the objects of two actions.

    Attributes
    ----------
    source_action : Action

    target_action : Action

    source_object : Object

    target_object : Object

    joining_hyp : SameObjectHyp
        The SameObjectHyp between the source_object and the target_object.
    """

    source_action: Action
    target_action: Action
    source_object: Object
    target_object: Object

    def __init__(self, source_action: Action,
                 target_action: Action,
                 source_object: Object,
                 target_object: Object,
                 joining_hyp):
        # Premised on the joining hypothesis.
        super().__init__([joining_hyp.id])
        self.source_action = source_action
        self.target_action = target_action
        self.source_object = source_object
        self.target_object = target_object
        self.joining_hyp = joining_hyp
        # Score is based on the joining hypothesis' score, which won't be
        # known until later.
    # end __init__
        
# end ContinuityEv 