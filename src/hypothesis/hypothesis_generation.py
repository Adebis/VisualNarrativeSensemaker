from timeit import default_timer as timer

from commonsense.querier import CommonSenseQuerier
from commonsense.commonsense_data import (CommonSenseNode, CommonSenseEdge, 
                                          ConceptNetNode, WordNetNode)
from input_handling.scene_graph_data import (Image)
from knowledge_graph.graph import KnowledgeGraph 
from knowledge_graph.items import (Concept, Instance, Object, Action, Edge)
from knowledge_graph.path import (Path, MultiPath)

import constants as const
from constants import ConceptType

from hypothesis.evidence import (Evidence, VisualSimEv, AttributeSimEv,
                                 CausalPathEv, ContinuityEv, MultiCausalPathEv)
from hypothesis.hypothesis import (Hypothesis,
                                   SameObjectHyp,
                                   CausalSequenceHyp)

class HypothesisGenerator:
    """
    Handles generating hypotheses from a knowledge graph.
    """

    # Whether we have to obey the initial ordering of the images or not.
    ordering_constraint_active: bool

    def __init__(self, commonsense_querier: CommonSenseQuerier):
        print(f'Initializing HypothesisGenerator')
        self._commonsense_querier = commonsense_querier
        self.ordering_constraint_active = True
    # end __init__

    def generate_hypotheses(self, knowledge_graph: KnowledgeGraph) -> dict[int, Hypothesis]:
        """
        Generates hypotheses from a knowledge graph.

        Returns a dictionary of hypotheses, keyed by hypothesis id.
        """
        hypotheses = dict()
        print("Generating hypotheses")

        # Make SameObjectHyps between objects that have the same labels between scenes.
        same_object_hyps = self._make_same_object_hyps(knowledge_graph=knowledge_graph)
        
        # Make CausalSequenceHyps between actions that have ConceptNet causal
        # paths between them. 
        causal_sequence_hyps = self._make_causal_sequence_hyps(
            knowledge_graph=knowledge_graph,
            referential_hyps=same_object_hyps) 

        hypotheses.update(same_object_hyps)
        hypotheses.update(causal_sequence_hyps)
        print("Done generating hypotheses")
        return hypotheses
    # end generate_hypotheses

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

    def _make_same_object_hyps(self, knowledge_graph: KnowledgeGraph) -> dict[int, Hypothesis]:
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
        # end for

        # Go through every object in every scene. Look at every
        # other scene's observed objects and make SameObjectHyps with them
        # if their Concepts overlap. 
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

    def _make_causal_sequence_hyps(self, 
                                   knowledge_graph: KnowledgeGraph,
                                   referential_hyps: dict[int, Hypothesis]) -> dict[int, Hypothesis]:
        """
        Make causal sequence hypotheses between every Action and every other
        Action in a different image with which there is a causal path through
        ConceptNet Concepts between the two Actions' Concepts.

        Returns a dictionary of CausalSequenceHyps, keyed by Hypothesis ID
        """

        causal_sequence_hyps = dict()

        # Set up a mapping of pairs of Action IDs to the CausalSequenceHyp
        # between them.
        # Key is a pair of Action IDs.
        # Value is a list of hypotheses between those two actions.
        # Action ID pairs are stored as frozenpairs of ints.
        # Multiple causal paths in the same direction between the same two 
        # Actions will be stored as multiple pieces of CausalPathEvs in the 
        # single CausalSequenceHyp in that direction between the two Actions.
        hyps_by_id_pair = dict()

        # Make a mapping of Image IDs to lists of Actions in those Images.
        actions_by_image: dict[int, list[Action]] = dict()
        for image_id, image in knowledge_graph.images.items():
            actions_by_image[image_id] = knowledge_graph.get_scene_actions(image)
        # end for

        # Get a list of images ordered by their index (i.e. the order they're
        # defined in the image set).
        images_by_index: list[Image] = list()
        # n^2 insertion sort lol
        for image_id, image in knowledge_graph.images.items():
            # Search from the lowest index image until you find an index with
            # a higher index than this image. Then, insert this image behind
            # that image. 
            for i in range(len(images_by_index)):
                if image.index < images_by_index[i].index:
                    images_by_index.insert(i - 1, image)
                    break
                # end if
            # end for

            # If this is the image with the largest index, put it at the end.
            images_by_index.append(image)
        # end for

        # Go through all the Images.
        for source_image in images_by_index:
            source_image_id = source_image.id
            # Get all the Actions in this Image.
            source_actions = actions_by_image[source_image_id]
            # Get all the Actions NOT in this Image.
            target_images = [i for i in images_by_index
                             if not source_image==i]
            target_actions: list[Action] = list()
            for target_image in target_images:
                # ORDERING CONSTRAINT:
                # If obeying image ordering, don't look at actions in images
                # earlier than this one.
                # If the target image has a lower index than the source image,
                # skip it.
                if self.ordering_constraint_active:
                    if target_image.index < source_image.index:
                        continue

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
                    
                    # We want to prevent actions that are the same from
                    # forming CausalSequenceHyps with each other.
                    # Check their labels. If they're the same, skip this pair.
                    if source_action.label == target_action.label:
                        continue

                    # Find causal path evidence for the two actions.
                    causal_path_evs = self._make_causal_path_evs(
                        source_action=source_action,
                        target_action=target_action,
                        knowledge_graph=knowledge_graph)
                    
                    # Find two-step causal path evidence for the two actions.
                    multi_causal_path_evs = self._make_two_step_causal_path_evs(
                        source_action=source_action,
                        target_action=target_action,
                        knowledge_graph=knowledge_graph
                    )

                    # If there's no causal path evidence, stop here.
                    # If this is uncommented,
                    # this will prevent causal sequence hyps from being made
                    # using only continuity evidence.
                    # This is because with only continuity evidence, we can't
                    # determine what sequence the actions are in, so we can't
                    # assert their causal sequence. 
                    # ORDERING CONSTRAINT:
                    # If the ordering constraint is on, we assume actions flow
                    # from left-to-right in the images. So, we can allow
                    # causal sequence hyps using only continuity evidence. 
                    if not self.ordering_constraint_active:
                        if (not len(causal_path_evs) > 0
                            and not len(multi_causal_path_evs) > 0):
                            continue
                        # end if

                    #hyps_by_id_pair[id_pair] = list()
                    if not id_pair in hyps_by_id_pair:
                        hyps_by_id_pair[id_pair] = list()
                    else:
                        print('HypothesisGenerator._make_causal_sequence_hyps: Error, hyp id pair already has hyps when it shouldnt.')

                    # If there is any, make a hypothesis and add the evidence to
                    # it.
                    # Make a different hypothesis for forward evidence vs.
                    # backward evidence.
                    for causal_path_ev in causal_path_evs:
                        # ORDERING CONSTRAINT:
                        # If we're obeying image ordering, we only want causal
                        # paths whose direction is FORWARD, i.e. from source
                        # action to target action, because the source action
                        # is always going to be from the earlier image and
                        # the target action is always going to be from the
                        # later image. 
                        if self.ordering_constraint_active:
                            if causal_path_ev.direction == const.CausalFlowDirection.BACKWARD:
                                continue

                        # Look for an existing causal sequence hyp between
                        # the source and target actions in the same direction
                        # as the direction of this piece of causal path ev.
                        existing_hyp_found = False
                        for existing_hyp in hyps_by_id_pair[id_pair]:
                            # If we find one, add the causal path ev to that
                            # hypothesis.
                            if existing_hyp.direction == causal_path_ev.direction:
                                # There should only be one causal sequence hyp
                                # per direction.
                                # If another one is found, existing_hyp_found
                                # will already be true. This is an error.
                                if existing_hyp_found:
                                    print('hypothesis_generation._make_causal_sequence_hyps: ' +
                                            'Error! Multiple causal sequence hyps between the ' +
                                            'same two actions in the same direction!')
                                # end if
                                existing_hyp_found = True
                                existing_hyp.add_causal_path_ev(causal_path_ev)
                            # end if
                        # end for
                        # If no existing hypothesis in this causal path ev's
                        # direction was found, make a new one.
                        if not existing_hyp_found:
                            new_hyp = CausalSequenceHyp(source_action=source_action,
                                                        target_action=target_action)
                            new_hyp.add_causal_path_ev(causal_path_ev)
                            hyps_by_id_pair[id_pair].append(new_hyp)
                        # end if
                    # end for causal path ev. 

                    # Do the same for any multi causal path evidence.
                    for multi_causal_path_ev in multi_causal_path_evs:
                        # ORDERING CONSTRAINT:
                        # If we're obeying image ordering, we only want causal
                        # paths whose direction is FORWARD, i.e. from source
                        # action to target action, because the source action
                        # is always going to be from the earlier image and
                        # the target action is always going to be from the
                        # later image. 
                        if self.ordering_constraint_active:
                            if multi_causal_path_ev.direction == const.CausalFlowDirection.BACKWARD:
                                continue

                        # Look for an existing causal sequence hyp between
                        # the source and target actions in the same direction
                        # as the direction of this piece of causal path ev.
                        existing_hyp_found = False
                        for existing_hyp in hyps_by_id_pair[id_pair]:
                            # If we find one, add the causal path ev to that
                            # hypothesis.
                            if existing_hyp.direction == multi_causal_path_ev.direction:
                                # There should only be one causal sequence hyp
                                # per direction.
                                # If another one is found, existing_hyp_found
                                # will already be true. This is an error.
                                if existing_hyp_found:
                                    print('hypothesis_generation._make_causal_sequence_hyps: ' +
                                            'Error! Multiple causal sequence hyps between the ' +
                                            'same two actions in the same direction!')
                                # end if
                                existing_hyp_found = True
                                existing_hyp.add_multi_causal_path_ev(multi_causal_path_ev)
                            # end if
                        # end for
                        # If no existing hypothesis in this causal path ev's
                        # direction was found, make a new one.
                        if not existing_hyp_found:
                            new_hyp = CausalSequenceHyp(source_action=source_action,
                                                        target_action=target_action)
                            new_hyp.add_multi_causal_path_ev(multi_causal_path_ev)
                            hyps_by_id_pair[id_pair].append(new_hyp)
                        # end if
                    # end for multi causal path ev.
                        
                    # Find continuity evidence for the two actions.
                    same_object_hyps = [h for h in referential_hyps.values()
                                        if isinstance(h, SameObjectHyp)]
                    continuity_evs = self._make_continuity_evs(
                        source_action=source_action,
                        target_action=target_action,
                        same_object_hyps=same_object_hyps)
                    # If there is any, make and/or add the evidence to each
                    # causal sequence hyp between the two actions.
                    existing_hyp_found = False
                    for continuity_ev in continuity_evs:
                        for existing_hyp in hyps_by_id_pair[id_pair]:
                            existing_hyp.add_continuity_ev(continuity_ev)
                            existing_hyp_found = True
                    # end for
                    # ORDERING CONSTRAINT:
                    # If ordering constraint is active, we can have causal
                    # sequence hypotheses between actions that only have
                    # continuity evidence. We assume that the actions are
                    # ordered forward, from the lower index (earlier) image to
                    # the higher index (later) image.
                    if self.ordering_constraint_active:
                        if not existing_hyp_found:
                            new_hyp = CausalSequenceHyp(source_action=source_action,
                                                        target_action=target_action)
                            for continuity_ev in continuity_evs:
                                new_hyp.add_continuity_ev(continuity_ev)
                            # end for
                            new_hyp.direction = const.CausalFlowDirection.FORWARD
                            hyps_by_id_pair[id_pair].append(new_hyp)
                        # end if
                # end for target_action in target_actions
            # end for
        # end for

        # Add all hypotheses to the dictionary keyed by their IDs.
        for id_pair, hyps in hyps_by_id_pair.items():
            for hyp in hyps:
                causal_sequence_hyps[hyp.id] = hyp
            # end for
        # end for

        return causal_sequence_hyps
    # end _make_causal_sequence_hyps

    def _make_causal_path_evs(self, source_action: Action, 
                              target_action: Action,
                              knowledge_graph: KnowledgeGraph) -> list[CausalPathEv]:
        """
        Makes causal path evidence for a pair of actions.

        Returns the evidence made as a list of CausalPathEv objects.
        """
        causal_path_evs = list()
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
            causal_path_evs.append(causal_path_evidence)
        # end for causal_concept_edge in causal_concept_edges

        return causal_path_evs
    # end _make_causal_path_evs

    def _make_two_step_causal_path_evs(self, source_action: Action, 
        target_action: Action,
        knowledge_graph: KnowledgeGraph) -> list[MultiCausalPathEv]:
        """
        Makes two-step causal path evidence between a pair of actions.
        Two-step causal paths go from the source action to a middle
        concept, and from the middle concept to the target action
        (or target --> middle --> source if the flow is backwards).

        Makes a different piece of evidence for every middle concept node
        between source and target actions. If there are both forward and
        backward flowing paths going through a middle concept node, makes a 
        piece of evidence for forward flowing paths and a piece of evidence for 
        backward flowing paths. 

        Returns the evidence made as a list of MultiCausalPathEv objects.
        """
        # DEBUG: Disable multi causal paths.
        #return list()

        # Go through all the edges of concepts of source action.
        # Get all their middle cs nodes (the cs nodes of each edge that are NOT cs
        # nodes of the source action's concepts).

        # Result is a dictionary of the middle cs nodes and the edges that lead
        # to them.
        # Key: middle cs node's id.
        # Value: list of pairs of cs edges and the Concepts they're
        # connected to. 
        source_middle_cs_node_ids = self._get_middle_cs_node_ids(source_action)

        # Do the same for the target action.
        target_middle_cs_node_ids = self._get_middle_cs_node_ids(target_action)

        # Find pairs of source and target cs edges where the middle node is
        # the same and the causal flow direction is the same.
        # Store them in a list of dicts, with each dict having:
        # 'source_cs_edge': CommonSenseEdge
        # 'source_concept': Concept
        # 'target_cs_edge': CommonSenseEdge
        # 'target_concept': Concept
        # 'middle_cs_node_id': int
        # 'causal_flow_direction': const.CausalFlowDirection

        cs_edge_pairs = list()
        for middle_cs_node_id, source_concept_edge_pairs in source_middle_cs_node_ids.items():
            if not middle_cs_node_id in target_middle_cs_node_ids:
                continue
            # end if

            target_concept_edge_pairs = target_middle_cs_node_ids[middle_cs_node_id]

            # If they do, see if there are pairs of cs edges that flow in the 
            # same direction.
            # i.e. source cs node -> middle cs node -> target cs node
            # or target cs node -> middle cs node -> source cs node.

            # Determine the flow directions for every edge in every pair.
            # Make new lists for the source and target concept-cs_edge pairs
            # that adds the flow direction under a 'flow_direction' key.
            source_pairs_with_direction = list()
            target_pairs_with_direction = list()

            # For source edges, find flow directions relative to the middle cs
            # node, since we consider source action -> middle node to be FORWARD.
            for source_pair in source_concept_edge_pairs:
                concept = source_pair['concept']
                cs_edge = source_pair['cs_edge']
                flow_direction = self._get_cs_edge_flow_direction(
                    cs_edge, middle_cs_node_id
                )
                source_pairs_with_direction.append({'concept': concept,
                    'cs_edge': cs_edge, 'direction': flow_direction
                })
            # end for
            # For target edges, find flow directions relative to the target's
            # cs node, since we consider middle node -> target action to
            # be FORWARD.
            for target_pair in target_concept_edge_pairs:
                concept = target_pair['concept']
                cs_edge = target_pair['cs_edge']
                flow_direction = self._get_cs_edge_flow_direction(
                    cs_edge, cs_edge.get_other_node_id(middle_cs_node_id)
                )
                target_pairs_with_direction.append({'concept': concept,
                    'cs_edge': cs_edge, 'direction': flow_direction
                })
            # end for

            # Find any pairs of source and target cs edges that have the
            # same flow direction.
            for source_pair in source_pairs_with_direction:
                for target_pair in target_pairs_with_direction:
                    source_flow_direction = source_pair['direction']
                    target_flow_direction = target_pair['direction']
                    if source_flow_direction == target_flow_direction:
                        pair_dict = dict()
                        pair_dict['source_cs_edge'] = source_pair['cs_edge']
                        pair_dict['source_concept'] = source_pair['concept']
                        pair_dict['target_cs_edge'] = target_pair['cs_edge']
                        pair_dict['target_concept'] = target_pair['concept']
                        pair_dict['middle_cs_node_id'] = middle_cs_node_id
                        pair_dict['causal_flow_direction'] = source_flow_direction
                        cs_edge_pairs.append(pair_dict)
                    # end if
                # end for
            # end for
        # end for

        # We now have a list of dicts, with each dict consisting of:
        # 'source_cs_edge': CommonSenseEdge
        # 'source_concept': Concept
        # 'target_cs_edge': CommonSenseEdge
        # 'target_concept': Concept
        # 'middle_cs_node_id': int
        # 'causal_flow_direction': const.CausalFlowDirection
        # Every path that goes through the same middle node in the same
        # direction will be combined into a MultiPath.

        # Group the cs edge pairs by middle_cs_node_id and causal_flow_direction.
        # Key 1: middle_cs_node_id, int
        # Key 2: causal_flow_direction, const.CausalFlowDirection
        # Value: list of edge pair dicts, as in cs_edge_pairs.
        grouped_edge_pairs = dict()

        for edge_pair in cs_edge_pairs:
            middle_cs_node_id = edge_pair['middle_cs_node_id']
            direction = edge_pair['causal_flow_direction']
            if not middle_cs_node_id in grouped_edge_pairs:
                grouped_edge_pairs[middle_cs_node_id] = dict()
            if not direction in grouped_edge_pairs[middle_cs_node_id]:
                grouped_edge_pairs[middle_cs_node_id][direction] = list()
            grouped_edge_pairs[middle_cs_node_id][direction].append(edge_pair)
        # end for

        # Make a multi causal path ev for each middle cs node and each
        # direction. 
        multi_causal_path_evs = list()

        for middle_cs_node_id, direction_dicts in grouped_edge_pairs.items():
            # Get the CommonSenseNode for the middle cs node.
            middle_cs_node = knowledge_graph.get_commonsense_node(middle_cs_node_id)
            # Get a Concept for this middle cs node.
            middle_concept = knowledge_graph.get_or_make_concept(
                search_item=middle_cs_node,
                concept_type=ConceptType.ACTION
            )
            for direction, edge_pair_dicts in direction_dicts.items():
                # Make a path from source concepts to middle concept to
                # target concepts.

                # Gather all the edges between the source and middle concepts
                # and all the edges bewteen the middle and target concepts. 
                source_concepts = list()
                target_concepts = list()
                source_to_middle_edges = list()
                middle_to_target_edges = list()

                for pair_dict in edge_pair_dicts:
                    source_concept = pair_dict['source_concept']
                    if not source_concept in source_concepts:
                        source_concepts.append(source_concept)

                    source_cs_edge = pair_dict['source_cs_edge']
                    # We need the edge from the source concept to the middle concept
                    # which uses the source cs edge.
                    source_to_middle_edge = None
                    for edge in source_concept.get_edges_with(middle_concept):
                        if edge.commonsense_edge == source_cs_edge:
                            source_to_middle_edge = edge
                            break
                    # end for
                    if source_to_middle_edge is None:
                        print('HypothesisGenerator._make_two_step_causal_path_evs: ' +
                              'Error! No edge found from source to middle concepts ' +
                              f'for cs edge {source_cs_edge}')
                    # end if
                    if not source_to_middle_edge in source_to_middle_edges:
                        source_to_middle_edges.append(source_to_middle_edge)

                    target_concept = pair_dict['target_concept']
                    if not target_concept in target_concepts:
                        target_concepts.append(target_concept)

                    target_cs_edge = pair_dict['target_cs_edge']
                    
                    # We also need the edge from the middle concept to the
                    # target concept.
                    middle_to_target_edge = None
                    for edge in middle_concept.get_edges_with(target_concept):
                        if edge.commonsense_edge == target_cs_edge:
                            middle_to_target_edge = edge
                            break
                    # end for
                    if middle_to_target_edge is None:
                        print('HypothesisGenerator._make_two_step_causal_path_evs: ' +
                              'Error! No edge found from middle to source concepts ' +
                              f'for cs edge {target_cs_edge}')
                    # end if
                    if not middle_to_target_edge in middle_to_target_edges:
                        middle_to_target_edges.append(middle_to_target_edge)
                # end for pair_dict in edge_pair_dicts

                # Make a MultiPath using the source concepts, all the
                # source to middle edges, the middle concept, all the
                # middle to target edges, and the target concepts. 
                path = MultiPath()
                path.add_nodes(new_nodes=source_concepts)
                path.add_nodes(new_nodes=[middle_concept],
                               edges_from_last=source_to_middle_edges)
                path.add_nodes(new_nodes=target_concepts,
                              edges_from_last=middle_to_target_edges)

                ev = MultiCausalPathEv(
                    source_action=source_action,
                    target_action=target_action,
                    source_concepts=source_concepts,
                    target_concepts=target_concepts,
                    concept_path=path
                )
                multi_causal_path_evs.append(ev)
            # end for direction
        # end for middle_cs_node_id

        return multi_causal_path_evs
    # end _make_two_step_causal_path_evs

    def _get_middle_cs_node_ids(self, action: Action) -> dict[int, list[dict]]:
        """
        Gets the id of each commonsense node connected to commonsense 
        nodes that is part of the action's concepts, as well as the commonsense
        edge connecting it and the Concept that the commonsense edge is
        connected to. 

        Only counts causal commonsense edges. 

        Returns a dictionary:
        Key: commonsense_node_id, int
        Value: list of dicts, each dict consisting of:
            'concept': Concept
            'cs_edge': CommonSenseEdge
        """
        middle_cs_nodes_dict = dict()

        # Go through all the CommonSenseEdges of concepts in the action.
        # Get all their middle cs nodes (the cs nodes of each edge that are NOT cs
        # nodes of the source action's concepts).
        action_cs_nodes = action.get_commonsense_nodes()
        action_cs_node_ids = [cs_node.id for cs_node in action_cs_nodes]

        # For each concept, make a pair out of it and each of its cs edges
        # that has a causal relationship.
        concept_cs_edge_pairs = list()
        for concept in action.concepts:
            for cs_edge_id, cs_edge in concept.commonsense_edges.items():
                if cs_edge.get_relationship() in const.COHERENCE_TO_RELATIONSHIP['causal']:
                    concept_cs_edge_pairs.append({'concept': concept,
                                                  'cs_edge': cs_edge})
            # end for
        # end for


        for concept_cs_edge_pair in concept_cs_edge_pairs:
            cs_edge = concept_cs_edge_pair['cs_edge']
            # Figure out which cs node in this edge is part of the source
            # action's concepts and which one is the middle cs node.
            middle_cs_node_id = None
            if cs_edge.start_node_id in action_cs_node_ids:
                # Filter out the edge case where both cs nodes are part of the
                # action's concepts.
                if cs_edge.end_node_id in action_cs_node_ids:
                    #print('HypothesisGenerator._get_middle_cs_nodes: ' + 
                    #      'Both cs nodes in action. Skipping.')
                    continue
                # end if
                middle_cs_node_id = cs_edge.end_node_id
            # end if
            elif cs_edge.end_node_id in action_cs_node_ids:
                middle_cs_node_id = cs_edge.start_node_id
            else:
                print('HypothesisGenerator._get_middle_cs_nodes: ' + 
                      'Neither cs node in action. Error!')
                continue
            # end else
            if not middle_cs_node_id in middle_cs_nodes_dict:
                middle_cs_nodes_dict[middle_cs_node_id] = list()
            # end if
            middle_cs_nodes_dict[middle_cs_node_id].append(concept_cs_edge_pair)
        # end for

        return middle_cs_nodes_dict
    # end _get_middle_cs_node_ids

    def _get_cs_edge_flow_direction(self, 
        commonsense_edge: CommonSenseEdge,
        commonsense_node_id: int) -> const.CausalFlowDirection:
        """
        Returns the causal flow direction of an edge towards one of its
        CommonSenseNode endpoints, specified by id. 

        e.g. if the CommonSenseNode id is the end node of the edge,
        FORWARD would be from the start node to the end node and
        BACKWARD would be from the end node to the start node.

        If the CommonSenseNode id is the start node of the edge,
        FORWARD would be from the end to the start and
        BACKWARD would be from the start to the end.
        """
        # Start with getting the flow direction of the relationship. 
        # This is the direction from start node to end node. 
        flow_direction = const.CAUSAL_RELATIONSHIP_DIRECTION[
            commonsense_edge.get_relationship()]
        # Flip it if the specified cs node is at the start of the edge.
        if commonsense_node_id == commonsense_edge.start_node_id:
            if flow_direction == const.CausalFlowDirection.FORWARD:
                flow_direction = const.CausalFlowDirection.BACKWARD
            elif flow_direction == const.CausalFlowDirection.BACKWARD:
                flow_direction = const.CausalFlowDirection.FORWARD
            else:
                print('HypothesisGenerator._get_cs_edge_flow_direction: ' + 
                      'Error! cs_edge flow direction was initially not forward or backward!'
                      + f' Instead, it was {flow_direction}.')
            # end else
        # end if
        elif not commonsense_node_id == commonsense_edge.end_node_id:
            print('HypothesisGenerator._get_cs_edge_flow_direction: ' +
                  f'Error! cs node id {commonsense_node_id} is neither ' +
                  f'start or end node of edge {commonsense_edge}.')
        return flow_direction
    # _get_cs_edge_flow_direction

    def _make_continuity_evs(self, source_action: Action, 
                             target_action: Action,
                             same_object_hyps: list[SameObjectHyp]) -> list:
        """
        Makes continuity evidence between two actions.

        Returns a list of ContinuityEv objects.
        """
        continuity_evs = list()

        # See if any of the source action's connected Objects have same object
        # hypotheses with any of the target action's connected Objects.
        # For each pair of objects that do, make a piece of continuity evidence. 
        for source_object in source_action.objects.values():
            for target_object in target_action.objects.values():
                joining_hyps = [h for h in same_object_hyps
                                if h.has_object(source_object)
                                and h.has_object(target_object)]
                for joining_hyp in joining_hyps:
                    continuity_ev = ContinuityEv(
                        source_action=source_action,
                        target_action=target_action,
                        source_object=source_object,
                        target_object=target_object,
                        joining_hyp=joining_hyp)
                    continuity_evs.append(continuity_ev)
                # end for
            # end for
        # end for

        return continuity_evs
    # end _make_continuity_evs

# end class HypothesisGenerator