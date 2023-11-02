from abc import abstractmethod

import cv2
from image_similarity_measures import quality_metrics

import constants as const

from knowledge_graph.items import (Concept, Instance, Object, Action, Edge,
                                   EdgeRelationship)
from knowledge_graph.path import (Path, Step)

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

class ConceptEdgeEv(Evidence):
    """
    Evidence consisting of the Edge between the Concepts of two Instances.

    Attributes
    ----------
    edge : Edge
        The edge from one Instance's Concept to the other.
    source_instance : Instance
        The source Instance. The edge is from the source_instance's Concept
        to the target_instance's Concept.
    target_instance : Instance
        The target Instance.
    """
    edge: Edge
    source_instance: Instance
    target_instance: Instance

    def __init__(self, edge: Edge, 
                 source_instance: Instance,
                 target_instance: Instance,
                 premise_hyp_ids: list[int]=list()):
        super().__init__(premise_hyp_ids=premise_hyp_ids)
        self.edge = edge
        # The score of a piece of ConceptEdgeEv is the weight of the Edge
        # between the two Concepts.
        self.score = edge.weight
        self.source_instance = source_instance
        self.target_instance = target_instance
    # end __init__

    def __str__(self):
        return (f'ConceptEdgeEv: {self.source_instance} related to ' + 
                f'{self.target_instance} through edge ' +
                f'{self.edge}. Score: {self.score}')
    # end __str__
# end class ConceptEdgeEv

class UnrelatedEv(Evidence):
    """
    Evidence consisting of the fact that one Instance has no relationship
    to another Instance.

    Attributes
    ----------
    source_instance : Instance
        The source Instance.
    target_instance : Instance
        The target Instance.
    """
    source_instance: Instance
    target_instance: Instance

    def __init__(self,
                 source_instance: Instance,
                 target_instance: Instance,
                 score: int,
                 premise_hyp_ids: list[int]=list()):
        super().__init__(premise_hyp_ids=premise_hyp_ids)
        self.source_instance = source_instance
        self.target_instance = target_instance
        self.score = score
    # end __init__

    def __str__(self):
        return (f'UnrelatedEv: {self.source_instance} not related to ' + 
                f'{self.target_instance}. Score: {self.score}')
    
# end class UnrelatedEv

class OtherHypEv(Evidence):
    """
    Evidence consisting of another Hypothesis.

    Attributes
    ----------
    hypothesis : Hypothesis
        The Hypothesis serving as Evidence.
    """
    def __init__(self, hypothesis):
        super().__init__()
        self.hypothesis = hypothesis
        self.score = 0
    # end __init__

    def __repr__(self):
        return (f'OtherHypEv: {self.hypothesis}')
    # end __repr__
# end class OtherHypEv

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
        # Calculate the visual similarity between these two Objects' appearances
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
            appearance_1 = cv2.resize(appearance_1, new_size)
            appearance_2 = cv2.resize(appearance_2, new_size)
            # Convert both appearances to grayscale.
            #appearance_1 = cv2.cvtColor(appearance_1, cv2.COLOR_GR)
            #appearance_2 = cv2.cvtColor(appearance_2, cv2.COLOR_BGR2GRAY)
            # Get the similarity between the two image regions.
            # Returns a float.
            # RMSE gives us the difference, so we have to subtract it from 1.
            # FSIM gives us a similarity, so we don't subtract it from 1.
            # SSIM gives us a similarity. Closer to 1 is more similar.
            similarity = quality_metrics.ssim(appearance_1, appearance_2)
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
    """

    source_action: Action
    target_action: Action
    source_concept: Concept
    target_concept: Concept
    concept_path: Path

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
        
        # Calculate the score based on the average score of every edge in
        # the path.
        # The number of edges in the path is one less than the length of
        # the path.
        total_score = sum([step.previous_edge.weight for step in self.concept_path.steps
                           if step.previous_edge is not None])
        self.score = total_score / (len(self.concept_path.steps) - 1)
    # end __init__

# end CausalPathEv

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

class ConceptEdgeHyp(Hypothesis):
    """
    A Hypothesis that a relationship between two Instances' Concepts is a
    real relationship between those Instances. 
    
    If the Hypothesis is accepted, the two Instances would get the Concept Edge
    between them. 

    Evidence for the Hypothesis is the ConceptEdgeEv between the two
    Instances' Concepts.

    Attributes
    ----------
    source_instance : Instance
        One of the Instances. The source of the Edge is one of the Concepts of 
        this Instance.
    target_instance : Instance
        The other Instance. The target of the Edge is one of the Concepts of 
        this Instance.
    edge : Edge
        The Edge from the source Instance's Concept to the target Instance's 
        Concept.
    concept_edge_ev : ConceptEdgeEv
        The evidence consisting of the concept edge between the source
        instance's concept and the target instance's concept.
    """
    source_instance: Instance
    target_instance: Instance
    edge: Edge
    concept_edge_ev: ConceptEdgeEv

    def __init__(self, source_instance: Instance, target_instance: Instance, 
                 edge: Edge):
        """
        Initializes a ConceptEdgeHyp with the source and target Instances
        it's about and the Edge between the Instance's Concepts.

        Makes its own ConceptEdgeEv out of the Edge that's passed in, so 
        no evidence needs to be provided.
        """
        # Name this hypothesis after the instances it's hypothesizing an edge
        # between and its id.
        name = (f'conceptedge_h_{Hypothesis._next_id}_{source_instance.name}_' + 
                f'{target_instance.name}')
        super().__init__(name=name)
        
        self.source_instance = source_instance
        self.target_instance = target_instance
        self.edge = edge
        # Make evidence out of the edge passed in.
        self.concept_edge_ev = ConceptEdgeEv(edge)
    # end __init__

    def __repr__(self):
        return (f'ConceptEdge h_{self.id} {self.source_instance}->{self.edge.relationship}'+
                f'->{self.target_instance}. Score: {self.score}')
    # end __str__

    def get_individual_score(self):
        """
        Gets the score for accepting this hypothesis alone.
        """
        individual_score = self.concept_edge_ev.score
        return individual_score
    # end get_individual_score

# end class ConceptEdgeHypothesis

class NewObjectHyp(Hypothesis):
    """
    A Hypothesis that an Object exists which was not observed in a scene graph.

    If the Hypothesis is accepted, the hypothetical Object would be added to
    the KnowledgeGraph.

    Evidence for this Hypothesis is the OtherHypEv for a series of 
    ConceptEdgeHypotheses, each hypothesizing an Edge between the hypothetical 
    Object's Concept and another Object's Concept in the same scene.

    Attributes
    ----------
    obj : Object
        The hypothesized new Object.
    source_object : Object
        The Object that led to this new Object being hypothesized.

        Currently, new objects are only hypothesized as copies of existing
        objects from other scenes. source_object is the existing object that
        this hypothesis' new object is a copy of.

        Optional. 
    concept_edge_evs : list[ConceptEdgeEv]
        The ConceptEdgeEv supporting the Hypothesis that this new Object belongs
        in its scene.
    unrelated_evs : list[UnrelatedEv]
        The UnrelatedEv refuting the Hypothesis that this new Object belongs
        in its scene.
    """
    obj: Object
    source_object: Object
    concept_edge_evs: list[ConceptEdgeEv]
    unrelated_evs: list[UnrelatedEv]

    def __init__(self, obj: Object, source_object: Object):
        """
        Initializes a NewObjectHyp with the hypothetical Object and
        the source Object it's a copy of.
        """
        name = (f'newobj_h_{Hypothesis._next_id}_{obj.name}')
        super().__init__(name=name)

        self.obj = obj
        self.source_object = source_object
        self.concept_edge_evs = list()
        self.unrelated_evs = list()
    # end __init__

    def __repr__(self):
        return (f'{self.name}. ')
    # end __repr__

    def get_individual_score(self):
        """
        Gets the score for accepting this hypothesis alone.
        """
        individual_score = 0
        return individual_score
    # end get_individual_score

    def add_concept_edge_ev(self, concept_edge_ev: ConceptEdgeEv):
        self.concept_edge_evs.append(concept_edge_ev)
    # end add_concept_edge_evs
    
    def add_unrelated_ev(self, unrelated_ev: UnrelatedEv):
        self.unrelated_evs.append(unrelated_ev)
    # end add_unrelated_evs
    # end add_unrelated_evs
# end NewObjectHyp

class NewActionHyp(Hypothesis):
    """
    A Hypothesis that an Action exists which was not observed in a scene graph.

    If the Hypothesis is accepted, the hypothetical Action would be added to
    the KnowledgeGraph.

    Evidence for this Hypothesis is the OtherHypEv for a series of 
    ConceptEdgeHypotheses, each hypothesizing an Edge between the hypothetical 
    Action's Concept and another Instance's Concept in the same scene.

    Attributes
    ----------
    action : Action
        The hypothesized Object.
    source_action : Action
        The Action that led to this new Action being hypothesized.

        Currently, new actions are only hypothesized from causally related actions 
        of existing actions from other scenes. source_action is the existing action 
        that this hypothesis' new action is causally related to.
    source_causal_edge : Edge
        The causal edge between one of the source action's Concepts and one of the
        new action's Concepts that led to the new action being hypothesized.
    concept_edge_evs : list[ConceptEdgeEv]
        The ConceptEdgeEv supporting the Hypothesis that this new Action belongs
        in its scene.
    unrelated_ev : list[UnrelatedEv]
        The UnrelatedEv refuting the Hypothesis that this new Action belongs
        in its scene.
    """
    action: Action
    source_action: Action
    source_causal_edge: Edge
    concept_edge_evs: list[ConceptEdgeEv]
    unrelated_evs: list[UnrelatedEv]

    def __init__(self, action: Action, 
                 source_action: Action, 
                 source_causal_edge: Edge):
        """
        Initializes a NewActionHyp with the hypothetical Action and
        the causally related existing Action it's sourced from. 
        """
        name = (f'newact_h_{Hypothesis._next_id}_{action.name}')
        super().__init__(name=name)
        self.action = action
        self.source_action = source_action
        self.source_causal_edge = source_causal_edge
        self.concept_edge_evs = list()
        self.unrelated_evs = list()
    # end __init__

    def __repr__(self):
        return (f'{self.name}. ')
    # end __repr__

    def get_individual_score(self):
        """
        Gets the score for accepting this hypothesis alone.
        """
        individual_score = 0
        return individual_score
    # end get_individual_score

    def add_concept_edge_ev(self, concept_edge_ev: ConceptEdgeEv):
        self.concept_edge_evs.append(concept_edge_ev)
    # end add_concept_edge_evs
    
    def add_unrelated_ev(self, unrelated_ev: UnrelatedEv):
        self.unrelated_evs.append(unrelated_ev)
    # end add_unrelated_evs
# end NewActionHyp

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
        self.edge = Edge(source=self.object_1, target=self.object_2,
                         relationship=str(EdgeRelationship.DUPLICATE_OF), 
                         weight=self.get_individual_score(),
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

    def get_individual_score(self):
        """
        Gets the score for accepting this hypothesis alone.
        """
        # Add each similarity evidence's score.
        individual_score = self.visual_sim_ev.score
        individual_score += self.attribute_sim_ev.score
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
    causal_path_ev : list[CausalPathEv]
        A list of Evidence, where each piece of Evidence consists of the causal 
        path from the source action to the target action.
    """

    source_action: Action
    target_action: Action
    edge: Edge
    causal_path_evs: list[CausalPathEv]

    def __init__(self, source_action: Action,
                 target_action: Action):
        name = (f'causal_h_{Hypothesis._next_id}_{source_action.name}_{target_action.name}')
        super().__init__(name)
        self.source_action = source_action
        self.target_action = target_action
        self.causal_path_evs = list()
        self.edge = Edge(source=source_action,
                         target=target_action,
                         relationship='leads-to',
                         weight=0,
                         hypothesized=True)
    # end __init__

    def __repr__(self):
        return (f'{self.source_action}->leads-to->{self.target_action}')
    # end __repr__

    def add_evidence(self, causal_path_ev: CausalPathEv):
        """
        Adds a piece of evidence to this Hypothesis.
        """
        self.causal_path_evs.append(causal_path_ev)
        # Add the new evidence's score to the Edge's weight.
        self.edge.weight += causal_path_ev.score
    # end add_evidence

    def get_individual_score(self):
        """
        Gets the score for accepting this hypothesis alone.
        """
        # Add each causal path evidence's scores together.
        individual_score = 0
        for causal_path_ev in self.causal_path_evs:
            individual_score += causal_path_ev.score
        return individual_score
    # end get_individual_score
    
# end CausalSequenceHyp






class PersistObjectHyp(Hypothesis):
    """
    A hypothesis that an Object in one image persists into another image
    as an off-screen Object. 

    Evidence is a NewObjectHyp for an offscreen Object in the
    other image that is an exact copy of the persisting Object and an
    SameObjectHyp between the persisting Object and its offscreen
    copy in the other image.

    Attributes
    ----------
    object_ : Object
        The existing Object that's hypothesized to persist into another image.
    new_object_hyp : NewObjectHyp
        The hypothesis hypothesizing a copy of the persisting object exists in 
        another image.
    same_object_hyp : SameObjectHyp
        The hypothesis hypothesizing that the copy of the persisting object is
        its duplicate. 
    new_object_hyp_ev : OtherHypEv
        Evidence consisting of a new object hypothesis hypothesizing that a copy 
        of the persisting object exists in another image.
    same_object_hyp_ev : OtherHypEv
        Evidence consisting of a same object hypothesis hypothesizing that the
        copy of the persisting object in the other image is the same as the
        original object it's a copy of. 
    """

    def __init__(self, object_: Object, 
                 new_object_hyp: NewObjectHyp,
                 same_object_hyp: SameObjectHyp):
        """
        Initializes with the existing Object that's hypothesized to persist,
        its NewObjectHyp, and its SameObjectHyp.

        Builds its own OtherHypEv.
        """
        name = (f'objpersist_h_{Hypothesis._next_id}_{object_.name}')
        super().__init__(name=name)
        self.object_ = object_
        self.new_object_hyp = new_object_hyp
        self.new_object_hyp_ev = OtherHypEv(new_object_hyp)
        self.same_object_hyp = same_object_hyp
        self.same_object_hyp_ev = OtherHypEv(same_object_hyp)
        # Adds the two Hypotheses used as evidence as premises to this
        # hypothesis.
        self.add_premise(new_object_hyp)
        self.add_premise(same_object_hyp)
    # end __init__

    def get_individual_score(self):
        """
        Gets the score for accepting this hypothesis alone.
        """
        individual_score = 0
        return individual_score
    # end get_individual_score

# end PersistObjectHyp




class ActionHypothesis(Hypothesis):
    """
    A Hypothesis that an Action is occuring that hasn't been directly observed.

    If the Hypothesis is accepted, the Action in question would be added to
    the knowledge graph. 

    Attributes
    ----------
    action : Action
        The hypothesized Action.
    """
    def __init__(self, action: Action, evidence: list[Evidence]):
        # Name this hypothesis after the action it's hypothesizing and its id.
        name = (f'h_{action.label}_{Hypothesis._next_id}')
        super().__init__(name=name, 
                         evidence=evidence)
        self.action = action
        self.calculate_score()
    # end __init__

    def __repr__(self):
        return (f'{self.name}')
    # end __repr__
    
    def calculate_score(self):
        """
        Calculates the score for this ActionHypothesis. Score is based on:

        The total weight of the Edges leading from the hypothesized Action's
        Concept to the Concepts of existing Instances.
        """
        score = 0
        
        for evidence in self.evidence:
            score += evidence.score
        # end for

        self.score = score
    # end calculate_score
# end ActionHypothesis

