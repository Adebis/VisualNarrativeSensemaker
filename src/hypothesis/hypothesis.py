from typing import Union

import constants as const
from constants import (CausalFlowDirection)

from knowledge_graph.items import (Concept, Instance, Object, Action, Edge,
                                   EdgeRelationship)
from hypothesis.evidence import (VisualSimEv, AttributeSimEv, CausalPathEv,
                                 ContinuityEv, MultiCausalPathEv)
from parameters import ParameterSet

class Hypothesis:
    """
    Base class for the Sensemaker's hypotheses.

    Attributes
    ----------
    id : int
        A unique integer identifier.
    name : str
        A human-readable string identifier. Should be unique per Hypothesis,
        but doesn't have to be.
    premises : dict[int, Hypothesis]
        A set of other Hypotheses that must be accepted for this Hypothesis
        to be accepted. Keyed by Hypothesis id. Default value is the empty dict.
    """
    # Class variable to make unique IDs when a new hypothesis is made.
    _next_id = 0

    def __init__(self, name: str):
        self.id = Hypothesis._next_id
        Hypothesis._next_id += 1
        self.name = name
        self.premises = dict()
    # end __init__

    def add_premise(self, premise):
        """
        Adds another Hypothesis as a premise for this Hypothesis.
        """
        self.premises[premise.id] = premise
    # end add_premise

    def get_premise_individual_score(self):
        """
        Gets the sum contribution of each of this hypothesis' premises to its
        individual score.
        """
        # Gives the individual score a large negative value for each premise
        # so that this hypothesis will not be accepted without its premise.
        return -len(self.premises) * const.H_SCORE_OFFSET
    # end _get_premise_individual_score

    def get_premise_paired_scores(self) -> dict[int, float]:
        """
        Gets the contribution of each of this hypothesis' premises to its
        paired scores.

        Returns a dictionary of scores keyed by hypothesis id.
        """
        # Gives each pair score a large positive value to counter the large
        # negative value in _get_premise_individual_score, allowing this
        # hypothesis to be accepted if its premise hypothesis is accepted.
        return {h.id: const.H_SCORE_OFFSET for h in self.premises.values()}
    # end _get_premise_paired_scores

# end class Hypothesis

class SameObjectHyp(Hypothesis):
    """
    A Hypothesis that two Object Instances represent the same Object. 

    If the Hypothesis is accepted, the two Objects would get a 'duplicate-of'
    Edge between them. 

    Evidence is the VisualSimEv between the two Objects'
    appearances and the AttributeSimEv between the two Objects'
    attributes.

    Attributes
    ----------
    object_1 : Object
        One of the Objects
    object_2 : Object
        The other Object.
    edge : Edge
        The 'duplicate-of' edge between object 1 and object 2. The weight of
        the edge represents the similarity between the two Objects.
    visual_sim_ev : VisualSimEv
        Evidence consisting of the visual similarity between object 1 and object
        2.
    attribute_sim_ev : AttributeSimEv
        Evidence consisting of the attribute similarity between object 1 and
        object 2.
    """

    def __init__(self, object_1: Object, object_2: Object):
        """
        Initializes with the two Objects that are being hypothesized as
        duplicates of one another. 

        Builds its own VisualSimEv and AttributeSimEv.

        Also makes the duplicate-of Edge that would be applied to both Objects.
        """
        name = (f'dup_h_{Hypothesis._next_id}_{object_1.name}_{object_2.name}')
        super().__init__(name)
        self.object_1 = object_1
        self.object_2 = object_2
        self.visual_sim_ev = VisualSimEv(object_1, object_2)
        self.attribute_sim_ev = AttributeSimEv(object_1, object_2)
        # The weight of this edge would be the score of this hypothesis, which
        # won't be known for sure until we know what parameter set is being used
        # to score the Hypothesis.
        # For now, set it to 0.
        self.edge = Edge(source=self.object_1, target=self.object_2,
                         relationship=str(EdgeRelationship.DUPLICATE_OF), 
                         weight=0,
                         hypothesized=True)
    # end __init__

    def __repr__(self):
        return (f'{self.object_1}->duplicate-of->{self.object_2}')
    # end __repr__

    def has_object(self, object: Object):
        """
        Whether or not the Object passed in is one of the two Objects this 
        SameObjectHyp is between.
        """
        return (True if (self.object_1 == object or self.object_2 == object) 
                else False)
    # end has_object

    def has_object_concept(self, object_: Object):
        '''
        Whether or not the concept of the Object passed in is the concept of
        one of the two Objects this SameObjectHyp is between.
        '''
        if (self.object_1.has_concept(object_.concepts[0])
            or self.object_2.has_concept(object_.concepts[0])):
            return True
        else:
            return False
    # end has_object_concept
        

    def get_other_object(self, object: Object):
        """
        Returns the Object for this SameObjectHyp which is not the
        one passed in. If the Object passed in is neither of this Hypothesis'
        Objects, returns None.
        """
        return (self.object_1 if not object == self.object_1 else
                self.object_2 if not object == self.object_2 else
                None)
    # end get_other_object

    def get_shared_object(self, hypothesis: Hypothesis):
        """
        Returns the Object in this SameObjectHyp that appears in the hypothesis
        passed in. If neither of this Hypothesis' objects appear in the hypothesis
        passed in, returns None.
        """
        return (self.object_1 if hypothesis.has_object(self.object_1) else
                self.object_2 if hypothesis.has_object(self.object_2) else
                None)
    # end get_shared_object

    def get_individual_score(self, p_set: ParameterSet):
        """
        Gets the score for accepting this hypothesis alone
        for a given parameter set.
        """
        # Add each similarity evidence's score.
        # VisualSimEv score.
        visual_sim_ev_score = self.visual_sim_ev.score
        # Apply the threshold.
        if visual_sim_ev_score < p_set.visual_sim_ev_thresh:
            visual_sim_ev_score -= p_set.visual_sim_ev_thresh
        # Apply the weight
        visual_sim_ev_score *= p_set.visual_sim_ev_weight

        # AttributeSimEv score
        attribute_sim_ev_score = self.attribute_sim_ev.score
        # Apply the threshold.
        if attribute_sim_ev_score < p_set.attribute_sim_ev_thresh:
            attribute_sim_ev_score -= p_set.attribute_sim_ev_thresh
        # Apply the weight.
        attribute_sim_ev_score *= p_set.attribute_sim_ev_weight

        individual_score = visual_sim_ev_score + attribute_sim_ev_score
        return individual_score
    # end get_individual_score

# end class SameObjectHyp

class CausalSequenceHyp(Hypothesis):
    """
    A Hypothesis that two Action Instances are in a causal sequence with one
    another. 

    More specifically, that the source_action leads to the target_action.

    If the Hypothesis is accepted, the two Actions would get a 'leads-to' edge
    pointing from the source action to the target action. Makes its own
    'leads-to' edge when instantiated.

    Evidence is the CausalPathEv from the source action to the target action.

    Attributes
    ----------
    source_action : Action
        The Action that comes before in the causal sequence.
    target_action : Action
        The Action that comes after in the causal sequence.
    edge : Edge
        The 'leads-to' edge from the source action to the target action. 
        Since this is the edge indicating which action leads to which other
        action, the edge will always point forward. This means that
        if the direction of this hypothesis is backwards, the edge's source will 
        be the target_action and its target will be the source_action.
    causal_path_evs : list[CausalPathEv]
        A list of Evidence, where each piece of Evidence consists of the causal 
        path from the source action to the target action.
    multi_causal_path_evs : List[MultiCausalPathEv]
        A list of Evidence, where each piece of Evidence consists of the
        multi-step causal paths from the source action to the target action.
    continuity_evs : list[ContinuityEv]
        A list of evidence, where each piece of Evidence consists of a 
        same object hyp between one of the source action's objects and one of the
        target action's objects.
    direction : CausalFlowDirection
        The direction that the original causal relationship points. If it
        is forwards, neutral, or NONE, then we assume that the source action 
        leads-to the target action.
        If it is backwards, then the target_action leads-to the source_action.
    """

    source_action: Action
    target_action: Action
    edge: Edge
    causal_path_evs: list[CausalPathEv]
    multi_causal_path_evs: list[MultiCausalPathEv]
    continuity_evs: list[ContinuityEv]
    direction: CausalFlowDirection

    # Affect curve scores per p-set id.
    affect_curve_scores: dict[int, float]

    def __init__(self, source_action: Action,
                 target_action: Action):
        name = (f'causal_h_{Hypothesis._next_id}_{source_action.name}_{target_action.name}')
        super().__init__(name)
        self.source_action = source_action
        self.target_action = target_action
        self.causal_path_evs = list()
        self.multi_causal_path_evs = list()
        self.continuity_evs = list()
        self.direction = CausalFlowDirection.NONE
        self.edge = Edge(source=source_action,
                         target=target_action,
                         relationship='leads-to',
                         weight=0,
                         hypothesized=True)
        self.affect_curve_scores = dict()
    # end __init__

    def __repr__(self):
        if self.direction is CausalFlowDirection.BACKWARD:
            return (f'{self.source_action}<-leads-to<-{self.target_action} ({self.edge.weight})')
        else:
            return (f'{self.source_action}->leads-to->{self.target_action} ({self.edge.weight})')
    # end __repr__

    def add_causal_path_ev(self, causal_path_ev: CausalPathEv):
        """
        Adds a piece of causal path evidence to this Hypothesis.
        """
        self.causal_path_evs.append(causal_path_ev)
        # Add the new evidence's score to the Edge's weight.
        self.edge.weight += causal_path_ev.score
        # Update the causal flow direction according to the direction of the
        # causal path evidence. 
        self._update_direction(causal_path_ev)

    # end add_causal_path_ev

    def add_multi_causal_path_ev(self, multi_causal_path_ev: MultiCausalPathEv):
        """
        Adds a piece of MultiCausalPathEvidence to this Hypothesis.
        """
        self.multi_causal_path_evs.append(multi_causal_path_ev)
        # Add the new evidence's score to the Edge's weight.
        self.edge.weight += multi_causal_path_ev.score
        # Update the causal flow direction according to the direction of the
        # causal path evidence. 
        self._update_direction(multi_causal_path_ev)
    # end add_multi_causal_path_ev

    def _update_direction(self, causal_path_ev: Union[CausalPathEv, MultiCausalPathEv]):
        """
        Update the direction of this hypothesis according to a piece of
        either CausalPathEv or MultiCausalPathEv.
        """
        # First, see if the causal path evidence's source is this hypothesis'
        # source. If not, it actually points from the target to the source and
        # its direction should be flipped.
        evidence_direction = causal_path_ev.direction
        if causal_path_ev.target_action == self.source_action:
            if evidence_direction == CausalFlowDirection.FORWARD:
                evidence_direction = CausalFlowDirection.BACKWARD
            elif evidence_direction == CausalFlowDirection.BACKWARD:
                evidence_direction = CausalFlowDirection.FORWARD
            # end elif
        # end if
                
        if self.direction == CausalFlowDirection.NONE:
            self.direction = evidence_direction
            # Adjust the edge if the direction is now backwards.
            if self.direction == CausalFlowDirection.BACKWARD:
                old_source = self.edge.source
                self.edge.source = self.edge.target
                self.edge.target = old_source
            # end if
        # end if
        elif not self.direction == evidence_direction:
            # Adjust the edge if the direction was backward and is now
            # becoming neutral.
            if self.direction == CausalFlowDirection.BACKWARD:
                old_source = self.edge.source
                self.edge.source = self.edge.target
                self.edge.target = old_source
            # end if
            self.direction = CausalFlowDirection.NEUTRAL
        # end elif
    # end _update_direction
            
    def add_continuity_ev(self, continuity_ev: ContinuityEv):
        """
        Adds a piece of continuity evidence to this Hypothesis.
        """
        self.continuity_evs.append(continuity_ev)
    # end add_continuity_ev

    def get_individual_score(self, p_set: ParameterSet):
        """
        Gets the score for accepting this hypothesis alone
        for a given parameter set.
        """

        # Add each causal path evidence's scores together.
        total_causal_path_score = 0
        for causal_path_ev in self.causal_path_evs:
            causal_path_ev_score = causal_path_ev.score
            ## Apply the threshold.
            #if causal_path_ev_score < p_set.causal_path_ev_thresh:
            #    causal_path_ev_score -= p_set.causal_path_ev_thresh
            ## Apply the weight.
            #causal_path_ev_score *= p_set.causal_path_ev_weight
            total_causal_path_score += causal_path_ev_score
        # end for
        for multi_causal_path_ev in self.multi_causal_path_evs:
            multi_causal_path_ev_score = multi_causal_path_ev.score
            ## Apply the threshold.
            #if multi_causal_path_ev_score < p_set.causal_path_ev_thresh:
            #    multi_causal_path_ev_score -= p_set.causal_path_ev_thresh
            ## Apply the weight.
            #multi_causal_path_ev_score *= p_set.causal_path_ev_weight
            total_causal_path_score += multi_causal_path_ev_score
        # end for

        # Apply the threshold.
        if total_causal_path_score < p_set.causal_path_ev_thresh:
            total_causal_path_score -= p_set.causal_path_ev_thresh
        # Apply the weight.
        total_causal_path_score *= p_set.causal_path_ev_weight

        if (self.id == 3):
            print('Teach leads-to hold')
        # See how much this causal sequence link obeys the affect curve.
        # Get the index of the image of the source action. 
        source_index = self.get_true_source_image().index
        target_index = self.get_true_target_image().index
        # Get the desired affect at each of these indices.
        source_affect = p_set.affect_curve[source_index]
        target_affect = p_set.affect_curve[target_index]
        # See what the desired affect change is from source image to
        # target image.
        desired_affect_change = target_affect - source_affect
        
        # Now see what the affect change between this system's source action
        # and target action are.
        source_action_affect = self.get_true_source_action().concepts[0].sentiment
        target_action_affect = self.get_true_target_action().concepts[0].sentiment
        action_affect_change = target_action_affect - source_action_affect

        correct_change = False
        reverse_change = False

        affect_curve_score = 0
        # 1. See if it matches the direction of change in affect. This gives it
        # a base score of 0.25.
        # This only applies if the direction of change is not 0.
        # If they're in the same direction, multiplying the changes together
        # results in a positive number. 
        if (not desired_affect_change == 0
            and (desired_affect_change * action_affect_change > 0)):
            correct_change = True
            affect_curve_score += 0.25
        # If they're in opposite directions, multiplying the changes together
        # results in a negative number. 
        elif (not desired_affect_change == 0
              and (desired_affect_change * action_affect_change < 0)):
            correct_change = False
        # end elif

        # 2. Increase score by some amount for each action whose sentiment 
        # matches the target affect if the affect change is in the right 
        # direction. This increases the score by 0.25 each. 
        if correct_change:
            if source_action_affect == source_affect:
                affect_curve_score += 0.25
            if target_action_affect == target_affect:
                affect_curve_score += 0.25

        # 3. If it matches the magnitude and the change is in the correct 
        # direction, increase score by 0.25. 
        if (correct_change and desired_affect_change == action_affect_change):
            affect_curve_score += 0.25

        # If the affect change is reversed, add a score component of -1.
        if (reverse_change):
            affect_curve_score = -1

        # Apply the threshold.
        if affect_curve_score < p_set.affect_curve_thresh:
            affect_curve_score -= p_set.affect_curve_thresh
        # Apply the weight.
        affect_curve_score *= p_set.affect_curve_weight

        # Store the result.
        self.affect_curve_scores[p_set.id] = affect_curve_score

        individual_score = total_causal_path_score + affect_curve_score

        return individual_score
    # end get_individual_score
        
    def get_true_source_action(self) -> Action:
        return self.edge.source
    
    def get_true_target_action(self) -> Action:
        return self.edge.target

    def get_true_source_image(self):
        return self.get_true_source_action().get_image()
    
    def get_true_target_image(self):
        return self.get_true_target_action().get_image()
    
# end CausalSequenceHyp
    
class HypothesisSet():
    """
    A set of hypotheses with a negative-numbered id.

    Attributes
    ----------
    id : int
        A unique integer identifier for this HypothesisSet.
        HypothesisSet IDs are always negative.
    hypotheses : dict[int, Hypothesis]
        The hypotheses in this set.
    is_all_or_ex : bool
        Whether or not this set is an all or exclusive set.
        If it is an all or exclusive set, then either all the members of the set 
        get accepted together or none of its members get accepted together.
        i.e. it is acceptable if:
            All members of the set are accepted.
            One member of the set is accepted.
            No members of the set are accepted.
    """

    id: int
    hypotheses: dict[int, Hypothesis]
    is_all_or_ex: bool

    # Class variable to make unique IDs when a new hypothesis set is made.
    _next_id = -1
    def __init__(self, 
                 hypotheses: list[Hypothesis],
                 is_all_or_ex: bool):
        self.id = HypothesisSet._next_id
        HypothesisSet._next_id -= 1
        self.hypotheses = {h.id: h for h in hypotheses}
        self.is_all_or_ex = is_all_or_ex
    # end __init__
        
    def get_hypothesis_list(self):
        return list(self.hypotheses.values())
    
    def contains_all(self, hyp_list: list[Hypothesis]) -> bool:
        """
        Returns whether this hypothesis set contains all of the hypotheses
        in a list.
        """
        for hyp in hyp_list:
            if not hyp.id in self.hypotheses:
                return False
        # end for
        return True
    # end contains_all
    
    def __contains__(self, item):
        """
        Checks whether this hypothesis set contains a hypothesis.

        Can pass either a hypothesis or its id.
        """
        # Resolve based on the item's type.
        if issubclass(type(item), Hypothesis):
            return True if item.id in self.hypotheses else False
        elif type(item) is int:
            return True if item in self.hypotheses else False
        else:
            return False
    # end __contains__
    
    def __len__(self):
        '''
        The length of a hypothesis set is the number of hypotheses in the set.
        '''
        return len(self.hypotheses)
    # end __len__
# end class HypothesisSet
        
class CausalHypChain(HypothesisSet):
    """
    An ordered chain of causal sequence hypotheses.
    
    Attributes
    ----------
    hyp_id_sequence : List[int]
        An list of the IDs of the hypotheses in this chain in the order that
        those hypotheses appear in the chain.
    """

    hyp_id_sequence: list[int]

    def __init__(self, hypotheses: list[CausalSequenceHyp]):
        super().__init__(hypotheses=hypotheses, is_all_or_ex=False)
        self.hyp_id_sequence = [h.id for h in hypotheses]
    # end  __init__
        
    def get_first_hyp(self):
        return self.hypotheses[self.hyp_id_sequence[0]]
    # end get_first_hyp
# end class CausalHypChain