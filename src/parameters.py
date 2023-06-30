from dataclasses import dataclass, field

@dataclass
class ParameterSet():
    """
    A set of parameters for sensemaking.

    Attributes
    ----------
    id : int
        A unique integer identifier. 
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
    id: int = field(init=False)
    name: str
    no_relationship_penalty: float
    relationship_score_minimum: float
    relationship_score_weight: float
    continuity_penalty: float

    # Class variable to ensure that each parameter set gets a unique id.
    _next_id = 0
    def __post_init__(self):
        # Assign the id and increment the class' id counter.
        self.id = ParameterSet._next_id
        ParameterSet._next_id += 1
    # end __post_init__