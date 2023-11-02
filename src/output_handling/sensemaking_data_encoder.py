import json

from parameters import ParameterSet
from input_handling.scene_graph_data import (Image, BoundingBox, 
                                             SceneGraphObject, 
                                             SceneGraphRelationship)
from knowledge_graph.graph import KnowledgeGraph
from knowledge_graph.items import (Node, Concept, Instance, Object, Action, 
                                   Edge, ConceptType, EdgeRelationship)
from commonsense.commonsense_data import (CommonSenseNode, CommonSenseEdge, 
                                          FrameNetType, Synset)
from hypothesis.hypothesis import (Evidence, ConceptEdgeEv, 
                                   OtherHypEv, 
                                   VisualSimEv,
                                   AttributeSimEv,
                                   CausalPathEv,
                                   Hypothesis,
                                   ConceptEdgeHyp,
                                   NewObjectHyp,
                                   SameObjectHyp,
                                   PersistObjectHyp,
                                   CausalSequenceHyp)
from hypothesis.hypothesis_evaluator import Solution

class SensemakingDataEncoder(json.JSONEncoder):
    """
    JSON encoder for custom classes and data involved in sensemaking.
    """

    def default(self, o):
        """
        Checks the type of the object. If it's of a type that this encoder
        handles, returns a serializable dictionary version of if.

        Otherwise, calls the default encoder on it. 
        """
        if isinstance(o, KnowledgeGraph):
            return self._encode_knowledge_graph(o)
        elif isinstance(o, CommonSenseNode):
            return self._encode_commonsense_node(o)
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
        elif isinstance(o, ConceptEdgeEv):
            return self._encode_concept_edge_ev(o)
        elif isinstance(o, OtherHypEv):
            return self._encode_other_hyp_ev(o)
        elif isinstance(o, VisualSimEv):
            return self._encode_visual_sim_ev(o)
        elif isinstance(o, AttributeSimEv):
            return self._encode_attribute_sim_ev(o)
        elif isinstance(o, CausalPathEv):
            return self._encode_causal_path_ev(o)
        elif isinstance(o, ConceptEdgeHyp):
            return self._encode_concept_edge_hyp(o)
        elif isinstance(o, NewObjectHyp):
            return self._encode_new_object_hyp(o)
        elif isinstance(o, SameObjectHyp):
            return self._encode_same_object_hyp(o)
        elif isinstance(o, PersistObjectHyp):
            return self._encode_persist_object_hyp(o)
        elif isinstance(o, CausalSequenceHyp):
            return self._encode_causal_sequence_hyp(o)
        elif isinstance(o, Solution):
            return self._encode_solution(o)
        # Some custom dataclasses can be turned into their dictionary forms and 
        # returned.
        elif isinstance(o, (Synset, BoundingBox, ParameterSet)):
            return o.__dict__
        # Custom enumerators can be cast into strings.
        elif isinstance(o, (FrameNetType, ConceptType, EdgeRelationship)):
            return str(o)
        # end elif
        return json.JSONEncoder.default(self, o)
    # end default

    def _encode_knowledge_graph(self, knowledge_graph: KnowledgeGraph):
        """
        Encodes a KnowledgeGraph into a json serializable dictionary.

        Has lists of all CommonSenseNodes, Images, Nodes, and Edges.
        """
        kg_dict = dict()
        # First, encode all commonsense_nodes into a top-level dictionaries. 
        # Any Concept that has these nodes will reference them by their IDs. 
        # Each CommonSenseNode is encoded with a list of the ids of the 
        # CommonSenseEdges incident on them. 
        commonsense_nodes = {cs_node.id: cs_node for cs_node in 
                             knowledge_graph.get_commonsense_nodes()}
        kg_dict['commonsense_nodes'] = list(commonsense_nodes.values())
        # Encode all the images.
        kg_dict['images'] = list(knowledge_graph.images.values())
        # Encode all Nodes
        kg_dict['nodes'] = list(knowledge_graph.nodes.values())
        #kg_dict['concepts'] = list(knowledge_graph.concepts.values())
        #kg_dict['objects'] = list(knowledge_graph.objects.values())
        #kg_dict['actions'] = list(knowledge_graph.actions.values())
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
                'image': scene_graph_object.image.id,
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
                'image': relationship.image.id}
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
                'edges': [edge_id for edge_id in node.edges.keys()],
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
                          'commonsense_nodes': [cs_node_id for cs_node_id in 
                                                concept.commonsense_nodes.keys()]})
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
        node_dict.update({'concepts': [concept.id for concept 
                                       in instance.concepts],
                          'images': [image_id for image_id 
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
        node_dict.update({'subject': action.subject.id,
                          'obj': (None if action.object is None 
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
                'source': edge.source.id,
                'target': edge.target.id,
                'relationship': edge.relationship,
                'weight': edge.weight,
                'commonsense_edge': (None if edge.commonsense_edge is None 
                                     else edge.commonsense_edge.id)}
    # end _encode_edge

    def _encode_evidence(self, evidence: Evidence):
        """
        Encodes a piece of Evidence into a json serializable dictionary.

        Adds a 'type' field with a string representation of the Evidence's type.
        """
        return {'id': evidence.id,
                'score': evidence.score,
                'type': type(evidence).__name__}
    # end _encode_evidence

    def _encode_concept_edge_ev(self, concept_edge_ev: ConceptEdgeEv):
        """
        Encodes a piece of ConceptEdgeEv into a json serializble dict.

        edge is encoded as its Edge id.
        """
        evidence_dict = self._encode_evidence(concept_edge_ev)
        evidence_dict.update({'edge': concept_edge_ev.edge.id})
        return evidence_dict
    # end _encode_concept_edge_ev

    def _encode_other_hyp_ev(self, oh_evidence: OtherHypEv):
        """
        Encodes a piece of OtherHypEv into a json serializable dict.

        hypothesis is encoded as the hypothesis' id.
        """
        evidence_dict = self._encode_evidence(oh_evidence)
        evidence_dict.update({'hypothesis': oh_evidence.hypothesis.id})
        return evidence_dict
    # end _encode_other_hyp_ev

    def _encode_visual_sim_ev(self, 
                                        visual_sim_ev: VisualSimEv):
        """
        Encodes a piece of VisualSimEv into a json serializable
        dict.

        object_1 and object_2 are encoded as Node ids.
        """
        evidence_dict = self._encode_evidence(visual_sim_ev)
        evidence_dict.update({'object_1': visual_sim_ev.object_1.id,
                              'object_2': visual_sim_ev.object_2.id})
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
        evidence_dict.update({'object_1': attribute_sim_ev.object_1.id,
                              'object_2': attribute_sim_ev.object_2.id})
        return evidence_dict
    # end _encode_attribute_sim_ev

    def _encode_causal_path_ev(self,
                               causal_path_ev: CausalPathEv):
        """
        Encodes a piece of CausalPathEv into a json serializable dict.

        source_action and target_action are encoded as Node ids.
        source_concept and target_concept are encoded as Node ids. 
        edge, the next_edge of the first Step of the concept_path, is encoded
            as an Edge id.
        """
        evidence_dict = self._encode_evidence(causal_path_ev)
        evidence_dict.update({'source_action': causal_path_ev.source_action.id,
                              'target_action': causal_path_ev.target_action.id,
                              'source_concept': causal_path_ev.source_concept.id,
                              'target_concept': causal_path_ev.target_concept.id,
                              'edge': causal_path_ev.concept_path.steps[0].next_edge.id})
        return evidence_dict
    # end _encode_causal_path_ev

    def _encode_hypothesis(self, hypothesis: Hypothesis):
        """
        Encodes a Hypothesis into a json serializable dict.

        Adds a 'type' field with a string of the Hypothesis' class type.

        premises is encoded as a list of Hypothesis ids.
        """
        return {'id': hypothesis.id,
                'name': hypothesis.name,
                'premises': [h_id for h_id in hypothesis.premises.keys()],
                'type': type(hypothesis).__name__}
    # end _encode_hypothesis

    def _encode_concept_edge_hyp(self, concept_edge_hyp: ConceptEdgeHyp):
        """
        Encodes a ConceptEdgeHypothesis into a json serializable dict.

        source_instance and target_instance are encoded as Node ids.

        edge is encoded as an Edge id.
        """
        h_dict = self._encode_hypothesis(concept_edge_hyp)
        h_dict.update({'source_instance': concept_edge_hyp.source_instance.id,
                       'target_instance': concept_edge_hyp.target_instance.id,
                       'edge': concept_edge_hyp.edge.id,
                       'concept_edge_ev': concept_edge_hyp.concept_edge_ev})
        return h_dict
    # end _encode_concept_edge_hyp

    def _encode_new_object_hyp(self, obj_hypothesis: NewObjectHyp):
        """
        Encodes a NewObjectHyp into a json serializable dict.

        object is a hypothesized Object which should be in the 
        KnowledgeGraph. It is encoded as its id.

        concept_edge_hyps is encoded as a list of Hypothesis id.
        """
        h_dict = self._encode_hypothesis(obj_hypothesis)
        h_dict.update({'object': obj_hypothesis.obj.id,
                       'concept_edge_hyps': [h.id for h in 
                                        obj_hypothesis.concept_edge_hyps],
                       'concept_edge_hyp_ev': [e for e in 
                                        obj_hypothesis.concept_edge_hyp_ev]})
        return h_dict
    # end _encode_new_object_hyp

    def _encode_same_object_hyp(self, 
                                    same_object_hyp: SameObjectHyp):
        """
        Encodes an SameObjectHyp into a json serializable dict.

        object_1 and object_2 are encoded as their Node ids.

        edge is a hypothesized Edge which does not exist in the knowledge graph, 
        so the whole Edge is encoded in the hypothesis.
        """
        h_dict = self._encode_hypothesis(same_object_hyp)
        h_dict.update({'object_1': same_object_hyp.object_1.id,
                       'object_2': same_object_hyp.object_2.id,
                       'edge': same_object_hyp.edge,
                       'visual_sim_ev': same_object_hyp.visual_sim_ev,
                       'attribute_sim_ev': same_object_hyp.attribute_sim_ev})
        return h_dict
    # end _encode_same_object_hyp

    def _encode_persist_object_hyp(self, persist_object_hyp: PersistObjectHyp):
        """
        Encodes a PersistObjectHyp into a json serializable dict.

        object_ is encoded as its Node id.

        new_object_hyp and same_object_hyp are encoded as their ids.
        """
        h_dict = self._encode_hypothesis(persist_object_hyp)
        h_dict.update({'object_': persist_object_hyp.object_.id,
            'new_object_hyp': persist_object_hyp.new_object_hyp.id,
            'same_object_hyp': persist_object_hyp.same_object_hyp.id,
            'new_object_hyp_ev': persist_object_hyp.new_object_hyp_ev,
            'same_object_hyp_ev': persist_object_hyp.same_object_hyp_ev})
        return h_dict
    # end _encode_persist_object_hyp

    def _encode_causal_sequence_hyp(self, causal_sequence_hyp: CausalSequenceHyp):
        """
        Encodes a CausalSequenceHyp into a json serializable dict.

        source_action and target_action encoded as their Node ids.
        edge (leads-to) added as-is. Can't encode by ID because it's not a part
            of the knowledge graph. 
        causal_path_evs added as-is so they can be encoded later.
        """
        h_dict = self._encode_hypothesis(causal_sequence_hyp)
        h_dict.update({'source_action': causal_sequence_hyp.source_action.id,
                       'target_action': causal_sequence_hyp.target_action.id,
                       'edge': causal_sequence_hyp.edge.id,
                       'causal_path_evs': causal_sequence_hyp.causal_path_evs})
        return h_dict
    # end _encode_causal_sequence_hyp

    def _encode_solution(self, solution: Solution):
        """
        Encodes a Solution into a json serializable dict.

        parameters is encoded as the parameter set's id.

        accepted_hypotheses is encoded as a list of Hypothesis ids.
        """
        return {'id': solution.id,
                'parameters': solution.parameters.id,
                'accepted_hypotheses': [h_id for h_id in 
                                        solution.accepted_hypotheses.keys()],
                'energy': solution.energy}
    # end _encode_solution
# end class SensemakingDataEncoder