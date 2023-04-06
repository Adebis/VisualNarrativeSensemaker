from abc import abstractmethod

import cv2
from image_similarity_measures import quality_metrics

from knowledge_graph.items import (Concept, Instance, Object, Action, Edge,
                                   EdgeRelationship)

class Evidence:
    """
    Base class for a piece of evidence supporting (or refuting) a Hypothesis.

    Attributes
    ----------
    id : int
        A unique int identifier for this evidence.
    score : int
        The Evidence's score. For use in MOOP solving.
    """
    # Class variable for making unique ids whenever a new piece of evidence is 
    # made.
    _next_id = 0

    def __init__(self):
        self.id = Evidence._next_id
        Evidence._next_id += 1
        self.score = 0
    # end __init__
# end Evidence

class ConceptEdgeEv(Evidence):
    """
    Evidence consisting of the Edge between two Concepts.

    Attributes
    ----------
    edge : Edge
        The edge from one Concept to the other.
    """
    edge: Edge

    def __init__(self, edge: Edge):
        super().__init__()
        self.edge = edge
        # The score of a piece of ConceptEdgeEv is the weight of the Edge
        # between the two Concepts.
        self.score = edge.weight
    # end __init__

    def __str__(self):
        return (f'ConceptEdgeEv: {self.edge.source} related to ' + 
                f'{self.edge.target} through edge ' +
                f'{self.edge}. Score: {self.score}')
    # end __str__

# end class ConceptEdgeEv

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

class VisualSimilarityEvidence(Evidence):
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
        super().__init__()
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
        return (f'vsim {self.object_1}|{self.object_2}: {self.score}')
    # end __repr__
# end class VisualSimilarityEvidence

class AttributeSimilarityEvidence(Evidence):
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
        super().__init__()
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
        return (f'asim {self.object_1}|{self.object_2}: {self.score}')
    # end __repr__

# end class AttributeSimilarityEvidence

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
        Initializes a ConceptEdgeHypothesis with the source and target Instances
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

    def has_instance(self, instance: Instance):
        """
        Whether or not this Hypothesis has an Instance as either its source
        instance or its target instance.
        """
        return (True if (self.source_instance == instance or 
                         self.target_instance == instance) else False)
    # end has_instance

    def get_other_instance(self, instance: Instance):
        """
        Gets the Instance in this scene which is not the one passed in. Returns
        None if neither Instance is the one passed in.
        """
        return (self.source_instance if self.target_instance == instance
                else self.target_instance if self.source_instance == instance
                else None)
    # end get_other_instance
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
        The hypothesized Object.
    concept_edge_hyps : list[Hypothesis]
        The hypothesized Concept Edges from the hypothesized Object's Concept
        to each other Instance's Concept in the same scene.
    """
    obj: Object
    concept_edge_hyps: list[Hypothesis]

    def __init__(self, obj: Object, concept_edge_hyps: list[Hypothesis]):
        """
        Initializes a NewObjectHyp with the hypothetical Object and
        the ConceptEdgeHypotheses between it and the other Objects in its
        scene. 

        Makes its own OtherHypEv out of the ConceptEdgeHypotheses
        passed in, so no Evidence needs to be provided.

        Also sets itself as a premise for every ConceptEdgeHypothesis provided
        to it. 
        """
        name = (f'offobj_h_{Hypothesis._next_id}_{obj.name}')
        # Make OtherHypEv for each concept edge hypothesis passed
        # in.
        evidence = [OtherHypEv(h) for h in concept_edge_hyps]
        super().__init__(name=name, evidence=evidence)
        # Make this Hypothesis a premise of every ConceptEdgeHypothesis passed
        # in, since they wouldn't exist without this Hypothesis' hypothetical
        # Instance.
        for hypothesis in concept_edge_hyps:
            hypothesis.add_premise(premise=self)
        self.obj = obj
        self.concept_edge_hyps = concept_edge_hyps

        self.calculate_score()
    # end __init__

    def __repr__(self):
        return (f'{self.name}. ' + 
                f'Concept edges: {len(self.concept_edge_hyps)}. ' + 
                f'Score: {self.score}')
    # end __repr__

    def calculate_score(self):
        score = 0
        for evidence in self.evidence:
            score += evidence.score
        self.score = score
        return score
    # end calculate_score
# end NewObjectHyp

class SameObjectHyp(Hypothesis):
    """
    A Hypothesis that two Object Instances represent the same Object. 

    If the Hypothesis is accepted, the two Objects would get a 'duplicate-of'
    Edge between them. 

    Evidence is the VisualSimilarityEvidence between the two Objects'
    appearances and the AttributeSimilarityEvidence between the two Objects'
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
    """

    def __init__(self, object_1: Object, object_2: Object):
        """
        Initializes with the two Objects that are being hypothesized as
        duplicates of one another. 

        Builds its own VisualSimilarityEvidence and AttributeSimilarityEvidence.

        Also makes the duplicate-of Edge that would be applied to both Objects.
        """
        self.object_1 = object_1
        self.object_2 = object_2
        name = (f'dup_h_{Hypothesis._next_id}_{object_1.name}_{object_2.name}')
        # Get the visual similarity evidence between the Objects.
        vs_evidence = VisualSimilarityEvidence(object_1, object_2)
        # Get the attribute similarity between the Objects.
        as_evidence = AttributeSimilarityEvidence(object_1, object_2)
        # Use them as the Evidence for this Hypothesis.
        super().__init__(name, [vs_evidence, as_evidence])
        self.calculate_score()
        # Make the duplicate-of edge between the two Objects.
        self.edge = Edge(source=self.object_1, target=self.object_2,
                         relationship=str(EdgeRelationship.DUPLICATE_OF), 
                         weight=self.score,
                         hypothesized=True)
    # end __init__

    def __repr__(self):
        return (f'{self.name}. ' + 
                f'Evidence: {self.evidence[0]}, {self.evidence[1]} ' + 
                f'Score: {self.score}')
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

    def calculate_score(self):
        score = 0
        for evidence in self.evidence:
            score += evidence.score
        self.score = score
        return score
    # end calculate_score

# end class SameObjectHyp

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
    """

    def __init__(self, object_: Object, 
                 new_object_hyp: NewObjectHyp,
                 object_dulpicate_hypothesis: SameObjectHyp):
        """
        Initializes with the existing Object that's hypothesized to persist,
        its NewObjectHyp, and its SameObjectHyp.

        Builds its own OtherHypEv.
        """
        self.object_ = object_
        self.new_object_hyp = new_object_hyp
        self.object_dulpicate_hypothesis = object_dulpicate_hypothesis
        evidence = list()
        evidence.append(
            OtherHypEv(new_object_hyp))
        evidence.append(
            OtherHypEv(object_dulpicate_hypothesis))
        name = (f'objpersist_h_{Hypothesis._next_id}_{object_.name}')
        super().__init__(name=name, evidence=evidence)
        # Adds the two Hypotheses used as evidence as premises to this
        # hypothesis.
        self.add_premise(new_object_hyp)
        self.add_premise(object_dulpicate_hypothesis)
    # end __init__

    def calculate_score(self):
        score = 0
        for evidence in self.evidence:
            score += evidence.score
        self.score = score
        return score
    # end calculate_score
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

