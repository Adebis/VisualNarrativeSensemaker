from dataclasses import dataclass, field
from enum import Enum

from hypothesis.hypothesis import Hypothesis

class Constraint(Enum):
    """
    The types of Constraints that could cause a Contradiction.
    """
    REFERENTIAL = 0
# end class Constraint

@dataclass
class Contradiction:
    """
    A class representing a contradiction between two hypotheses.

    Attributes
    ----------
    hypothesis_1 : Hypothesis
        One of the Hypotheses.
    hypothesis_2 : Hypothesis
        The other Hypothesis.
    explanation : str
        A text explanation of the Contradiction and why it is occurring.
    """
    hypothesis_1 : Hypothesis
    hypothesis_2 : Hypothesis
    explanation : str
# end class Contradiction

@dataclass
class TransitiveReference(Contradiction):
    """
    A class representing a transitive reference contradiction between Hypotheses.

    Transitive reference contradictions occur when two Hypotheses assert that 
    one Object in one Image is equal to two different Objects in a second image.
    """