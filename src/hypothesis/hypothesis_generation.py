from timeit import default_timer as timer

from commonsense.querier import CommonSenseQuerier
from commonsense.commonsense_data import (CommonSenseNode, CommonSenseEdge, 
                                          ConceptNetNode, WordNetNode)
from input_handling.scene_graph_data import (Image)
from knowledge_graph.graph import KnowledgeGraph 
from knowledge_graph.items import (Concept, Instance, Object, Action, Edge)
from knowledge_graph.path import (Path)

import constants as const
from constants import ConceptType

from hypothesis.hypothesis import (Hypothesis, ConceptEdgeHyp, 
                                   NewObjectHyp, 
                                   SameObjectHyp,
                                   PersistObjectHyp,
                                   NewActionHyp,
                                   CausalSequenceHyp,
                                   ActionHypothesis, Evidence, 
                                   ConceptEdgeEv, UnrelatedEv,
                                   CausalPathEv)

class HypothesisGenerator:
    """
    Handles generating hypotheses from a knowledge graph.
    """
    def __init__(self, commonsense_querier: CommonSenseQuerier):
        print(f'Initializing HypothesisGenerator')
        self._commonsense_querier = commonsense_querier
    # end __init__

    def generate_hypotheses(self, knowledge_graph: KnowledgeGraph) -> dict[int, Hypothesis]:
        """
        Generates hypotheses from a knowledge graph.

        Returns a dictionary of hypotheses, keyed by hypothesis id.
        """
        hypotheses = dict()
        print("Generating hypotheses")

        # Make NewObjectHyps and NewActionHyps
        #new_instance_hyps = self._hypothesize_new_instances(knowledge_graph=knowledge_graph)
        new_instance_hyps = {}

        # Make SameObjectHyps between objects that have the same labels between scenes.
        same_object_hyps = self._make_same_object_hyps(knowledge_graph=knowledge_graph,
                                                       new_object_hyps={h.id: h for h in new_instance_hyps.values() 
                                                                        if type(h) == NewObjectHyp})
        
        # Make CausalSequenceHyps between actions that have ConceptNet causal
        # paths between them. 
        causal_sequence_hyps = self._make_causal_sequence_hyps(knowledge_graph=knowledge_graph,
                                                               new_action_hyps={}) 

        hypotheses.update(same_object_hyps)
        hypotheses.update(causal_sequence_hyps)
        print("Done generating hypotheses")
        return hypotheses
    # end generate_hypotheses

    def _hypothesize_new_instances(self, knowledge_graph: KnowledgeGraph):
        """
        Hypothesizes new objects and actions for each scene.
        """
        # DEBUG
        timers = dict()
        timers['start'] = timer()
        times = dict()

        # First, make all new object and new action hypotheses without evidence.
        new_instance_hyps = dict()
        new_object_hyps = self._make_new_object_hyps(knowledge_graph=knowledge_graph)
        new_action_hyps = self._make_new_action_hyps(knowledge_graph=knowledge_graph)
        new_instance_hyps.update(new_object_hyps)
        new_instance_hyps.update(new_action_hyps)

        # Gather all the new objects and actions.
        new_instances = [h.obj for h in new_object_hyps.values()]
        new_instances.extend([h.action for h in new_action_hyps.values()])

        parsed_instance_pairs = set()

        # Dictionary of all the instances in each scene, keyed by the
        # scenes image id.
        all_scene_instances = dict()
        for image in knowledge_graph.images.values():
            # All observed instances in this image's scene.
            all_scene_instances[image.id] = knowledge_graph.get_scene_instances(image)
            # All hypothesized instances in this image's scene.
            all_scene_instances[image.id].extend(i for i in new_instances if i.get_image() == image)
        # end for

        # Next, build the ConceptEdgeEvidence. 
        # For each new instance, build ConceptEdgeEv between itself and
        # any other Instance in the same scene if its Concepts and the other
        # Instance's Concepts have an Edge with each other.
        # If there are none, instead build UnrelatedEv between them
        # using a penalty set in the parameter set as the score.
        for new_instance in new_instances:
            new_instance_hyp = new_instance_hyps[new_instance.source_hyp_id]
            # Get the new instance's scene image.
            image = new_instance.get_image()
            # Get all the instances in the same scene.
            scene_instances = all_scene_instances[image.id]
            # Go through each other Instance and look for Edges between
            # this Instance's Concepts and the other Instances Concepts.
            for other_instance in scene_instances:
                # Don't compare the instances to themselves.
                if new_instance == other_instance:
                    continue
                # end if
                # If this pair of instances has been parsed already, don't
                # parse it again.
                id_pair = frozenset([new_instance.id, other_instance.id])
                if id_pair in parsed_instance_pairs:
                    continue

                # Get shared concept edges for this pair of Instances.
                concept_edges = self._get_shared_concept_edges(new_instance, other_instance)

                # Make UnrelatedEv if there are no shared ConceptEdges.
                if len(concept_edges) == 0:
                    # The actual score has to be adjusted based on the
                    # parameter set. This is done in HypothesisEvaluator.
                    score = 1
                    unrelated_ev_1 = UnrelatedEv(source_instance=new_instance,
                                                 target_instance=other_instance,
                                                 score=score,
                                                 premise_hyp_ids=[other_instance.source_hyp_id] 
                                                    if other_instance.hypothesized 
                                                    else list())
                    # Add the evidence to the new Instance's source Hypothesis.
                    new_instance_hyp.add_unrelated_ev(unrelated_ev=unrelated_ev_1)
                    # Do the same for the other instance if it's hypothesized.
                    if other_instance.hypothesized:
                        unrelated_ev_2 = UnrelatedEv(source_instance=other_instance,
                                                     target_instance=new_instance,
                                                     score=score,
                                                     premise_hyp_ids=[new_instance.source_hyp_id])
                        other_instance_hyp = new_instance_hyps[other_instance.source_hyp_id]
                        other_instance_hyp.add_unrelated_ev(unrelated_ev_2)
                    # end if
                # end if
                # Otherwise, make ConceptEdgeEv for each shared Concept Edge.
                else:
                    for concept_edge in concept_edges:
                        concept_edge_ev_1 = ConceptEdgeEv(edge=concept_edge,
                                                          source_instance=new_instance,
                                                          target_instance=other_instance,
                                                          premise_hyp_ids=[other_instance.source_hyp_id] 
                                                              if other_instance.hypothesized 
                                                              else list())
                        # Add the evidence to the new Instance's source Hypothesis.
                        new_instance_hyp.add_concept_edge_ev(concept_edge_ev=concept_edge_ev_1)
                        # Do the same for the other Instance if it's hypothesized.
                        if other_instance.hypothesized:
                            concept_edge_ev_2 = ConceptEdgeEv(edge=concept_edge,
                                                              source_instance=other_instance,
                                                              target_instance=new_instance,
                                                              premise_hyp_ids=[new_instance.source_hyp_id])
                            other_instance_hyp = new_instance_hyps[other_instance.source_hyp_id]
                            other_instance_hyp.add_concept_edge_ev(concept_edge_ev_2)
                        # end if
                    # end for
                # end else
                # Add this ID pair to the set of parsed instance id pairs.
                parsed_instance_pairs.add(id_pair)
            # end for
        # end for

        times['total'] = timer() - timers['start']

        print(":)")

        return new_instance_hyps
    # end _hypothesize_new_instances

    def _make_new_object_hyps(self, knowledge_graph: KnowledgeGraph) -> dict[int, NewObjectHyp]:
        """
        Make new objects hypotheses based on a knowledge graph.

        These new object hypotheses won't have all of their evidence yet.
        ConceptEdgeEvidence has to be formed once all the hypothesized instances 
        have been made.

        Returns a dictionary of NewObjectHyps keyed by their IDs.
        """
        new_object_hyps = dict()
        # For each scene, make new object copies of its objects in every other
        # scene. 
        for source_image in knowledge_graph.images.values():
            for target_image in knowledge_graph.images.values():
                if source_image == target_image:
                    continue
                for source_object in [obj for obj in knowledge_graph.get_scene_objects(source_image)]:
                    new_object = Object(label=source_object.label, image=target_image,
                                        attributes=source_object.attributes,
                                        appearance=source_object.appearance,
                                        scene_graph_objects=source_object.scene_graph_objects,
                                        concepts=source_object.concepts,
                                        hypothesized=True,
                                        source_hyp_id=NewObjectHyp._next_id)
                    new_object_hyp = NewObjectHyp(obj=new_object, source_object=source_object)
                    new_object_hyps[new_object_hyp.id] = new_object_hyp
                # end for
            # end for
        # end for
        return new_object_hyps
    # end _make_new_object_hyps

    def _make_new_action_hyps(self, knowledge_graph: KnowledgeGraph) -> dict[int, NewActionHyp]:
        """
        Make new action hypotheses based on a knowledge graph.

        These new action hypotheses won't have all of their evidence yet.
        ConceptEdgeEvidence has to be formed once all the hypothesized instances 
        have been made.

        Returns a dictionary of NewActionHyps keyed by their IDs.
        """
        new_action_hyps = dict()

        # For each scene, find all the action concept causally linked to the
        # concepts of actions in the scene.
        # Make copies of those causally linked actions in each other scene.
        for source_image in knowledge_graph.images.values():
            # Get all the action concepts causally linked to the concepts
            # of this scene's actions.
            for source_action in knowledge_graph.get_scene_actions(source_image):
                causal_relation_pairs = self._get_causally_related_concepts(action=source_action,
                                                                            knowledge_graph=knowledge_graph)
                # Make a new action in every other image for every causally related concept.
                for target_image in knowledge_graph.images.values():
                    if source_image == target_image:
                        continue
                    for causal_relation_pair in causal_relation_pairs:
                        causally_related_concept = causal_relation_pair[0]
                        cs_edge = causal_relation_pair[1]
                        # Get the Edge with the causal relationship between
                        # one of the source action's concepts and the causally 
                        # related concept.
                        concept_edges = source_action.get_concept_edges_with(causally_related_concept)
                        source_causal_edge = None
                        for concept_edge in concept_edges:
                            if concept_edge.commonsense_edge == cs_edge:
                                source_causal_edge = concept_edge
                                break
                        # end for
                        # If we have not found a source concept edge, something
                        # has gone wrong.
                        if source_causal_edge is None:
                            print(f'Error: no concept edge found between source action' + 
                                  f' concepts and causally related concept!')
                        # end if
                        new_action = Action(label=causally_related_concept.label,
                                            image=target_image,
                                            subject=None,
                                            object=None,
                                            scene_graph_rel=None,
                                            concepts=[causally_related_concept],
                                            hypothesized=True,
                                            source_hyp_id=NewActionHyp._next_id)
                        new_action_hyp = NewActionHyp(action=new_action,
                                                      source_action=source_action,
                                                      source_causal_edge=source_causal_edge)
                        new_action_hyps[new_action_hyp.id] = new_action_hyp
                    # end for
                # end for
            # end for
        # end for
        return new_action_hyps
    # end _make_new_actions

    def _get_causally_related_concepts(self, action: Action, 
                                       knowledge_graph: KnowledgeGraph) -> list[(Concept, CommonSenseEdge)]:
        """
        Gets a list of all of the Concepts causally related to the given Action,
        along with the CommonSenseEdge that causally relates them.

        Only searches for other Action Concepts.
        """
        causally_related_concepts = list()
        # Go through all of this scene action's concepts.
        for source_action_concept in action.concepts:
            # Go through the CommonSenseEdges incident on this Concept.
            for cs_edge in source_action_concept.commonsense_edges.values():
                # Check if this edge's relationship is a causal relationship.
                # If not, skip it.
                relationship = cs_edge.get_relationship()
                if not relationship in const.COHERENCE_TO_RELATIONSHIP['causal']:
                    continue
                # Figure out whether the edge starts or ends at this Concept and
                # get the CommonSenseNode at the other end.
                other_cs_node_id = None
                if cs_edge.start_node_id in source_action_concept.commonsense_nodes:
                    other_cs_node_id = cs_edge.end_node_id
                elif cs_edge.end_node_id in source_action_concept.commonsense_nodes:
                    other_cs_node_id = cs_edge.start_node_id
                # If neither end is this Concept, something is wrong.
                # Skip this edge. 
                else:
                    continue
                # If the other cs node is ALSO in this Concept, the edge
                # points back to the Concept itself! Skip it.
                if other_cs_node_id in source_action_concept.commonsense_nodes:
                    continue
                # Query the node.
                other_cs_node = self._commonsense_querier.get_node(other_cs_node_id)
                # See if the CommonSenseNode has the 'pos' attribute.
                # If so, it's a ConceptNet or a WordNet node.
                if hasattr(other_cs_node, 'pos'):
                    related_concept = knowledge_graph.get_or_make_concept(
                        search_item=other_cs_node,
                        concept_type=ConceptType.ACTION)
                    if not related_concept in causally_related_concepts:
                        causally_related_concepts.append((related_concept, cs_edge))
                    # end if
                # end if
            # end for
        # end for
        return causally_related_concepts
    # end _get_causally_related_concepts

    def _get_shared_concept_edges(self, 
                                  instance_1: Instance, 
                                  instance_2: Instance) -> list[Edge]:
        """
        Gets all of the Edges between the Concepts of instance_1
        and the Concepts of instance_2.
        """
        shared_concept_edges = list()
        # Go through all of the Concepts for both Instances and see if any of 
        # them have any Edges with each other.
        for concept_1 in instance_1.concepts:
            for concept_2 in instance_2.concepts:
                shared_concept_edges.extend(concept_1.get_edges_with(concept_2))
        # end for
        return shared_concept_edges
    # end _get_shared_concept_edges

    def _make_same_object_hyps(self, knowledge_graph: KnowledgeGraph, new_object_hyps: dict[int, NewObjectHyp]):
        """
        Generates SameObjectHyps between objects that might be the same between
        scenes.

        Returns a dictionary of SameObjectHyps, keyed by hypothesis ID.
        """
        same_object_hyps = dict()

        # Keep track of which objects already have SameObjectHyps with each other
        # to avoid making duplicates.
        # Store it as a set of frozenpairs of ids.
        traversed_object_id_pairs = set()

        # Get all the observed and hypothesized objects for each scene into
        # lists. Keyed by the scene's image id.
        scene_objects = dict()
        for image in knowledge_graph.images.values():
            scene_objects[image.id] = knowledge_graph.get_scene_objects(image)
            scene_objects[image.id].extend([h.obj for h in new_object_hyps.values()
                                            if h.obj.get_image() == image])
        # end for

        # Go through every object in every scene. Look at every
        # other scene's observed objects and make SameObjectHyps with them
        # if their Concepts overlap. 
        # Also look through all the NewObjectHyps in that scene for new objects
        # whose concepts overlap. Make SameObjectHyps with those as well.
        # For those NewObjectHyps, if the object that made the NewObjectHyp
        # is the source object, premise the NewObjectHyp and the SameObjectHyp
        # on each other. 
        # For now, ANY concept overlapping counts.
        for source_image in knowledge_graph.images.values():
            # Gather all observed and hypothesized objects in this scene.
            source_scene_objects = scene_objects[source_image.id]
            for source_scene_object in source_scene_objects:
                # Look at the objects in other scenes and see if any of them
                # could be duplicates.
                for target_image in knowledge_graph.images.values():
                    if source_image == target_image:
                        continue
                    target_scene_objects = scene_objects[target_image.id]
                    for target_scene_object in target_scene_objects:
                        # Avoid traversing the same pairs of objects twice. 
                        id_pair = frozenset([source_scene_object.id, 
                                            target_scene_object.id])
                        if id_pair in traversed_object_id_pairs:
                            break
                        # Check if their Concepts overlap.
                        for source_concept in source_scene_object.concepts:
                            if target_scene_object.has_concept(source_concept):
                                # If so, make a SameObjectHyp between them.
                                same_object_hyp = SameObjectHyp(source_scene_object,
                                                                target_scene_object)
                                # If either objects are hypothesized from NewObjectHyps, 
                                # premise the new SameObjectHyp on its NewObjectHyp.

                                # If the other object is the observed object that
                                # lead to the NewObjectHyp being generated, then
                                # additionally premise that NewObjectHyp on this
                                # SameObjectHyp. 
                                if source_scene_object.hypothesized:
                                    new_object_hyp = new_object_hyps[source_scene_object.source_hyp_id]
                                    same_object_hyp.add_premise(new_object_hyp)
                                    if new_object_hyp.source_object == target_scene_object:
                                        new_object_hyp.add_premise(same_object_hyp)
                                # end if
                                if target_scene_object.hypothesized:
                                    new_object_hyp = new_object_hyps[target_scene_object.source_hyp_id]
                                    same_object_hyp.add_premise(new_object_hyp)
                                    if new_object_hyp.source_object == source_scene_object:
                                        new_object_hyp.add_premise(same_object_hyp)
                                # end if
                                same_object_hyps[same_object_hyp.id] = same_object_hyp
                                break
                            # end if
                        # end for
                        # Log that this pair of objects has been traversed.
                        traversed_object_id_pairs.add(id_pair)
                    # end for target_scene_object in target_scene_objects
                # end for target_image
            # end for source_scene_object
        # end for source_image

        return same_object_hyps
    # end _make_same_object_hyps

    def _make_causal_sequence_hyps(self, knowledge_graph: KnowledgeGraph, 
                                   new_action_hyps: dict[int, NewActionHyp]):
        """
        Make causal sequence hypotheses between every Action and every other
        Action in a different image with which there is a causal path through
        ConceptNet Concepts between the two Actions' Concepts.

        Returns a dictionary of CausalSequenceHyps, keyed by Hypothesis ID
        """

        causal_sequence_hyps = dict()

        # Set up a mapping of pairs of Action IDs to the CausalSequenceHyp
        # between them.
        # Action ID pairs are stored as frozenpairs of ints.
        # Multiple causal paths between the same two Actions will be
        # stored as multiple pieces of CausalPathEvs in the single 
        # CausalSequenceHyp between the two Actions.
        hyps_by_id_pair = dict()

        # Make a mapping of Image IDs to lists of Actions in those Images.
        actions_by_image = dict()
        for image_id, image in knowledge_graph.images.items():
            actions_by_image[image_id] = knowledge_graph.get_scene_actions(image)
        # end for

        # Go through all the Images.
        for source_image_id, source_image in knowledge_graph.images.items():
            # Get all the Actions in this Image.
            source_actions = actions_by_image[source_image_id]
            # Get all the Actions NOT in this Image.
            target_images = [i for i in knowledge_graph.images.values() 
                            if not source_image==i]
            target_actions = list()
            for target_image in target_images:
                target_actions.extend(actions_by_image[target_image.id])
            # end for
            # Compare all the Actions in this image with all the Actions not
            # in this image.
            for source_action in source_actions:
                for target_action in target_actions:
                    # Build the id pair.
                    id_pair = frozenset([source_action.id, 
                                         target_action.id])
                    # If the id pair already has a hypothesis connected to it,
                    # it has already been traversed in the other direction.
                    # Skip it.
                    if id_pair in hyps_by_id_pair:
                        continue

                    # Get any Edge shared between their Concepts whose
                    # corresponding CommonsenseEdge's relationship is causal.
                    shared_concept_edges = self._get_shared_concept_edges(instance_1=source_action,
                                                                          instance_2=target_action)
                    causal_concept_edges = [ce for ce in shared_concept_edges
                                            if ce.commonsense_edge.get_relationship() 
                                            in const.COHERENCE_TO_RELATIONSHIP['causal']]
                    # For each causal edge, make a Path with two steps.
                    # Step 1 is the Concept of the Action in this Image.
                    # Step 2 is the Concept of the Action in the other Image.
                    for causal_concept_edge in causal_concept_edges:
                        concept_path = Path()
                        # The Source Action is the Action in this image.
                        # The Target Action is the Action in the other image.
                        # Define source and target Concepts according to which
                        # Concept belongs to the Source Action and which belongs
                        # to the Target Action.
                        source_concept = None
                        target_concept = None
                        if (source_action.has_concept(causal_concept_edge.source)
                            and target_action.has_concept(causal_concept_edge.target)):
                            source_concept = causal_concept_edge.source
                            target_concept = causal_concept_edge.target
                        elif (source_action.has_concept(causal_concept_edge.target)
                              and target_action.has_concept(causal_concept_edge.source)):
                            source_concept = causal_concept_edge.target
                            target_concept = causal_concept_edge.source
                        else:
                            print('Error! Source and target concepts cannot be determined')
                        concept_path.add_node(new_node=source_concept,
                                              edge_from_last=None)
                        concept_path.add_node(new_node=target_concept,
                                              edge_from_last=causal_concept_edge)
                        # Make CausalPathEv using the concept path.
                        causal_path_evidence = CausalPathEv(source_action=source_action,
                                                            target_action=target_action,
                                                            source_concept=source_concept,
                                                            target_concept=target_concept,
                                                            concept_path=concept_path)
                        # Make or fetch the CasualSequenceHyp for this pair
                        # of actions.
                        if not id_pair in hyps_by_id_pair:
                            new_hyp = CausalSequenceHyp(source_action=source_action,
                                                        target_action=target_action)
                            hyps_by_id_pair[id_pair] = new_hyp
                        # end if
                        # Add the CausalPathEv to the Hypothesis.
                        hyps_by_id_pair[id_pair].add_evidence(causal_path_evidence)
                    # end for
                # end for
            # end for
        # end for

        # Add all hypotheses to the dictionary keyed by their IDs.
        for id_pair, hyp in hyps_by_id_pair.items():
            causal_sequence_hyps[hyp.id] = hyp

        return causal_sequence_hyps
    # end _make_causal_sequence_hyps






    # UNUSED
    # =============================

    def _hypothesize_concept_edge(self, instance_1: Instance, 
                                  instance_2: Instance):
        """
        Makes concept edge hypotheses between two Instances based on the
        edges between their Concepts. 

        Returns a list of all the hypotheses generated.
        """
        hypotheses = list()
        # Go through all of the edges from instance 1's Concepts.
        for concept in instance_1.concepts:
            # Get every edge with other Concepts and see if any of them are
            # with one of instance 2's concepts.
            concept_edges = concept.get_concept_edges()
            for edge in concept_edges:
                if edge.get_other_node(concept) in instance_2.concepts:
                    source_instance = None
                    target_instance = None
                    if edge.source == concept:
                        source_instance = instance_1
                        target_instance = instance_2
                    else:
                        source_instance = instance_2
                        target_instance = instance_1                     
                    # If it is, make a ConceptEdgeHypothesis of the two.
                    hypothesis = ConceptEdgeHyp(
                        source_instance=source_instance, 
                        target_instance=target_instance, 
                        edge=edge)
                    hypotheses.append(hypothesis)
                # end if
            # end for
        # end for
        return hypotheses
    # end _hypothesize_concept_edge




    def _get_related_concepts(self, instance: Instance, concept_type: ConceptType, 
                              knowledge_graph: KnowledgeGraph) -> list[Concept]:
        """
        Get all of the Concepts of a specified type related to the Instance passed in.

        Returns a list of Concepts.
        """
        related_concepts = list()

        # Look for a different part-of-speech depending on whether we're
        # searching for an Object or an Action.
        target_pos = ''
        if concept_type == ConceptType.OBJECT:
            target_pos = 'n'
        elif concept_type == ConceptType.ACTION:
            target_pos = 'v'
        # If it's neither of these, this is an error.
        else:
            return None
        # end elif

        # Go through all of the Instance's concepts.
        for instance_concept in instance.concepts:
            # Go through the CommonSenseEdges incident on this Concept.
            for cs_edge in instance_concept.commonsense_edges.values():
                # Figure out whether the edge starts or ends at this Concept and
                # get the CommonSenseNode at the other end.
                other_cs_node_id = None
                if cs_edge.start_node_id in instance_concept.commonsense_nodes:
                    other_cs_node_id = cs_edge.end_node_id
                elif cs_edge.end_node_id in instance_concept.commonsense_nodes:
                    other_cs_node_id = cs_edge.start_node_id
                # If neither end is this Concept, something is wrong.
                # Skip this edge. 
                else:
                    continue
                # If the other cs node is ALSO in this Concept, the edge
                # points back to the Concept itself! Skip it.
                if other_cs_node_id in instance_concept.commonsense_nodes:
                    continue
                # Query the node.
                other_cs_node = self._commonsense_querier.get_node(other_cs_node_id)
                # See if the CommonSenseNode has the 'pos' attribute.
                # If so, it's a ConceptNet or a WordNet node and we can check
                # if it's a noun.
                if hasattr(other_cs_node, 'pos'):
                    # See if the pos matches the part of speech we're looking for 
                    # based on whether we want Objects or Actions.
                    # If so, get or make a Concept for it in the knowledge graph
                    # and add that Concept to the list of related Concepts.
                    if other_cs_node.pos is not None and other_cs_node.pos == target_pos:
                        related_concept = knowledge_graph.get_or_make_concept(
                            search_item=other_cs_node,
                            concept_type=ConceptType.OBJECT)
                        if not related_concept in related_concepts:
                            related_concepts.append(related_concept)
                        # end if
                    # end if
                # end if
            # end for
        # end for
        return related_concepts
    # end _get_related_concepts

    def _make_concept_edge_hyps(self, knowledge_graph: KnowledgeGraph):
        """
        Makes concept edge hypotheses between all observed Instances in 
        the knowledge graph with every other observed Instance in the same scene. 

        Returns a list of all the hypotheses generated.
        """
        new_hypotheses = list()
        # Keep track of every pair of instances we've checked.
        # Each item in the set is a tuple of the ids of a pair of Instances.
        instance_pairs_checked = set()
        # Treat every image as its own scene.
        for image in knowledge_graph.images.values():
            instances = knowledge_graph.get_scene_instances(image)

            # Generate concept edge hypotheses between every instance and
            # every other instance in the same scene.
            for instance_1 in instances:
                for instance_2 in instances:
                    # Don't make concept edge hypotheses between an instance
                    # and itself.
                    if instance_1 == instance_2:
                        continue
                    # Have to check the id pairs in both orders.
                    id_pair_1 = (instance_1.id, instance_2.id)
                    id_pair_2 = (instance_2.id, instance_1.id)
                    # Don't make a hypothesis between a pair of instances that 
                    # have already been checked for concept edge hypotheses.
                    if (id_pair_1 in instance_pairs_checked
                        or id_pair_2 in instance_pairs_checked):
                        continue
                    # Generate concept edge hypotheses between the two.
                    hypotheses = self._hypothesize_concept_edge(
                        instance_1=instance_1, instance_2=instance_2)
                    new_hypotheses.extend(hypotheses)
                    # Log that the two instances have checked each other.
                    instance_pairs_checked.add(id_pair_1)
                    instance_pairs_checked.add(id_pair_2)
                # end for
            # end for
        # end for
        return new_hypotheses
    # _make_concept_edge_hyps

    def _hypothesize_concept_edge(self, instance_1: Instance, 
                                  instance_2: Instance):
        """
        Makes concept edge hypotheses between two Instances based on the
        edges between their Concepts. 

        Returns a list of all the hypotheses generated.
        """
        hypotheses = list()
        # Go through all of the edges from instance 1's Concepts.
        for concept in instance_1.concepts:
            # Get every edge with other Concepts and see if any of them are
            # with one of instance 2's concepts.
            concept_edges = concept.get_concept_edges()
            for edge in concept_edges:
                if edge.get_other_node(concept) in instance_2.concepts:
                    source_instance = None
                    target_instance = None
                    if edge.source == concept:
                        source_instance = instance_1
                        target_instance = instance_2
                    else:
                        source_instance = instance_2
                        target_instance = instance_1                     
                    # If it is, make a ConceptEdgeHypothesis of the two.
                    hypothesis = ConceptEdgeHyp(
                        source_instance=source_instance, 
                        target_instance=target_instance, 
                        edge=edge)
                    hypotheses.append(hypothesis)
                # end if
            # end for
        # end for
        return hypotheses
    # end _hypothesize_concept_edge

    def _hypothesize_for_continuity(self, knowledge_graph: KnowledgeGraph):
        """
        Generates Hypotheses to repair continuity between images.

        Returns a list of generated Hypotheses.
        """
        all_new_hypotheses = self._make_persist_object_hyps(
            knowledge_graph=knowledge_graph)
        
        # Get all observed and hypothesized Objects.
        all_objects = list(knowledge_graph.objects.values())
        all_objects.extend([h.object_ for h in all_new_hypotheses
                            if type(h) == PersistObjectHyp])

        for current_object in all_objects:
            # Get all the images the Object is NOT in.
            absent_images = [image for image in knowledge_graph.images.values()
                             if not image.id in current_object.images]
            for image in absent_images:
                # Go through each Object in this image and make a
                # SameObjectHyp with any of them whose Concepts
                # overlap with this current Object.
                scene_objects = [o for o in all_objects 
                                 if o.get_image() == image]
                for scene_object in scene_objects:
                    # See if any of the concepts overlap.
                    # If they do, make a SameObjectHyp.
                    for concept in current_object.concepts:
                        if scene_object.has_concept(concept):
                            # Don't make this same object hypothesis if a
                            # duplicate one already exists in the other
                            # direction. 
                            duplicate_hyps = [h for h in all_new_hypotheses
                                              if type(h) == SameObjectHyp and
                                              h.has_object(current_object) and
                                              h.has_object(scene_object)]
                            if len(duplicate_hyps) > 0:
                                break
                            new_od_h = SameObjectHyp(
                                object_1=current_object,
                                object_2=scene_object)
                            all_new_hypotheses.append(new_od_h)
                            break
                        # end if
                    # end for
                # end for scene_object in scene_objects
            # end for image in absent_images
        # end for current_object in all_objects

        return all_new_hypotheses
    # end _hypothesize_for_continuity

    def _make_persist_object_hyps(self, knowledge_graph: KnowledgeGraph):
        """
        Generates PersistObjectHyps for all observed Objects
        in the knowledge graph.

        Returns a list of all the new Hypotheses that were generated.
        """
        new_hypotheses = list()
        # Go through every observed Object in the knowledge graph.
        for current_object in knowledge_graph.objects.values():
            # Get all the images the Object is NOT in.
            absent_images = list()
            for image in knowledge_graph.images.values():
                if not image.id in current_object.images:
                    absent_images.append(image)
            # end for
            # For each Image the Object is not in, make a NewObjectHyp 
            # that an Object with the current Object's Concepts, appearance, and
            # attributes is in that Image. 
            for image in absent_images:
                # Make the hypothesized Object.
                # Make sure it has the original Object's attributes and
                # appearance.
                new_object = Object(label=current_object.label,
                                    image=image,
                                    attributes=current_object.attributes,
                                    appearance=current_object.appearance,
                                    concepts=current_object.concepts,
                                    hypothesized=True)
                # Give the hypothesized Object the focal score of the Object 
                # it's copying.
                new_object.focal_score = current_object.focal_score
                # Make ConceptEdgeHypotheses to every observed Instance in the
                # same scene.
                concept_edge_hyps = list()
                for scene_instance in knowledge_graph.get_scene_instances(image):
                    concept_edge_hyps.extend(
                        self._hypothesize_concept_edge(
                            instance_1=new_object, 
                            instance_2=scene_instance))
                # end for
                # Make ConceptEdgeHypotheses to every other hypothesized
                # Object in the same scene.
                obj_hypotheses = [h for h in new_hypotheses 
                                  if type(h) == NewObjectHyp
                                  and h.obj.get_image() == image]
                for existing_hypothesis in obj_hypotheses:
                    ces_to_existing_hypotheses = self._hypothesize_concept_edge(
                        instance_1=new_object, 
                        instance_2=existing_hypothesis.obj)
                    # Make the existing Object hypothesis a premise for this
                    # concept edge hypothesis, too, since it wouldn't exist
                    # without the existing Object hypothesis.
                    for concept_edge_hyp in ces_to_existing_hypotheses:
                        concept_edge_hyp.add_premise(existing_hypothesis)
                    concept_edge_hyps.extend(ces_to_existing_hypotheses)
                # end for
                # Make the NewObjectHyp using these 
                # ConceptEdgeHypotheses as evidence.
                new_object_hyp = NewObjectHyp(
                    obj=new_object, 
                    concept_edge_hyps=concept_edge_hyps)
                # Make an SameObjectHyp between the original Object
                # and the hypothesized Object.
                same_object_hyp = SameObjectHyp(
                    current_object, new_object)
                # Premise the SameObjectHyp on the 
                # NewObjectHyp, since it wouldn't exist without the 
                # new Object being hypothesized.
                same_object_hyp.add_premise(new_object_hyp)
                # Premise the NewObjectHyp on the 
                # SameObjectHyp, since if it isn't a duplicate of 
                # the original Object it has no reason to exist.
                new_object_hyp.add_premise(same_object_hyp)

                # Make the PersistObjectHyp based on this
                # NewObjectHyp and SameObjectHyp.
                persist_object_hyp = PersistObjectHyp(
                    object_ = new_object,
                    new_object_hyp=new_object_hyp,
                    same_object_hyp=same_object_hyp)
                
                # Premise both the object duplicate hypothesis and the offscreen
                # object hypothesis on the offscreen persistence hypothesis, as
                # they have no reason for existing without it.
                new_object_hyp.add_premise(persist_object_hyp)
                same_object_hyp.add_premise(persist_object_hyp)

                # Make sure to store the new Hypotheses
                new_hypotheses.append(new_object_hyp)
                new_hypotheses.extend(concept_edge_hyps)
                new_hypotheses.append(same_object_hyp)
                new_hypotheses.append(persist_object_hyp)
            # end for image in absent_images
        # end for current_object in knowledge_graph.objects.values()
        return new_hypotheses
    # end _make_persist_object_hyps

    def _make_new_action_hyps_old(self, existing_hypotheses: dict[int, Hypothesis], 
                              knowledge_graph: KnowledgeGraph):
        """
        Generates NewActionHyps.

        Hypothesizes what new Actions the hypothesized and observed Objects in
        each scene could be doing. 
        """
        # Get all existing NewObjectHyps
        new_object_hyps = [h for h in existing_hypotheses.values() if type(h) == NewObjectHyp]
        # Go through all the images.
        for image_id, image in knowledge_graph.images:
            # For each image, gather all the observed and hypothesized objects
            # in that image. 
            image_objects = list()
            hyp_image_objects = [h.obj for h in new_object_hyps 
                                 if h.obj.get_image().id == image_id]
            observed_image_objects = [i for i in knowledge_graph.get_scene_instances(image) 
                                      if type(i) == Object]
            image_objects.extend(hyp_image_objects)
            image_objects.extend(observed_image_objects)
            # For each object, get all the action concepts related to it.
            image_action_concepts = list()
            for obj in image_objects:
                object_action_concepts = self._get_related_action_concepts(obj=obj, knowledge_graph=knowledge_graph)
                image_action_concepts.extend(object_action_concepts)
            # end for obj in image_objects
            # For every action concept, make a hypothesized Action Instance.
            image_action_instances = list()
            for action_concept in image_action_concepts:
                action_instance = Action(label=action_concept.label,
                                         image=image, subject=None, object=None,
                                         scene_graph_rel=None, 
                                         concepts=[action_concept],
                                         hypothesized=True)
                image_action_instances.append(action_instance)
            # end for

            # Now that we have every hypothesized action, make a NewActionHyp
            # for each one. Try to form a ConceptEdgeHyp with every observed
            # and hypothesized instance in the same scene. 
        # end for image_id, image in knowledge_graph.images


        all_new_actions = list()
        # For each one, find all possible event concepts connected to the concepts
        # of the new object its hypothesizing.
        for new_object_hyp in new_object_hyps:
            event_concepts = list()
            for obj_concept in new_object_hyp.obj.concepts:
                # Check all the commonsense edges incident on each of the
                # object's concepts' commonsense nodes.
                for cs_node in obj_concept.commonsense_nodes.values():
                    for cs_edge_id in cs_node.edge_ids:
                        # Some edges, like VisualGenome edges, are ignored and
                        # won't appear in the list of CommonSenseEdges for a
                        # Concept. Check if it's in the list first.
                        if not cs_edge_id in obj_concept.commonsense_edges.keys():
                            continue
                        cs_edge = obj_concept.commonsense_edges[cs_edge_id]
                        # See if the other cs node is a verb. If so, find or make
                        # a concept for it and add it to the list of event concepts 
                        # related to this hypothesized object.
                        other_cs_node_id = cs_edge.get_other_node_id(cs_node.id)
                        other_cs_node = self._commonsense_querier.get_node(other_cs_node_id)
                        # See if the CommonSenseNode has the 'pos' attribute.
                        # If so, it's a ConceptNet or a WordNet node.
                        if hasattr(other_cs_node, 'pos'):
                            if other_cs_node.pos is not None and other_cs_node.pos == 'v':
                                event_concept = knowledge_graph.get_or_make_concept(
                                    search_item=other_cs_node,
                                    concept_type=ConceptType.ACTION)
                                if not event_concept in event_concepts:
                                    event_concepts.append(event_concept)
                                # end if
                            # end if
                        # end if
                # end for
            # end for

            # Now that we have event concepts related to this new object,
            # hypothesize a new action for each event concept. 
            # Make all of the new actions first.
            new_actions = list()
            for event_concept in event_concepts:
                new_action = Action(label=event_concept.label,
                                    image=new_object_hyp.obj.get_image(),
                                    subject=new_object_hyp.obj,
                                    object=None,
                                    scene_graph_rel=None,
                                    concepts=[event_concept],
                                    hypothesized=True)
                new_actions.append(new_action)
            # end for
            # Add them to the set of all new actions.
            all_new_actions.extend(new_actions)
        # end for

        new_action_hyps = list()
        all_concept_edge_hyps = list()
        for new_action in all_new_actions:
            image = new_action.subject.get_image()
            # For every new action, make ConceptEdgeHyp to every
            # observed Object in the same scene.
            scene_instances = knowledge_graph.get_scene_instances(image)
            scene_objects = [i for i in scene_instances if type(i) == Object]
            concept_edge_hyps = list()
            for scene_object in scene_objects:
                concept_edge_hyps.extend(self._hypothesize_concept_edge(
                    instance_1=new_action, instance_2=scene_object))
            # end for
            # Also make ConceptEdgeHyp to every hypothesized Object
            # in the same scene.
            for new_object_hyp in new_object_hyps:
                concept_edge_hyps.extend(self._hypothesize_concept_edge(
                    instance_1=new_action, instance_2=new_object_hyp.obj))
            # end for
            # Make a NewActionHyp using these ConceptEdgeHyps as evidence.
            new_action_hyp = NewActionHyp(
                action=new_action,
                concept_edge_hyps=concept_edge_hyps)
            new_action_hyps.append(new_action_hyp)
            all_concept_edge_hyps.extend(concept_edge_hyps)
        # end for
        print(f'Number of new action hypotheses: {len(new_action_hyps)}')
        all_hyps = list()
        all_hyps.extend(all_concept_edge_hyps)
        all_hyps.extend(new_action_hyps)
        return all_hyps
    # end _hypothesize_new_actions

    # TODO: Delete this?
    def _generate_action_hypotheses(self, knowledge_graph: KnowledgeGraph):
        """
        Generates hypotheses for unobserved actions.
        """
        # Go through every action.
        # Get the commonsense actions related to each action and object instance
        # This is the basis of our set of possible non-observed actions.
        # Key an Action id. Value is a list of CommonSenseNode objects.
        related_cs_actions = list()
        for node in knowledge_graph.nodes.values():
            # If the node is neither an object nor an action, skip it.
            if not type(node) == Object and not type(node) == Action:
                continue
            
            # Follow action-action and object-action edges in the commonsense
            # data to find related potential new actions.
            for concept in node.concepts:
                for cs_edge in concept.commonsense_edges:
                    # Check if the edge has a relationship that'll lead to
                    # another action.
                    if (type(node) == Object and not cs_edge.relation in 
                        const.OBJECT_ACTION_RELATIONSHIPS):
                        continue
                    elif (type(node) == Action and not cs_edge.relation in
                          const.ACTION_ACTION_RELATIONSHIPS):
                        continue
                    # Get the id of the commonsense node on this edge which is
                    # not one of the Concept's CommonSenseNodes.
                    other_cs_node_id = -1
                    if cs_edge.start_node_id not in concept.commonsense_nodes:
                        other_cs_node_id = cs_edge.start_node_id
                    elif cs_edge.end_node_id not in concept.commonsense_nodes:
                        other_cs_node_id = cs_edge.end_node_id
                    # If both the start and end of the edge lead to concept net
                    # nodes that are represented by this Concept, the edge leads
                    # from the Concept to itself!
                    # Skip this Concept
                    else:
                        continue
                    # end else
                    # Fetch the concept net node itself.
                    other_cs_node = self._commonsense_querier.get_node(
                                                            other_cs_node_id)
                    # If it's of a filtered action, ignore it.
                    # It's a filtered action if at least one of its labels is in
                    # the list of filtered actions defined in constants.
                    if len(set(other_cs_node.labels).intersection(set(const.FILTERED_ACTIONS))) > 0:
                        continue
                    # If it has a part-of-speech, make sure it's a verb.
                    if (hasattr(other_cs_node, 'pos') and
                        not other_cs_node.pos is None 
                        and not other_cs_node.pos == 'v'):
                        # If it has a part of speech that labels it as a noun,
                        # look for a definition from an external source.
                        # Acts are nouns but are still actions.
                        if (hasattr(other_cs_node, 'source_def') and
                            not other_cs_node.source_def is None):
                            if not other_cs_node.source_def == 'act':
                                continue
                            # end if
                        else:
                            continue
                        # end if else
                    # end if
                    # Only add it to the overall list of related conceptnet
                    # actions if it's not already in it.
                    if not other_cs_node in related_cs_actions:
                        related_cs_actions.append(other_cs_node)
                # end for
            # end for
        # end for action in knowledge_graph.actions.values()

        # Now that we have all unique commonsense nodes that are actions related 
        # to existing Instances, make a hypothetical Action out of each concept 
        # net node.
        # Then, make an ActionHypothesis out of each hypothetical Action.
        # Dictionary of ActionHypothesis objects, keyed by hypothesis id.
        action_hypotheses = dict()
        timers = dict()
        timer_sums = dict()
        timer_sums['get or make_concepts'] = 0
        timer_sums['parse potential actions'] = 0
        for cs_action in related_cs_actions:
            timers['action_start'] = timer()
            # Make or get a Concept for this commonsense action.
            concept = knowledge_graph.get_or_make_concept(cs_action,
                                                          ConceptType.ACTION)
            timers['get_or_make_concept_end'] = timer()
            timer_sums['get or make_concepts'] += timers['get_or_make_concept_end'] - timers['action_start']
            # A new action hypothesis will be made for each scene in which
            # this Action is grounded by a conceptually related Instance.
            # Keep track of an action and list of evidence per scene.
            # Keyed by image id.
            new_actions = dict()
            evidence = dict()
            # Go through each of the hypothesized Action's Concept's edges to
            # other Concepts.
            if len(concept.edges) == 0:
                print(f'Error! Concept {concept} has no edges!')
            for edge in concept.edges.values():
                other_concept = edge.get_other_node(concept)
                if not type(other_concept) == Concept:
                    continue
                # Get all instances of the other Concept. These are the existing
                # Instances that might be related to the hypothezied
                # Action through a relationship between their Concepts. 
                instances = knowledge_graph.get_concept_instances(other_concept)
                # Make a piece of ConceptEdgeEv for each one. 

                # Organize the instance evidence by image index.
                for instance in instances:
                    # See if there's an Action and Evidence list for this 
                    # Instance's scene yet.
                    if not instance.get_image().id in new_actions:
                        # If not, start a new evidence list and make a new
                        # hypothetical action for this image.
                        new_actions[instance.get_image().id] = Action(
                            label=concept.label, image=instance.get_image(),
                            concepts=[concept], hypothesized=True)
                        evidence[instance.get_image().id] = list()
                    # end if
                    # Make evidence for this conceptually related Instance.
                    new_evidence = None
                    if edge.source == concept:
                        new_evidence = ConceptEdgeEv(
                            source_instance=new_actions[instance.get_image().id],
                            target_instance=instance,
                            edge=edge)
                    elif edge.target == concept:
                        new_evidence= ConceptEdgeEv(
                            source_instance=instance,
                            target_instance=new_actions[instance.get_image().id],
                            edge=edge)
                    # end elif
                    if new_evidence is None:
                        print(f'Error! Hypothesized action\'s concept was ' +
                              f'neither the source nor the target of its '+
                              f' Concept edge!')
                    evidence[instance.get_image().id].append(new_evidence)
                # end for
            # end for

            for image_id, action in new_actions.items():
                # Make the ActionHypothesis for each new hypothesized Action.
                action_hypothesis = ActionHypothesis(action=action, 
                                    evidence=evidence[instance.get_image().id])
                action_hypotheses[action_hypothesis.id] = action_hypothesis
            # end for

            # DEBUG
            time_taken = timer() - timers["action_start"]
            #if time_taken > 0.1:
            #    print(f'cn action {cn_action.uri}, edges:' + 
            #          f' {len([edge for edge in concept.edges.values() if type(edge.get_other_node(concept)) == Concept])}' +
            #          f' time taken: {time_taken}')
            # end if
            timer_sums['parse potential actions'] += time_taken
            # END DEBUG

        # end for
        print(f'Time spent getting or making concepts: {timer_sums["get or make_concepts"]}')
        print(f'Total time spent parsing potential actions: {timer_sums["parse potential actions"]}')
        # Return all the action hypotheses we made.
        return action_hypotheses
    # end _generate_action_hypotheses

# end class HypothesisGenerator

