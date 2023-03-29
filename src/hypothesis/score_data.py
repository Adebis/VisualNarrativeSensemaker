from dataclasses import dataclass, field

from knowledge_graph.items import (Instance, Edge)

@dataclass
class RelationshipScore:
    """
    The information about the score of a relationship between two Instances.

    Attributes
    ----------
    source : Instance
        The source Instance.
    target : Instance
        The target Instance.
    edge : Edge
        The Edge between the two Instances. Points away from the source and
        towards the target.
    score : float
        The score the Edge was given.
    """