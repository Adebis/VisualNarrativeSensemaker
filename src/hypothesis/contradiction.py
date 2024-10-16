from dataclasses import dataclass, field
from enum import Enum

from knowledge_graph.items import Object
from input_handling.scene_graph_data import Image
from hypothesis.hypothesis import (Hypothesis,
                                   CausalSequenceHyp,
                                   HypothesisSet,
                                   CausalHypChain)

class Constraint(Enum):
    """
    The types of Constraints that could cause a Contradiction.
    """
    REFERENTIAL = 0
# end class Constraint

@dataclass
class Contradiction:
    """
    A class representing a contradiction.

    Attributes
    ----------
    id: int
        A unique identifier for this contradiction.
    explanation : str
        A text explanation of the Contradiction and why it is occurring.
    """
    id : int
    explanation : str

    _next_id = 0
    def __init__(self, explanation: str):
        self.id = Contradiction._next_id
        Contradiction._next_id += 1
        self.explanation = explanation
    # end __init__
        
# end class Contradiction
    
@dataclass
class HypothesisCon(Contradiction):
    """
    A class representing a contradiction between two hypotheses.
    If one hypothesis in the contradiction is accepted, the other must be
    rejected.

    Attributes
    ----------
    hypothesis_1 : Hypothesis
        One of the Hypotheses.
    hypothesis_2 : Hypothesis
        The other Hypothesis.
    """
    hypothesis_1: Hypothesis
    hypothesis_2: Hypothesis

    def __init__(self, explanation: str, hypothesis_1: Hypothesis, 
                 hypothesis_2: Hypothesis):
        super().__init__(explanation)
        self.hypothesis_1 = hypothesis_1
        self.hypothesis_2 = hypothesis_2
    # end __init__
        
    def __contains__(self, item):
        if issubclass(type(item), Hypothesis):
            return (True if self.hypothesis_1 == item 
                    or self.hypothesis_2 == item
                    else False)
        else:
            return False
    # end __contains___

    def other_hypothesis(self, hypothesis: Hypothesis):
        return (self.hypothesis_2 if hypothesis == self.hypothesis_1
                else self.hypothesis_1 if hypothesis == self.hypothesis_2
                else None)
    # end other_hypothesis
# end class HypothesisCon

@dataclass  
class HypothesisSetCon(Contradiction):
    """
    A class represetning a contradiction between two sets of hypotheses.
    If one set of hypotheses is accepted in its entirety, at least one
    hypothesis in the other must be rejected.

    Attributes
    ----------
    hyp_set_1 : HypothesisSet
        One of the Hypothesis sets.
    hyp_set_2 : HypothesisSet
        The other Hypothesis set.
    """
    hyp_set_1: HypothesisSet
    hyp_set_2: HypothesisSet

    def __init__(self, explanation: str, hyp_set_1: HypothesisSet, 
                 hyp_set_2: HypothesisSet):
        super().__init__(explanation)
        self.hyp_set_1 = hyp_set_1
        self.hyp_set_2 = hyp_set_2
    # end __init__
        
    def __contains__(self, item):
        if issubclass(type(item), Hypothesis):
            return (True if item in self.hyp_set_1 or item in self.hyp_set_2
                    else False)
        elif issubclass(type(item), HypothesisSet):
            return (True if item == self.hyp_set_1 or item == self.hyp_set_2
                    else False)
        else:
            return False
    # end __contains__
        
    def get_hyp_set(self, hypothesis: Hypothesis):
        if hypothesis in self.hyp_set_1:
            return self.hyp_set_1
        elif hypothesis in self.hyp_set_2:
            return self.hyp_set_2
        else:
            return None
    # end get_hyp_set

    def other_hyp_set(self, item):
        # If item is a hypothesis, get the hypothesis set in this contradiction
        # which does NOT contain the hypothesis.
        if issubclass(type(item), Hypothesis):
            return (self.hyp_set_1 if item in self.hyp_set_2
                    else self.hyp_set_2 if item in self.hyp_set_1
                    else None)
        elif issubclass(type(item), HypothesisSet):
            return (self.hyp_set_1 if item == self.hyp_set_2
                    else self.hyp_set_2 if item == self.hyp_set_1
                    else None)
        else:
            return None
# end class HypothesisSetCon

@dataclass
class InImageTransCon(HypothesisCon):
    """
    Within Image Transitivity Contradiction
    
    A class representing a within-image transitivity contradiction between 
    Hypotheses.

    A within-image transitivity contradiction occurs when two Hypotheses assert 
    that one Object in one Image is equal to two different Objects in a second 
    Image.

    For example, if hypothesis 1 states that bike_1_1 in image 1 equals bike_2
    in image 2
    and hypothesis 2 states that bike_1_2 in image 1 equals bike_2 in image 2,
    these two hypotheses have an in-image transitivity contradiction with each 
    other. 

    Attributes
    ----------
    obj_1 : Object
        The Object that hypothesis_1 asserts is equal to shared_obj.
    obj_2 : Object
        The Object that hypothesis_2 asserts is equal to shared_obj.
    shared_obj : Object
        The Object that both obj_1 and obj_2 are asserted as equal to. 
    """
    obj_1 : Object
    obj_2 : Object
    shared_obj : Object

    def __init__(self, hypothesis_1: Hypothesis, hypothesis_2: Hypothesis,
                 explanation: str, obj_1: Object, obj_2: Object, 
                 shared_obj: Object):
        super().__init__(hypothesis_1=hypothesis_1,
                       hypothesis_2=hypothesis_2,
                       explanation=explanation)
        self.obj_1 = obj_1
        self.obj_2 = obj_2
        self.shared_obj = shared_obj
    # end __init__
# end class InImageTransCon

@dataclass
class TweenImageTransCon(HypothesisCon):
    """
    Between Image Transitivity Contradiction

    A between image transitivity contradiction occurs when two Hypotheses
    assert that one Object in one Image is equal to two different Objects in
    different Images and there is NOT a hypothesis asserting that those two
    different Objects are also equal to one another. 

    For example:
        hypothesis 1: bike 1 in Image 1 equals bike 3 in Image 3
        hypothesis 2: bike 2 in Image 2 equals bike 3 in Image 3
    If there is no hypothesis that bike 1 and bike 2 are also equal, this is
    a between-image transitivity contradiction. 

    Attributes:
    obj_1 : Object
        The Object that hypothesis_1 asserts is equal to shared_obj.
    obj_2 : Object
        The Object that hypothesis_2 asserts is equal to shared_obj.
    shared_obj : Object
        The Object that both obj_1 and obj_2 are asserted as equal to. 
    joining_hyp : Hypothesis
        The hypothesis that would repair the transitivity contradiction by
        asserting that obj_1 and obj_2 are equal, if any. If this Hypothesis is
        rejected or does not exist, the other two Hypotheses contradict each 
        other. 
    hyp_set_id : int
        The ID of the hypothesis id set corresponding to hyp_1, hyp_2,
        and the joining hypothesis in this contradiction.
    """
    obj_1 : Object
    obj_2 : Object
    shared_obj : Object
    joining_hyp : Hypothesis
    hyp_set_id : int

    def __init__(self, explanation: str, hypothesis_1: Hypothesis, 
                 hypothesis_2: Hypothesis, obj_1: Object, obj_2: Object, 
                 shared_obj: Object, joining_hyp: Hypothesis, hyp_set_id: int):
        super().__init__(explanation=explanation,
                         hypothesis_1=hypothesis_1,
                         hypothesis_2=hypothesis_2)
        self.obj_1 = obj_1
        self.obj_2 = obj_2
        self.shared_obj = shared_obj
        self.joining_hyp = joining_hyp
        self.hyp_set_id = hyp_set_id
    # end __init__
# end class TweenImageTransCon

@dataclass
class CausalCycleCon(Contradiction):
    '''
    Causal Cycle Contradiction

    A causal cycle contradiction occurs when a sequence of causal sequence
    hypotheses asserts that their actions start and end at the same image.

    A causal cycle contradiction is currently only between either two
    hypotheses or three hypotheses. 

    If it is between two hypotheses, the two hypotheses cannot be accepted
    alongside each other, as they would form a cycle. 
    
    If it is between three hypotheses, then the CausalCycleCon will have three 
    subsets of two hypotheses each. Each subset cannot be accepted alongside
    the last hypothesis not in the subset, as they would form a cycle. 

    Attributes:
        image : Image
            The image that this causal cycle contradiction starts and ends at.
        causal_chain : CausalHypChain
            The CausalHypChain that causes this cycle.
        subsets : list[HypothesisSet] = field(init=False)
            Subsets of the causal hyp chain. Made after initialization.
    '''

    image: Image
    causal_chain: CausalHypChain
    subsets: list[HypothesisSet] = field(init=False)

    def __init__(self,
                 explanation: str,
                 image: Image,
                 causal_chain: CausalHypChain):
        super().__init__(explanation=explanation)
        self.image = image
        self.causal_chain = causal_chain
        self.subsets = list()
        if len(self.causal_chain) > 2:
            # Make subsets out of each pair of hypotheses in the causal chain.
            hyps = self.causal_chain.get_hypothesis_list()
            for i in range(len(hyps) - 1):
                hyp_1 = hyps[i]
                for j in range(i, len(hyps)):
                    hyp_2 = hyps[j]
                    hyp_set = HypothesisSet(hypotheses=[hyp_1, hyp_2])
                    self.subsets.append(hyp_set)
                # end for j
            # end for i
        # end if
    # end __init__

    def get_subset_exclusion_pairs(self) -> list[tuple[HypothesisSet, CausalSequenceHyp]]:
        '''
        Gets all of the subsets in this chain paired with the hypothesis
        that they exclude.
        '''
        pairs = list()
        for subset in self.subsets:
            # Find the hypothesis not in this subset.
            for h in self.causal_chain:
                if h not in subset:
                    pair = (subset, h)
                    pairs.append(pair)
                break
            # end for
        # end for
        return pairs
    # end get_subset_exclusion_pairs
# end class CausalCycleCon

@dataclass
class CausalHypFlowCon(HypothesisCon):
    """
    Causal Hyp Flow Contradiction

    A causal hyp flow contradiction occurs when two causal sequence hypotheses
    assert that the actions in their images flow in the opposite directions.

    Each causal hyp flow con starts and ends at an image. The start image of
    one of the causal hyps in this contradiction is the end image of the other
    causal hyp and vice-versa.

    Attributes:
    image_1 : Image
        The image that hypothesis_1 starts at and hypothesis_2 ends at.
    image_2 : Image
        The image that hypothesis_2 starts at and hypothesis_1 ends at.
    """

    image_1: Image
    image_2: Image

    def __init__(self,
                 explanation: str,
                 hypothesis_1: CausalSequenceHyp,
                 hypothesis_2: CausalSequenceHyp,
                 image_1: Image,
                 image_2: Image):
        super().__init__(explanation=explanation,
                         hypothesis_1=hypothesis_1,
                         hypothesis_2=hypothesis_2)
        self.image_1 = image_1
        self.image_2 = image_2
    # end __init__

# end CausalHypFlowCon
        
@dataclass
class CausalChainFlowCon(HypothesisSetCon):
    """
    Causal Chain Flow Contradiction

    A causal chain flow contradiction occurs when two chains of causal sequence 
    hypotheses assert that the actions in their images flow in the opposite 
    directions.

    Each causal chain starts and ends at an image. The start image of one of
    the causal chains in this contradiction is the end image of the other
    causal chain and vice-versa. 

    Attributes:
    image_1 : Image
        The image that causal_chain_1 starts at and causal_chain_2 ends at.
    image_2 : Image
        The image that causal_chain_1 ends at and causal_chain_2 starts at.
    """

    image_1 : Image
    image_2 : Image

    def __init__(self,
                 explanation: str, 
                 causal_chain_1: CausalHypChain, 
                 causal_chain_2: CausalHypChain, 
                 image_1: Image, 
                 image_2: Image):
        super().__init__(explanation=explanation,
                         hyp_set_1=causal_chain_1,
                         hyp_set_2=causal_chain_2)
        self.image_1 = image_1
        self.image_2 = image_2
    # end __init__
        
# end class CausalChainFlowCon