from functools import singledispatchmethod
from typing import Union
from timeit import default_timer as timer

from knowledge_graph.items import (Node, Concept, Instance, Object, Action, 
                                   Edge)

from commonsense import querier
from commonsense.querier import CommonSenseQuerier

from input_handling.scene_graph_data import (Image, BoundingBox, Synset, SceneGraphObject, 
                                             SceneGraphRelationship)
from commonsense.commonsense_data import (CommonSenseNode, CommonSenseEdge,
                                          ConceptNetNode)

from constants import ConceptType
import constants as const

class KnowledgeGraph:
    """
    A knowledge graph of Concepts, Objects, Actions, and the relationships
    between them.

    ...
    
    Parameters:
    -----------
    commonsense_querier : CommonSenseQuerier
        A querier to interact with commonsense data.

    Attributes:
    ----------
    nodes : dict[int, Node]
        Dictionary of the Nodes in this graph, keyed by node id.
    concepts : dict[int, Concept]
        Dictionary of the Concept nodes in this graph, keyed by node id.
        Subset of overall nodes dictionary.
    objects : dict[int, Object]
        Dictionary of the Object nodes in this graph, keyed by node id.
        Subset of overall nodes dictionary.
    actions : dict[int, Action]
        Dictionary of the Action nodes in this graph, keyed by node id.
        Subset of overall nodes dictionary.
    hypothesized_nodes : dict[int, Node]
        Dictionary of the hypothesized Nodes made for this graph, keyed by
        node id. 
    hypothesized_objects : dict[int, Object]
        Dictionary of the hypothesized Object nodes made for this graph, keyed
        by node id. Subset of the overall hypothesized_nodes dictionary. 
    edges : dict[int, Edge]
        Dictionary of the Edges in this graph, keyed by edge id.
    images : dict[int, Image]
        Dictionary of all the Images the nodes in this graph came from, keyed by
        image id.
    """
    nodes: dict[int, Node]
    concepts: dict[int, Concept]
    objects: dict[int, Object]
    actions: dict[int, Action]
    hypothesized_objects: dict[int, Object]
    edges: dict[int, Edge]
    images: dict[int, Image]

    # A mapping of CommonSenseNode ids to sets of ids for the Concepts
    # they're in.
    _concept_membership_map: dict[int, set[int]]

    def __init__(self, commonsense_querier: CommonSenseQuerier):
        self.nodes = dict()
        self.concepts = dict()
        self.objects = dict()
        self.actions = dict()
        self.hypothesized_nodes = dict()
        self.hypothesized_objects = dict()
        self.edges = dict()
        self.images = dict()
        # A concept net querier for the knowledge graph to use to make
        # Concepts with.
        self._commonsense_querier = commonsense_querier
        self._concept_membership_map = dict()
    # end __init__

    def __contains__(self, item):
        """
        Checks whether or not a Node or Edge is present in this KnowledgeGraph.

        If the item is neither a Node nor an Edge, returns False.
        """
        # For nodes, check if the node dictionary has the given node.
        if isinstance(item, Node):
            if item.id in self.nodes:
                return True
            # If not in the regular nodes dictionary, check the hypothesized
            # objects dictionary.
            elif item.id in self.hypothesized_objects:
                return True
            else:
                return False
        # For edges, check if the edge dictionary has the given edge.
        elif isinstance(item, Edge):
            if item.id in self.edges:
                return True
            else:
                return False
        else:
            return False
    # end __contains__

    def update (self, knowledge_graph):
        """
        Updates the Nodes and Edges in this knowledge graph with the Nodes
        and Edges in the knowledge graph passed in.

        Only updates which Nodes and Edges exist in this knowledge graph. Does 
        not touch the contents of any specific Node or Edge.

        Also merges this knowledge graph's concept membership map and images 
        with that of the knowledge graph passed in.
        """
        # Don't try to update from non-KnowledgeGraph objects.
        if not type(knowledge_graph) == KnowledgeGraph:
            return
        self.nodes.update(knowledge_graph.nodes)
        self.concepts.update(knowledge_graph.concepts)
        self.objects.update(knowledge_graph.objects)
        self.actions.update(knowledge_graph.actions)
        self.hypothesized_objects.update(knowledge_graph.hypothesized_objects)
        self.edges.update(knowledge_graph.edges)
        # Merge the concept membership maps.
        cm_map = knowledge_graph._concept_membership_map
        for cn_node_id, concept_id_set in cm_map.items():
            if not cn_node_id in self._concept_membership_map:
                self._concept_membership_map[cn_node_id] = set()
            self._concept_membership_map[cn_node_id].update(concept_id_set)
        # end for
        self.images.update(knowledge_graph.images)
    # end update

    @singledispatchmethod
    def get_concept(self, search_item: Union[str, Synset, CommonSenseNode], 
                    concept_type: ConceptType):
        """
        Gets the Concept node for the label or Synset passed in if it exists.
        Returns None otherwise.

        Parameters
        ----------
        search_item : str | Synset | CommonSenseNode
            Gets the Concept node for this search item.

            If the search item is a string, searches for a Concept whose word
            matches that string.

            If the search item is a Synset, searches for a Concept whose synset
            exactly matches that synset.

            If the search item is a CommonSenseNode, searched for a Concept that
            contains that CommonSenseNode.
        concept_type : ConceptType
            The type of Concept to search for.
        
        Returns
        -------
        Concept | None
            The Concept node for the search item passed in with type passed in.

            None if there is no Concept node for the search item and type in 
            this knowledge graph.
        """
        raise NotImplementedError(f'get_concept : cannot search for a ' + 
                                  f'{type(search_item)}')
    # end get_concept
    @get_concept.register
    def _get_concept_synset(self, search_item: Synset, 
                            concept_type: ConceptType):
        for concept in self.concepts.values():
            if (concept.synset == search_item 
                and concept.concept_type == concept_type):
                return concept
        # end for
        return None
    # end _get_concept_synset
    @get_concept.register
    def _get_concept_str(self, search_item: str, concept_type: ConceptType):
        for concept in self.concepts.values():
            if (concept.label == search_item 
                and concept.concept_type == concept_type):
                return concept
        # end for
        return None
    # end _get_concept_str
    @get_concept.register
    def _get_concept_commonsense_node(self, search_item: CommonSenseNode, 
                                      concept_type: ConceptType):
        for concept in self.concepts.values():
            if search_item.id in concept.commonsense_nodes:
                return concept
        # end for
        return None
    # end _get_concept_commonsense_node

    def get_or_make_concept(self, 
                            search_item: Union[str, Synset, CommonSenseNode], 
                            concept_type: ConceptType) -> Concept:
        """
        Gets the Concept node for the label, synset, or commonsense node passed 
        in if it exists. If it does not exist, makes a new Concept node and adds 
        it to this knowledge graph.

        Parameters
        ----------
        search_item : str | Synset |
            The label, Synset, or CommonSenseNode to find or make a Concept for.
        concept_type : ConceptType
            The type of Concept to look for or make.

        Returns
        -------
        Concept
            The Concept node for the search item and type passed in.
        """
        concept = self.get_concept(search_item, concept_type)
        if concept is None:
            if type(search_item) == str:
                concept = self.make_concept(label=search_item, 
                                            concept_type=concept_type)
            elif type(search_item) == Synset:
                concept = self.make_concept(label=search_item.word, 
                                            concept_type=concept_type, 
                                            synset=search_item)
            elif issubclass(type(search_item), CommonSenseNode):
                concept = self.make_concept(label=search_item.labels[0],
                                            concept_type=concept_type,
                                            commonsense_node=search_item)
            # end elif
            # Add the newly made Concept to this knowledge graph.
            if not concept is None:
                self.add_node(concept)
            # end if
        # end if
        return concept
    # end get_or_make_concept

    # DEBUG
    _timer_sums = {'make_concept': 0,
                   'find_nodes': 0,
                   'get_edges': 0,
                   'add_edges': 0,
                   'make_edges': 0}
    def make_concept(self, label: str, concept_type: ConceptType, 
                     synset: Synset = None, 
                     commonsense_node: CommonSenseNode = None):
        """
        Makes a Concept with the given Label, ConceptType, and, optionally, an
        existing Synset and/or existing CommonSenseNode.

        If no existing Synset is provided, a Synset will be found for the label.

        The resulting Concept will have its associated commonsense nodes
        and edges, as well as an Edge to every existing Concept that its
        commonsense nodes have commonsense edges to.

        Returns the Concept node that was made.
        """
        timers = dict()
        timers['start'] = timer()
        pos = ''
        score_threshold = 0.8
        if concept_type == ConceptType.OBJECT:
            pos = 'n'
        elif concept_type == ConceptType.ACTION:
            pos = 'v'
        # Find a synset based on the label if one wasn't provided.
        if synset is None:
            synset = querier.find_synset(label, pos)
        # end if
        # Make the Concept.
        concept = Concept(label, concept_type, synset)
        # Get ConceptNet nodes and edges. 
        search_word = label
        # If a CommonSenseNode was provided, uses its first label.
        if not commonsense_node == None:
            search_word = commonsense_node.labels[0]
        # Otherwise, use the synset's term.
        else:
            search_word = synset.word
        # Find other CommonSenseNodes matching the search word.
        # If a CommonSenseNode was provided, the results from the querier will 
        # naturally include that node.
        timers['find_nodes_start'] = timer()
        cs_nodes = self._commonsense_querier.find_nodes(search_word)
        timers['find_nodes_end'] = timer()
        KnowledgeGraph._timer_sums['find_nodes'] += timers['find_nodes_end'] - timers['find_nodes_start']
        for cs_node in cs_nodes:
            # Filter out any commonsense nodes that don't match the concept's
            # type.
            # ConceptNet nodes may not have a part of speech, so check first.
            if type(cs_node) == ConceptNetNode:
                if not cs_node.pos is None and not cs_node.pos == pos:
                    continue

            # Add the CommonSenseNode to the Concept.
            concept.add_commonsense_node(cs_node)
            # Get the CommonSenseEdges for this node and add them to the Concept 
            # as well.
            timers['get_edges_start'] = timer()
            cs_edges = self._commonsense_querier.get_edges(cs_node.id)
            timers['get_edges_end'] = timer()
            KnowledgeGraph._timer_sums['get_edges'] += timers['get_edges_end'] - timers['get_edges_start']
            for cs_edge in cs_edges:
                timers['add_edge_start'] = timer()
                concept.add_commonsense_edge(cs_edge)
                timers['add_edge_end'] = timer()
                KnowledgeGraph._timer_sums['add_edges'] += timers['add_edge_end'] - timers['add_edge_start']
            #for cs_edge in self._commonsense_querier.get_edges(cs_node):
            #    concept.add_commonsense_edge(cs_edge)
            ## end for

            # Update the mapping of CommonSenseNode ids to Concept ids.
            if not cs_node.id in self._concept_membership_map:
                self._concept_membership_map[cs_node.id] = set()
            self._concept_membership_map[cs_node.id].add(concept.id)
        # end for

        timers['make_edges_start'] = timer()

        # Make an Edge between Concepts for each of this new Concept's
        # CommonSenseEdges that lead to a CommonSenseNode in another Concept.
        for cs_edge in concept.commonsense_edges.values():
            other_cs_node_id = -1
            # Whether or not this edge points away from this concept.
            points_away = False
            # If both the start and end node IDs are in the Concept, the edge
            # loops around to the Concept itself. Ignore it.
            if (cs_edge.start_node_id in concept.commonsense_nodes and
                cs_edge.end_node_id in concept.commonsense_nodes):
                continue
            # If the edge's start node is the one that's in the concept, the 
            # edge points away from the concept.
            # The other node is the end node.
            elif cs_edge.start_node_id in concept.commonsense_nodes:
                 other_cs_node_id = cs_edge.end_node_id
                 points_away = True
            elif cs_edge.end_node_id in concept.commonsense_nodes:
                 other_cs_node_id = cs_edge.start_node_id
                 points_away = False
            # end elif
            else:
                print(f'Error! Neither cn edge\'s start nor end nodes are one' +
                      f' of the Concept\'s CommonSenseNodes!')
            # See if there are Concepts representing this cn node.
            # If there aren't any existing Concepts for the CommonSenseNode at 
            # the other end of the edge, don't make a new one or it will start 
            # recursively calling this function.
            # Instead, move on to the next concept net edge.
            if not other_cs_node_id in self._concept_membership_map:
                continue
            ex_concept_ids = self._concept_membership_map[other_cs_node_id]

            # If there are, make an Edge between the new Concept and each 
            # existing Concept mapped to this CommonSenseNode.
            for existing_concept_id in ex_concept_ids:
                existing_concept = self.concepts[existing_concept_id]
                # Make the Edge in the same direction as the CommonSenseEdge.
                source_node = None
                target_node = None
                if points_away:
                    source_node = concept
                    target_node = existing_concept
                else:
                    source_node = existing_concept
                    target_node = concept
                # end else
                self.make_and_add_edge(source=source_node,
                                       target=target_node,
                                       relationship=cs_edge.relation,
                                       weight=cs_edge.weight,
                                       commonsense_edge=cs_edge)
            # end for
        # end for

        timers['make_edges_end'] = timer()
        KnowledgeGraph._timer_sums['make_edges'] += timers['make_edges_end'] - timers['make_edges_start']
        KnowledgeGraph._timer_sums['make_concept'] += timers['make_edges_end'] - timers['start']

        return concept
    # end make_concept

    def get_concept_instances(self, concept: Concept) -> list[Instance]:
        """
        Returns a list of all Nodes that are Instances of the Concept passed in.

        A Node is an Instance of a Concept if it is an Instance and has a 
        concept attribute that matches the Concept.
        """
        instances = list()
        for action in self.actions.values():
            if concept in action.concepts:
                instances.append(action)
        # end for
        for object in self.objects.values():
            if concept in object.concepts:
                instances.append(object)
        # end for
        return instances
    # end get_concept_instances

    def get_scene_instances(self, image: Image):
        """
        Gets a list of all of the Instances present in a single scene, 
        represented by the scene's Image object.
        """
        return [node for node in self.get_all_instances() 
                if node.get_image() == image]
    # end get_scene_instances

    def get_all_instances(self) -> list[Instance]:
        """
        Gets a list of all of the Instances in this knowledge graph.
        """
        instances = list()
        instances.extend([node for node in self.objects.values()])
        instances.extend([node for node in self.actions.values()])
        return instances
    # end get_all_instances

    def add_node(self, node: Node):
        """
        Adds a Node to the knowledge graph.

        Adds it both to the overall dictionary of Nodes and to one of the
        dictionaries for specific node subtypes.

        If the Node is an Instance and has an Image that is not present in this
        knowledge graph's set of images, also updates that. 

        If the Node is an Instance, adds all the Instance's Concepts to this
        knowledge graph.
        
        Prevents duplicate entries.
        """
        # Prevent duplicates.
        if node.id in self.nodes:
            return
        self.nodes[node.id] = node
        # Add the node to its specific subtype dictionary as well.
        if type(node) == Concept:
            self.concepts[node.id] = node
        elif issubclass(type(node), Instance):
            # Add all the Instance's Concepts to this knowledge graph.
            for concept in node.concepts.values():
                self.add_node(concept)
            # Take all the images this node Instance is grounded in. 
            self.images.update(node.images)
            if type(node) == Object:
                self.objects[node.id] = node
            elif type(node) == Action:
                self.actions[node.id] = node
        else:
            print(f'Node {node.name} has no subtype!')
    # end add_node

    def remove_node(self, node: Node):
        """
        Removes a node from this KnowledgeGraph.

        Removes it from both this KnowledgeGraph's dictionary of all Nodes and 
        from its dictionary of all Nodes of the Node's subtype.
        """
        self.nodes.pop(node.id)
        if type(node) == Concept:
            self.concepts.pop(node.id)
        elif type(node) == Object:
            self.objects.pop(node.id)
        elif type(node) == Action:
            self.actions.pop(node.id)
        # end elif
    # end remove_node

    def add_edge(self, edge: Edge):
        """
        Adds an Edge to the knowledge graph.
        
        Prevents duplicate entries.
        """
        # Prevent duplicates.
        if edge.id in self.edges:
            return
        self.edges[edge.id] = edge
    # end add_edge

    def make_and_add_edge(self, source: Node, target: Node, relationship: str, 
                          weight: float = None, 
                          commonsense_edge : CommonSenseEdge = None):
        """
        Makes an Edge between the source and target nodes with the given
        relationship and, optionally, weight and/or CommonSenseEdge, then adds 
        the edge to both nodes and to this knowledge graph.

        Returns
        -------
        Edge
            The edge that was created.
        """
        edge = (Edge(source=source, 
                     target=target, 
                     relationship=relationship)
                if weight == None else
                Edge(source=source,
                     target=target,
                     relationship=relationship,
                     weight=weight))
        if not commonsense_edge is None:
            edge.commonsense_edge = commonsense_edge
        # Add the edge to its source and target nodes.
        edge.source.add_edge(edge)
        edge.target.add_edge(edge)
        # Add the edge to this knowledge graph.
        self.add_edge(edge)
        return edge
    # end make_and_add_edge

    def set_focal_node(self, node_id: int, focal_score: float):
        """
        Sets the Instance with the node id passed in as a focal node and gives
        it the focal score passed in.

        Updates every other Instance with the focal node and their distance
        to the focal node.
        """
        focal_node = self.nodes[node_id]
        focal_node.focal_score = focal_score

        # Propagate the focal node using BFS.
        # Keep a queue of nodes to be checked.
        # Start by checking all neighboring instances.
        nodes_to_check = focal_node.get_neighboring_instances()
        # Keep track of which nodes have already been checked OR added to the
        # queue of nodes to be checked.
        checked_nodes = {node.id for node in nodes_to_check}
        checked_nodes.add(focal_node.id)
        # Store the distance of each node from the focal node.
        node_distances = {focal_node.id: 0}
        for node in nodes_to_check:
            node_distances[node.id] = 1
        while len(nodes_to_check) > 0:
            # Pop the first node in the queue.
            node = nodes_to_check.pop(0)
            # Get its distance.
            distance = node_distances[node.id]
            # Add the focal node and its distance in this node.
            node.add_focal_node(focal_node, distance)
            # Add this node's neighboring instances to the list of nodes to
            # check if they haven't already been added.
            neighboring_instances = node.get_neighboring_instances()
            for neighbor in neighboring_instances:
                if not neighbor.id in checked_nodes:
                    nodes_to_check.append(neighbor)
                    checked_nodes.add(neighbor.id)
                    node_distances[neighbor.id] = distance + 1
                # end if
            # end for
        # end while
    # end set_focal_node

    def get_focal_nodes(self):
        """
        Gets a list of all the focal nodes in this graph.

        Any node with a non-zero focal score is a focal node.
        """
        return [node for node in self.get_all_instances()
                if not node.focal_score == 0]
    # end get_focal_nodes

    def get_commonsense_nodes(self):
        """
        Gets a list of all of the unique CommonSenseNodes in Concepts in this
        KnowledgeGraph.
        """
        cs_node_ids = set()
        cs_nodes = list()
        for concept in self.concepts.values():
            for cs_node in concept.commonsense_nodes.values():
                if not cs_node.id in cs_node_ids:
                    cs_nodes.append(cs_node)
                    cs_node_ids.add(cs_node.id)
                # end if
            # end for
        # end for
        return cs_nodes
    # end get_commonsense_nodes

    def get_commonsense_edges(self):
        """
        Gets a list of all the unique CommonSenseEdges in Concepts in this
        KnowledgeGraph.
        """
        cs_edge_ids = set()
        cs_edges = list()
        for concept in self.concepts.values():
            for cs_edge_id, cs_edge in concept.commonsense_edges.items():
                if not cs_edge_id in cs_edge_ids:
                    cs_edges.append(cs_edge)
                    cs_edge_ids.add(cs_edge_id)
                # end if
            # end for
        # end for
        return cs_edges
    # end get_commonsense_edges
# end class KnowledgeGraph