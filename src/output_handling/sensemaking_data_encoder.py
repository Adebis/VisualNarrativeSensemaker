import json

from constants import CausalFlowDirection
from parameters import ParameterSet
from input_handling.scene_graph_data import (Image, BoundingBox, 
                                             SceneGraphObject, 
                                             SceneGraphRelationship)
from knowledge_graph.graph import KnowledgeGraph
from knowledge_graph.items import (Node, Concept, Instance, Object, Action, 
                                   Edge, ConceptType, EdgeRelationship)
from commonsense.commonsense_data import (CommonSenseNode, CommonSenseEdge, 
                                          FrameNetType, Synset)
from hypothesis.evidence import (Evidence, VisualSimEv, AttributeSimEv, 
                                 CausalPathEv, ContinuityEv, MultiCausalPathEv)
from hypothesis.hypothesis import (Hypothesis,
                                   SameObjectHyp,
                                   CausalSequenceHyp,
                                   HypothesisSet,
                                   CausalHypChain)
from hypothesis.contradiction import (Contradiction, 
                                      HypothesisCon,
                                      HypothesisSetCon,
                                      InImageTransCon, 
                                      TweenImageTransCon,
                                      CausalHypFlowCon,
                                      CausalChainFlowCon,
                                      CausalCycleCon)
from hypothesis.hypothesis_evaluator import (Solution,
                                             SolutionSet,
                                             Rejection,
                                             HypConRejection,
                                             HypSetConRejection,
                                             CausalCycleRejection)
from knowledge_graph.path import (Step, MultiStep, Path, MultiPath)

class SensemakingDataEncoder(json.JSONEncoder):
    """
    JSON encoder for custom classes and data involved in sensemaking.
    """

    # Debug
    _current_object_encoded = None
    _last_object_encoded = None
    def default(self, o):
        """
        Checks the type of the object. If it's of a type that this encoder
        handles, returns a serializable dictionary version of if.

        Otherwise, calls the default encoder on it. 
        """
        self._last_object_encoded = self._current_object_encoded
        self._current_object_encoded = o
        try:
            if isinstance(o, KnowledgeGraph):
                return self._encode_knowledge_graph(o)
            elif isinstance(o, CommonSenseNode):
                return self._encode_commonsense_node(o)
            elif isinstance(o, CommonSenseEdge):
                return self._encode_commonsense_edge(o)
            elif isinstance(o, Concept):
                return self._encode_concept(o)
            elif isinstance(o, Object):
                return self._encode_object(o)
            elif isinstance(o, Action):
                return self._encode_action(o)
            elif isinstance(o, Edge):
                return self._encode_edge(o)
            elif isinstance(o, Image):
                return self._encode_image(o)
            elif isinstance(o, SceneGraphObject):
                return self._encode_scene_graph_object(o)
            elif isinstance(o, SceneGraphRelationship):
                return self._encode_scene_graph_relationship(o)
            elif isinstance(o, Step):
                return self._encode_step(o)
            elif isinstance(o, MultiStep):
                return self._encode_multi_step(o)
            elif isinstance(o, Path):
                return self._encode_path(o)
            elif isinstance(o, MultiPath):
                return self._encode_multi_path(o)
            elif isinstance(o, VisualSimEv):
                return self._encode_visual_sim_ev(o)
            elif isinstance(o, AttributeSimEv):
                return self._encode_attribute_sim_ev(o)
            elif isinstance(o, CausalPathEv):
                return self._encode_causal_path_ev(o)
            elif isinstance(o, MultiCausalPathEv):
                return self._encode_multi_causal_path_ev(o)
            elif isinstance(o, ContinuityEv):
                return self._encode_continuity_ev(o)
            elif isinstance(o, SameObjectHyp):
                return self._encode_same_object_hyp(o)
            elif isinstance(o, CausalSequenceHyp):
                return self._encode_causal_sequence_hyp(o)
            elif isinstance(o, HypothesisSet):
                return self._encode_hypothesis_set(o)
            elif isinstance(o, CausalHypChain):
                return self._encode_causal_hyp_chain(o)
            elif isinstance(o, InImageTransCon):
                return self._encode_in_image_trans_con(o)
            elif isinstance(o, TweenImageTransCon):
                return self._encode_tween_image_trans_con(o)
            elif isinstance(o, CausalHypFlowCon):
                return self._encode_causal_hyp_flow_con(o)
            elif isinstance(o, CausalChainFlowCon):
                return self._encode_causal_chain_flow_con(o)
            elif isinstance(o, CausalCycleCon):
                return self._encode_causal_cycle_con(o)
            elif isinstance(o, HypConRejection):
                return self._encode_hyp_con_rejection(o)
            elif isinstance(o, HypSetConRejection):
                return self._encode_hyp_set_con_rejection(o)
            elif isinstance(o, CausalCycleRejection):
                return self._encode_causal_cycle_rejection(o)
            elif isinstance(o, Solution):
                return self._encode_solution(o)
            elif isinstance(o, SolutionSet):
                return self._encode_solution_set(o)
            # Some custom dataclasses can be turned into their dictionary forms and 
            # returned.
            elif isinstance(o, (Synset, BoundingBox, ParameterSet)):
                return o.__dict__
            # Custom enumerators can be cast into strings.
            elif isinstance(o, (FrameNetType, ConceptType, EdgeRelationship, 
                                CausalFlowDirection)):
                return str(o)
            # end elif
            return json.JSONEncoder.default(self, o)
        except Exception as e:
            print(f'SensemakingDataEncoder.default: Error: {e}')
    # end default

    def _encode_knowledge_graph(self, knowledge_graph: KnowledgeGraph):
        """
        Encodes a KnowledgeGraph into a json serializable dictionary.

        Has lists of all CommonSenseNodes, CommonSenseEdges, Images, Nodes, 
        and Edges.
        """
        kg_dict = dict()
        # First, encode all commonsense_nodes into a top-level dictionaries. 
        # Any Concept that has these nodes will reference them by their IDs. 
        # Each CommonSenseNode is encoded with a list of the ids of the 
        # CommonSenseEdges incident on them. 
        commonsense_nodes = knowledge_graph.get_commonsense_nodes()
        # Get all of the commonsense_edges as well.
        # These are commonsense_edges that are associated with edges in
        # the knowledge graph.
        #commonsense_edges = knowledge_graph.get_commonsense_edges()
        # There are a lot of theses...
        commonsense_edges = list()

        kg_dict['commonsense_nodes'] = commonsense_nodes
        kg_dict['commonsense_edges'] = commonsense_edges
        # Encode all the images.
        kg_dict['images'] = list(knowledge_graph.images.values())
        # Encode all Nodes
        #kg_dict['nodes'] = list(knowledge_graph.nodes.values())
        kg_dict['concepts'] = list(knowledge_graph.concepts.values())
        kg_dict['objects'] = list(knowledge_graph.objects.values())
        kg_dict['actions'] = list(knowledge_graph.actions.values())
        # Encode all edges
        kg_dict['edges'] = list(knowledge_graph.edges.values())
        return kg_dict
    # end _encode_knowledge_graph

    def _encode_image(self, image: Image):
        """
        Encodes an Image into a json serializable dict.

        Ignores the matrix attribute. Whatever loads the image can find the
        image file's data itself using the file_path.
        """
        return {'id': image.id,
                'index': image.index,
                'file_path': image.file_path}
    # end _encode_image

    def _encode_scene_graph_object(self, scene_graph_object: SceneGraphObject):
        """
        Encodes a SceneGraphObject into a json serializable dict.

        image is encoded as the image's id, which can be looked up in the
        knowledge graph's dictionary of images.
        """
        return {'names': scene_graph_object.names,
                'synsets': scene_graph_object.synsets,
                'object_id': scene_graph_object.object_id,
                'bounding_box': scene_graph_object.bounding_box,
                'image_id': scene_graph_object.image.id,
                'attributes': scene_graph_object.attributes}
    # end _encode_scene_graph_object

    def _encode_scene_graph_relationship(self, 
                                         relationship: SceneGraphRelationship):
        """
        Encodes a SceneGraphRelationship into a json serializable dict.

        image is encoded as the image's id, which can ben looked up in the
        knowledge graph's dictionary of images.
        """
        return {'predicate': relationship.predicate,
                'synsets': relationship.synsets,
                'relationship_id': relationship.relationship_id,
                'object_id': relationship.object_id,
                'subject_id': relationship.subject_id,
                'image_id': relationship.image.id}
    # end _encode_scene_graph_relationship

    def _encode_commonsense_node(self, node: CommonSenseNode):
        """
        Encodes a CommonSenseNode into a json serializable dict.

        CommonSenseEdges incident on this CommonSenseNode are encoded as a list 
        of CommonSenseEdge ids. These can be looked up in the 
        commonsense_knowledge database.
        """
        return {'id': node.id,
                'uri': node.uri,
                'labels': node.labels,
                'edge_ids': [edge_id for edge_id in node.edge_ids]}
    # end _encode_commonsense_node

    def _encode_commonsense_edge(self, edge: CommonSenseEdge):
        """
        Encodes a CommonSenseEdge into a json serializable dict.
        
        CommonSenseNodes incident on this CommonSenseEdge are encoded as 
        start and end node ids. These can be looked up in the 
        commonsense_knowledge database.
        """
        return {'id': edge.id,
                'uri': edge.uri,
                'labels': edge.labels,
                'relation': edge.relation,
                'start_node_id': edge.start_node_id,
                'end_node_id': edge.end_node_id,
                'start_node_uri': edge.start_node_uri,
                'end_node_uri': edge.end_node_uri,
                'weight': edge.weight,
                'dimension': edge.dimension if edge.dimension is not None else "",
                'source': edge.source if edge.source is not None else "",
                'sentence': edge.sentence if edge.sentence is not None else ""}
    # end _encode_commonsense_edge

    def _encode_node(self, node: Node):
        """
        Encodes a Node into a json serializable dictionary.

        Adds a 'type' field with the string name of the node's type.

        Edges are encoded as a list of edge ids. These can be looked up in
        the KnowledgeGraph's edges dictionary.
        """
        return {'id': node.id,
                'label': node.label,
                'name': node.name,
                'edge_ids': [edge_id for edge_id in node.edges.keys()],
                'hypothesized': node.hypothesized,
                'type': type(node).__name__}
    # end _encode_node

    def _encode_concept(self, concept: Concept):
        """
        Encodes a Concept node into a json serializable dictionary.
        commonsense_nodes is encoded as a list of CommonSenseNode ids. 
        These can be looked up in the KnowledgeGraph's commonsense_nodes
        dictionary. 
        """
        # First, encode it as a Node.
        node_dict = self._encode_node(concept)
        # Then, add the extra information from it being a Concept.
        node_dict.update({'concept_type': concept.concept_type,
                          'synset': concept.synset,
                          'commonsense_node_ids': [cs_node_id for cs_node_id in 
                                                   concept.commonsense_nodes.keys()],
                          'polarity_scores': concept.polarity_scores,
                          'sentiment': concept.sentiment})
        return node_dict
    # end _encode_concept

    def _encode_instance(self, instance: Instance):
        """
        Encodes an Instance node into a json serializable dictionary.

        concepts is encoded as a list of Node ids. These can be looked up in
        the knowledge graph's dictionary of nodes.

        images is encoded as a list of image ids. These can be looked up in
        the knowledge graph's dictionary of images.
        """
        # First, encode it as a Node.
        node_dict = self._encode_node(instance)
        # Then, add extra information from it being an Instance.
        node_dict.update({'concept_ids': [concept.id for concept 
                                          in instance.concepts],
                          'image_ids': [image_id for image_id 
                                       in instance.images.keys()],
                          'focal_score': instance.focal_score})
        return node_dict
    # end _encode_instance

    def _encode_object(self, object_node: Object):
        """
        Encodes an Object node into a json serializable dictionary.

        Ignores the appearance attribute. The Object's appearance can be
        re-calculated from its smallest bounding box and its image's file.
        """
        # First, encode it as an Instance.
        node_dict = self._encode_instance(object_node)
        # Then, add extra information from it being an Object.
        node_dict.update({'scene_graph_objects': object_node.scene_graph_objects,
                          'attributes': object_node.attributes})
        return node_dict
    # end _encode_object

    def _encode_action(self, action: Action):
        """
        Encodes an Action node into a json serializable dictionary.

        subject and object are encoded as the ids of Object nodes. 

        Have to call object 'obj' because object is a reserved term.
        """
        # First, encode it as an Instance.
        node_dict = self._encode_instance(action)
        # Then, add extra information from it being an Action.
        node_dict.update({'subject_id': action.subject.id,
                          'obj_id': (-1 if action.object is None 
                                     else action.object.id),
                          'scene_graph_rel': action.scene_graph_rel})
        return node_dict
    # end _encode_action

    def _encode_edge(self, edge: Edge):
        """
        Encodes an Edge into a json serializable dictionary.

        source and target are encoded as Node ids.

        commonsense_edge is encoded as the CommonSenseEdge's id. 
        """
        return {'id': edge.id,
                'source_id': edge.source.id,
                'target_id': edge.target.id,
                'relationship': edge.relationship,
                'weight': edge.weight,
                'commonsense_edge_id': (-1 if edge.commonsense_edge is None 
                                        else edge.commonsense_edge.id)}
    # end _encode_edge

    def _encode_step(self, step: Step):
        """
        Encodes a single Step in a Path into a json serializable dictionary.
        node, next_step, next_edge, previous_step, and previous_edge are
        encoded as those objects' ids.
        """
        # Previous and next steps and edges can be None.
        # If so, set their ids to -1.
        next_step_id = -1
        if step.next_step is not None:
            next_step_id = step.next_step.id
        next_edge_id = -1
        if step.next_edge is not None:
            next_edge_id = step.next_edge.id
        previous_step_id = -1
        if step.previous_step is not None:
            previous_step_id = step.previous_step.id
        previous_edge_id = -1
        if step.previous_edge is not None:
            previous_edge_id = step.previous_edge.id
        return {'id': step.id,
                'node_id': step.node.id,
                'next_step_id': next_step_id,
                'next_edge_id': next_edge_id,
                'previous_step_id': previous_step_id,
                'previous_edge_id': previous_edge_id}
    # end _encode_step

    def _encode_multi_step(self, multi_step: MultiStep):
        """
        Encodes a single multi-step in a multi-path into a json serializable
        dict.

        nodes is encoded as a list of node_ids.
        next_step is encoded as the next_step_id.
        previous_step is encoded as the previous_step_id.
        next_edges is encoded as a list of next_edge_ids.
        previous_edges is encoded as a list of previous_edge_ids.
        """
        node_ids = [node.id for node in multi_step.nodes]

        # Previous and next steps and edges can be None.
        next_step_id = -1
        if multi_step.next_step is not None:
            next_step_id = multi_step.next_step.id
        next_edge_ids = [edge.id for edge in multi_step.next_edges]

        previous_step_id = -1
        if multi_step.previous_step is not None:
            previous_step_id = multi_step.previous_step.id
        previous_edge_ids = [edge.id for edge in multi_step.previous_edges]

        return {'id': multi_step.id,
                'node_ids': node_ids,
                'next_step_id': next_step_id,
                'next_edge_ids': next_edge_ids,
                'previous_step_id': previous_step_id,
                'previous_edge_ids': previous_edge_ids}
    # end _encode_multi_step

    def _encode_path(self, path: Path):
        """
        Encodes a Path into a json serializable dictionary.
        The list of steps is included as-is to be encoded as Step objects later.
        """
        return {'id': path.id,
                'steps': path.steps}
    # end _encode_path

    def _encode_multi_path(self, multi_path: MultiPath):
        """
        Encodes a MultiPath into a json serializable dictionary.
        The list of multi-steps is included as-is to be encoded as MultiStep
        objects later.
        """
        return {'id': multi_path.id,
                'steps': multi_path.steps}
    # end _encode_multi_path

    def _encode_evidence(self, evidence: Evidence):
        """
        Encodes a piece of Evidence into a json serializable dictionary.

        Adds a 'type' field with a string representation of the Evidence's type.
        """
        return {'id': evidence.id,
                'score': evidence.score,
                'type': type(evidence).__name__}
    # end _encode_evidence

    def _encode_visual_sim_ev(self, visual_sim_ev: VisualSimEv):
        """
        Encodes a piece of VisualSimEv into a json serializable
        dict.

        object_1 and object_2 are encoded as Node ids.
        """
        evidence_dict = self._encode_evidence(visual_sim_ev)
        evidence_dict.update({'object_1_id': visual_sim_ev.object_1.id,
                              'object_2_id': visual_sim_ev.object_2.id})
        return evidence_dict
    # end _encode_visual_sim_ev

    def _encode_attribute_sim_ev(self,
                                 attribute_sim_ev: AttributeSimEv):
        """
        Encodes a piece of AttributeSimEv into a json serializable
        dict.

        object_1 and object_2 are encoded as Node ids.
        """
        evidence_dict = self._encode_evidence(attribute_sim_ev)
        evidence_dict.update({'object_1_id': attribute_sim_ev.object_1.id,
                              'object_2_id': attribute_sim_ev.object_2.id})
        return evidence_dict
    # end _encode_attribute_sim_ev

    def _encode_causal_path_ev(self,
                               causal_path_ev: CausalPathEv):
        """
        Encodes a piece of CausalPathEv into a json serializable dict.

        source_action and target_action are encoded as Node ids.
        source_concept and target_concept are encoded as Node ids. 
        concept_path is included as-is to be encoded as a Path later.
        direction is included as-is.
        """
        evidence_dict = self._encode_evidence(causal_path_ev)
        evidence_dict.update({'source_action_id': causal_path_ev.source_action.id,
                              'target_action_id': causal_path_ev.target_action.id,
                              'source_concept_id': causal_path_ev.source_concept.id,
                              'target_concept_id': causal_path_ev.target_concept.id,
                              'concept_path': causal_path_ev.concept_path,
                              'direction': causal_path_ev.direction})
        return evidence_dict
    # end _encode_causal_path_ev

    def _encode_multi_causal_path_ev(self,
                                     multi_causal_path_ev: MultiCausalPathEv):
        """
        Encodes a piece of MultiCausalPathEv into a json serializable dict.

        source_action and target_action are encoded as Node ids.
        source_concepts and target_concepts are encoded as lists of Node ids. 
        concept_path is included as-is to be encoded as a Path later.
        direction is included as-is.
        """
        evidence_dict = self._encode_evidence(multi_causal_path_ev)
        source_concept_ids = [c.id for c in multi_causal_path_ev.source_concepts]
        target_concept_ids = [c.id for c in multi_causal_path_ev.target_concepts]
        evidence_dict.update({'source_action_id': multi_causal_path_ev.source_action.id,
                              'target_action_id': multi_causal_path_ev.target_action.id,
                              'source_concept_ids': source_concept_ids,
                              'target_concept_ids': target_concept_ids,
                              'concept_path': multi_causal_path_ev.concept_path,
                              'direction': multi_causal_path_ev.direction})
        return evidence_dict
    # end _encode_multi_causal_path_ev

    def _encode_continuity_ev(self,
                              continuity_ev: ContinuityEv):
        """
        Encodes a piece of ContinuityEv into a json serializable dict.

        source_action is encoded as its id.
        target_action is encoded as its id.
        source_object is encoded as its id.
        target_object is encoded as its id.
        joining_hyp is encoded as its id.
        """
        evidence_dict = self._encode_evidence(continuity_ev)
        evidence_dict.update({'source_action_id': continuity_ev.source_action.id,
                              'target_action_id': continuity_ev.target_action.id,
                              'source_object_id': continuity_ev.source_object.id,
                              'target_object_id': continuity_ev.target_object.id,
                              'joining_hyp_id': continuity_ev.joining_hyp.id})
        return evidence_dict
    # end _encode_continuity_ev

    def _encode_hypothesis(self, hypothesis: Hypothesis):
        """
        Encodes a Hypothesis into a json serializable dict.

        Adds a 'type' field with a string of the Hypothesis' class type.

        premises is encoded as a list of Hypothesis ids.
        """
        return {'id': hypothesis.id,
                'name': hypothesis.name,
                'premise_ids': [h_id for h_id in hypothesis.premises.keys()],
                'type': type(hypothesis).__name__}
    # end _encode_hypothesis

    def _encode_same_object_hyp(self, 
                                    same_object_hyp: SameObjectHyp):
        """
        Encodes an SameObjectHyp into a json serializable dict.

        object_1 and object_2 are encoded as their Node ids.

        edge is a hypothesized Edge which does not exist in the knowledge graph, 
        so the whole Edge is encoded in the hypothesis.
        """
        h_dict = self._encode_hypothesis(same_object_hyp)
        h_dict.update({'object_1_id': same_object_hyp.object_1.id,
                       'object_2_id': same_object_hyp.object_2.id,
                       'edge': same_object_hyp.edge,
                       'visual_sim_ev': same_object_hyp.visual_sim_ev,
                       'attribute_sim_ev': same_object_hyp.attribute_sim_ev})
        return h_dict
    # end _encode_same_object_hyp

    def _encode_causal_sequence_hyp(self, causal_sequence_hyp: CausalSequenceHyp):
        """
        Encodes a CausalSequenceHyp into a json serializable dict.

        source_action and target_action encoded as their Node ids.
        edge (leads-to) added as-is. Can't encode by ID because it's not a part
            of the knowledge graph. 
        causal_path_evs added as-is so they can be encoded later.
        multi_causal_path_evs added as-is so they can be encoded later.s
        continuity_evs added as-is so they can be encoded later.
        direction included as-is.
        """
        h_dict = self._encode_hypothesis(causal_sequence_hyp)
        h_dict.update({
            'source_action_id': causal_sequence_hyp.source_action.id,
            'target_action_id': causal_sequence_hyp.target_action.id,
            'edge': causal_sequence_hyp.edge,
            'causal_path_evs': causal_sequence_hyp.causal_path_evs,
            'multi_causal_path_evs': causal_sequence_hyp.multi_causal_path_evs,
            'continuity_evs': causal_sequence_hyp.continuity_evs,
            'direction': causal_sequence_hyp.direction,
            'affect_curve_scores': [{'pset_id': s[0],
                                    'score': s[1]}
                                    for s in causal_sequence_hyp.affect_curve_scores.items()]
        })
        return h_dict
    # end _encode_causal_sequence_hyp

    def _encode_hypothesis_set(self, hyp_set: HypothesisSet):
        """
        Encodes a HypothesisSet into a json serializable dict.

        hypotheses is encoded as a list of hypothesis ids.
        """
        return {'id': hyp_set.id,
                'hypothesis_ids': list(hyp_set.hypotheses.keys()),
                'is_all_or_ex': hyp_set.is_all_or_ex}
    # end _encode_hypothesis_set

    def _encode_causal_hyp_chain(self, causal_hyp_chain: CausalHypChain):
        """
        Encodes a CausalHypChain into a json serializable dict.
        """
        super_dict = self._encode_hypothesis_set(causal_hyp_chain)
        super_dict.update({'hyp_id_sequence': causal_hyp_chain.hyp_id_sequence})

        return super_dict
    # end _encode_causal_hyp_chain

    def _encode_contradiction(self, contradiction: Contradiction):
        """
        Encodes a Contradiction into a json serializable dict.

        explanation is encoded as itself, a string.
        Adds a type field with a string of the contradiction's type.
        """
        return {'id': contradiction.id,
                'explanation': contradiction.explanation,
                'type': type(contradiction).__name__}
    # end _encode_contradiction

    def _encode_hypothesis_con(self, hypothesis_con: HypothesisCon):
        """
        Encodes a HypothesisCon into a json serializable dict.
        
        hypothesis_1 and hypothesis_2 are encoded as their ids.
        """
        super_dict = self._encode_contradiction(contradiction=hypothesis_con)
        super_dict.update({'hypothesis_1_id': hypothesis_con.hypothesis_1.id,
                           'hypothesis_2_id': hypothesis_con.hypothesis_2.id})
        return super_dict
    # end _encode_hypothesis_con

    def _encode_hypothesis_set_con(self, hypothesis_set_con: HypothesisSetCon):
        """
        Encodes a HypothesisSetCon into a json serializable dict.

        hyp_set_1 and hyp_set_2 are encoded as their ids.
        """
        super_dict = self._encode_contradiction(contradiction=hypothesis_set_con)
        super_dict.update({'hyp_set_1_id': hypothesis_set_con.hyp_set_1.id,
                           'hyp_set_2_id': hypothesis_set_con.hyp_set_2.id})
        return super_dict
    # end _encode_hypothesis_set_con

    def _encode_in_image_trans_con(self, in_image_trans_con: InImageTransCon):
        """
        Encodes an InImageTransCon into a json serializable dict.

        obj_1 is encoded as its node id.
        obj_2 is encoded as its node id.
        shared_obj is encoded as its node id.
        """
        con_dict = self._encode_hypothesis_con(hypothesis_con=in_image_trans_con)
        con_dict.update({'obj_1_id': in_image_trans_con.obj_1.id,
                         'obj_2_id': in_image_trans_con.obj_2.id,
                         'shared_obj_id': in_image_trans_con.shared_obj.id})
        return con_dict
    # end _encode_in_image_trans_con

    def _encode_tween_image_trans_con(self, tween_image_trans_con: TweenImageTransCon):
        """
        Encodes a TweenImageTransCon into a json serializable dict.

        obj_1 is encoded as its node id.
        obj_2 is encoded as its node id.
        shared_obj is encoded as its node id.
        joining_hyp is encoded as its Hypothesis id.
        hyp_set_id is encoded as itself.
        """
        con_dict = self._encode_hypothesis_con(hypothesis_con=tween_image_trans_con)
        con_dict.update({'obj_1_id': tween_image_trans_con.obj_1.id,
                         'obj_2_id': tween_image_trans_con.obj_2.id,
                         'shared_obj_id': tween_image_trans_con.shared_obj.id,
                         'joining_hyp_id': tween_image_trans_con.joining_hyp.id,
                         'hyp_set_id': tween_image_trans_con.hyp_set_id})
        return con_dict
    # end _encode_tween_image_trans_con

    def _encode_causal_hyp_flow_con(self, causal_hyp_flow_con: CausalHypFlowCon):
        """
        Encodes a CausalHypFlowCon into a json serializable dict.

        image_1 is encoded as its id.
        image_2 is encoded as its id.
        """
        super_dict = self._encode_hypothesis_con(causal_hyp_flow_con)
        super_dict.update({'image_1_id': causal_hyp_flow_con.image_1.id,
                           'image_2_id': causal_hyp_flow_con.image_2.id})
        return super_dict
    # end _encode_causal_hyp_flow_con

    def _encode_causal_chain_flow_con(self, causal_chain_flow_con: CausalChainFlowCon):
        """
        Encodes a CausalChainFlowCon into a json serializable dict.

        image_1 is encoded as its id.
        image_2 is encoded as its id.
        """
        super_dict = self._encode_hypothesis_set_con(causal_chain_flow_con)
        super_dict.update({'image_1_id': causal_chain_flow_con.image_1.id,
                           'image_2_id': causal_chain_flow_con.image_2.id})
        return super_dict
    # end _encode_causal_flow_con

    def _encode_causal_cycle_con(self, causal_cycle_con: CausalCycleCon):
        '''
        Encodes a CausalCycleCon into a json serializable dict.

        image is encoded as its id.
        causal_chain is encoded as its id.
        subsets is encoded as a list of their ids.
        '''
        super_dict = self._encode_contradiction(causal_cycle_con)
        super_dict.update({'image_id': causal_cycle_con.image.id,
                           'causal_chain_id': causal_cycle_con.causal_chain.id,
                           'subset_ids': [h.id for h in causal_cycle_con.subsets]})
        return super_dict
    # end _encode_causal_cycle_con

    def _encode_rejection(self, rejection: Rejection):
        """
        Encodes a Rejection into a json serializable dict.

        rejected_hyp is encoded as its Hypothesis id.
        explanation is encoded as itself.
        Adds a type field with a string of the rejection's type.
        """
        return{'rejected_hyp_id': rejection.rejected_hyp.id,
               'explanation': rejection.explanation,
               'type': type(rejection).__name__}
    # end _encode_rejection

    def _encode_hyp_con_rejection(self, 
                                  hyp_con_rejection: HypConRejection):
        """
        Encodes a HypConRejection into a json serializable dict.

        contradicting_hyp is encoded as its Hypothesis id.
        contradiction is encoded as its id.
        """
        super_dict = self._encode_rejection(hyp_con_rejection)
        super_dict.update({'contradicting_hyp_id': hyp_con_rejection.contradicting_hyp.id,
                           'contradiction_id': hyp_con_rejection.contradiction.id})
        return super_dict
    # end _encode_hyp_con_rejection

    def _encode_hyp_set_con_rejection(self, 
                                      hyp_set_con_rejection: HypSetConRejection):
        """
        Encodes a HypSetConRejection into a json serializable dict.

        contradicting_hyp_set is encoded as its id.
        contradiction is encoded as its id.
        """
        super_dict = self._encode_rejection(hyp_set_con_rejection)
        super_dict.update({'contradicting_hyp_set_id': hyp_set_con_rejection.contradicting_hyp_set.id,
                           'contradiction_id': hyp_set_con_rejection.contradiction.id})
        return super_dict
    # end _encode_hyp_con_rejection

    def _encode_causal_cycle_rejection(self, causal_cycle_rejection: CausalCycleRejection):
        '''
        Encodes a CausalCycleRejection into a json serializable dict.

        contradicting_hyps is encoded as a list of their ids.
        contradiction is encoded as its id.
        '''
        super_dict = self._encode_rejection(causal_cycle_rejection)
        super_dict.update({'contradicting_hyp_ids': [h.id for h in causal_cycle_rejection.contradicting_hyps],
                           'contradiction_id': causal_cycle_rejection.contradiction.id})
        return super_dict
    # end _encode_causal_cycle_rejection

    def _encode_solution(self, solution: Solution):
        """
        Encodes a Solution into a json serializable dict.

        parameters is encoded as the parameter set's id.

        accepted_hypotheses is encoded as a list of Hypothesis ids.

        accepted_hyp_sets is encoded as a list of HypothesisSet ids.

        energy is encoded as itself, a float.

        rejections are encoded as-is so they can be encoded later.
        """
        # Encode rejections into separate lists according to their type.
        rejections_output_dict = dict()
        rejections_output_dict['hyp_con_rejections'] = [r for r in solution.rejections
                                                        if isinstance(r, HypConRejection)]
        rejections_output_dict['hyp_set_con_rejections'] = [r for r in solution.rejections
                                                            if isinstance(r, HypSetConRejection)]
        rejections_output_dict['causal_cycle_rejections'] = [r for r in solution.rejections
                                                             if isinstance(r, CausalCycleRejection)]

        return {'id': solution.id,
                'parameter_set_id': solution.parameters.id,
                'accepted_hypothesis_ids': [h_id for h_id in 
                                            solution.accepted_hypotheses.keys()],
                'accepted_hyp_set_ids': [h_id for h_id in 
                                         solution.accepted_hyp_sets.keys()],
                'energy': solution.energy,
                'rejections': rejections_output_dict}
    # end _encode_solution

    def _encode_solution_set(self, solution_set: SolutionSet):
        """
        Encodes a SolutionSet into a json serializable dict.

        parameters is encoded as the parameter set's id.

        The keys for paired_scores are encoded as a dictionary with a list
        for the id pair and a float for the score.

        id_triplets are encoded as a dictionary with an int for the triplet id,
        and a list of ints for the ids in the triplet.

        Contradictions are encoded as-is so they can be encoded later.

        Solutions are encoded as-is so they can be encoded later.
        """

        # Encode individual scores as a list of dictionaries.
        individual_scores_output_list = [{'id': id, 'score': solution_set.individual_scores[id]} 
                                         for id in solution_set.individual_scores.keys()]
        paired_scores_output_list = [{'id_pair': list(id_pair), 'score': solution_set.paired_scores[id_pair]} 
                                     for id_pair in solution_set.paired_scores.keys()]
        # Encode hypothesis sets into separate lists according to their type.
        hyp_sets_output_dict = dict()
        hyp_sets_output_dict['causal_hyp_chains'] = list()
        hyp_sets_output_dict['hypothesis_sets'] = list()
        for hyp_set in solution_set.hyp_sets.values():
            if hyp_set is CausalHypChain:
                hyp_sets_output_dict['causal_hyp_chains'].append(hyp_set)
            else:
                hyp_sets_output_dict['hypothesis_sets'].append(hyp_set)
            # end if else
        # end for

        # Encode contradictions into separate lists according to their type.
        contradictions_output_dict = dict()
        contradictions_output_dict['in_image_trans_cons'] = [c for c in solution_set.contradictions
                                                             if isinstance(c, InImageTransCon)]
        contradictions_output_dict['tween_image_trans_cons'] = [c for c in solution_set.contradictions
                                                                if isinstance(c, TweenImageTransCon)]
        contradictions_output_dict['causal_hyp_flow_cons'] = [c for c in solution_set.contradictions
                                                              if isinstance(c, CausalHypFlowCon)]
        contradictions_output_dict['causal_chain_flow_cons'] = [c for c in solution_set.contradictions
                                                                if isinstance(c, CausalChainFlowCon)]
        contradictions_output_dict['causal_cycle_con'] = [c for c in solution_set.contradictions
                                                          if isinstance(c, CausalCycleCon)]

        return {'id': solution_set.id,
                'parameter_set_id': solution_set.parameters.id,
                'individual_scores': individual_scores_output_list,
                'paired_scores': paired_scores_output_list,
                'hyp_sets': hyp_sets_output_dict,
                'contradictions': contradictions_output_dict,
                'solutions': solution_set.solutions}
    # end _encode_solution_set
# end class SensemakingDataEncoder