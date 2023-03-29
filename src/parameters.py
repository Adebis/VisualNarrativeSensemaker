from dataclasses import dataclass, field

@dataclass
class ParameterSet():
    """
    A set of parameters for sensemaking.

    Attributes
    ----------
    name : str
        A human readable name for this set of parameters.
    no_relationship_penalty : float
        The base penalty for not having an Edge between two Instances in the 
        same scene.

        The value of this penalty should be set to a negative value for it to be
        a penalty.
    relationship_score_minimum : float
        All relationship scores that fall below this minimum are penalized. All
        relationship scores that exceed this minium are rewarded.
    relationship_score_weight : float
        A weight multiplied against all relationship scores after they have
        been compared to the minimum.
    continuity_penalty : float
        The base penalty for all Instances that aren't accounted for in other
        scenes.

        The value of this penalty should be set to a negative value for it to be
        a penalty.
    """
    name: str
    no_relationship_penalty: float
    relationship_score_minimum: float
    relationship_score_weight: float
    continuity_penalty: float