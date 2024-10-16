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
    visual_sim_ev_weight : float
        A weight multiplied against all VisualSimEv scores.
    visual_sim_ev_thresh : float
        A minimum threshold below which VisualSimEv scores are negative.
    attribute_sim_ev_weight : float
        A weight multiplied against all AttributeSimEv scores.
    attribute_sim_ev_thresh : float
        A minimum threshold below which AttributeSimEv scores are negative.
    causal_path_ev_weight : float
        A weight multiplied against all CausalPathEv scores.
    causal_path_ev_thresh : float
        A minimum threshold below which CausalPathEv scores are negative.
    continuity_ev_weight : float
        A weight multiplied against all ContinuityEv scores.
    continuity_ev_thresh : float
        A minimum threshold below which ContinuityEv scores are negative.
    """
    id: int = field(init=False)
    name: str
    visual_sim_ev_weight: float
    visual_sim_ev_thresh: float
    attribute_sim_ev_weight: float
    attribute_sim_ev_thresh: float
    causal_path_ev_weight: float
    causal_path_ev_thresh: float
    continuity_ev_weight: float
    continuity_ev_thresh: float
    density_weight: float
    affect_curve: list[int]
    affect_curve_weight: float
    affect_curve_thresh: float

    # Class variable to ensure that each parameter set gets a unique id.
    _next_id = 0
    def __post_init__(self):
        # Assign the id and increment the class' id counter.
        self.id = ParameterSet._next_id
        ParameterSet._next_id += 1
    # end __post_init__

    def set_id(self, id: int):
        self.id = id
    # end set_id