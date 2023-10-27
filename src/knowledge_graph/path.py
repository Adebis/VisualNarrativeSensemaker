

from knowledge_graph.items import (Node, Concept, Instance, Object, Action, 
                                   Edge)

class Step:
    """
    A single Step in a Path.

    A Step consists of a Node, the Edge leading to the previous Step,
    and the Edge leading to the next Step. 

    ...

    Attributes
    ----------
    id : int
        Unique int identifier for this Step.
    node : Node
        The Node at this step of the path.
    next_step : Step
        The next Step of the path.
    next_edge : Edge
        The Edge between this step's Node and the next Step's Node. This edge may point
        either way, e.g. the source_node of the Edge may be this step's Node
        or the next Step's Node.
    previous_step : Step
        The Node at the previous step of the path.
    previous_edge : Edge
        The Edge between this step's Node and the previous step's Node. This edge may point
        either way, e.g. the source_node of the Edge may be this step's Node
        or the previous Step's Node.
    
    """

    id: int
    node: Node
    next_edge: Edge
    previous_edge: Edge

    # Class variable to make unique IDs when a new Step is made.
    _next_id = 0
    def __init__(self, node):
        self.id = Step._next_id
        Step._next_id += 1
        self.node = node
        self.next_step = None
        self.next_edge = None
        self.previous_step = None
        self.previous_edge = None
    # end __init__

    def set_next_step(self, next_step, next_edge: Edge):
        """
        Sets the next Step and the edge to the next step's node.
        """
        self.next_step = next_step
        self.next_edge = next_edge
    # end set_next_step

    def set_previous_step(self, previous_step, previous_edge: Edge):
        """
        Sets the previous Step and the edge to the previous step's node.
        """
        self.previous_step = previous_step
        self.previous_edge = previous_edge
    # end set_previous_step

# end Step

class Path:
    """
    A sequence of Nodes and the Edges leading between them. 

    A path is made up of a sequence of Steps, with the steps forming a
    doubly-linked list. 

    ...

    Attributes
    ----------
    id : int
        Unique int identifier for this Path.
    steps : list[Step]
        The ordered list of Steps that make up this Path.
    """

    id: int
    steps: list[Step]

    # Class variable to make unique IDs when a new Path is made.
    _next_id = 0
    def __init__(self):
        self.id = Path._next_id
        Path._next_id += 1
        self.steps = list()
    # end __init__

    def add_node(self, new_node: Node, edge_from_last: Edge=None):
        """
        Adds a Node to the end of this Path and makes a Step for it, along with 
        the Edge leading from the last Step to the new Node's Step. If this is 
        the first Step an Edge is not needed.
        """
        new_step = Step(new_node)
        self.add_step(new_step, edge_from_last=edge_from_last)

    # end add_node

    def add_step(self, new_step: Step, edge_from_last: Edge=None):
        """
        Adds a Step to the end of this Path, along with the Edge leading from the 
        last Step to the new Step. If this is the first step, an Edge is not needed.

        Sets the Steps' next and previous Steps appropriately.
        """
        # The first Step doesn't need a new Edge and doesn't need to update
        # any next or previous Edges. Subsequent Steps do.
        if len(self.steps) > 0:
            last_step = self.steps[len(self.steps) - 1]
            last_step.set_next_step(new_step, edge_from_last)
            new_step.set_previous_step(last_step, edge_from_last)
        # end if
        self.steps.append(new_step)
    # end add_step

# end path