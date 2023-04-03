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
from hypothesis.hypothesis import (Evidence, ConceptEdgeEvidence, 
                                   OtherHypothesisEvidence, 
                                   VisualSimilarityEvidence,
                                   AttributeSimilarityEvidence,
                                   Hypothesis,
                                   ConceptEdgeHypothesis,
                                   ObjectHypothesis,
                                   ObjectDuplicateHypothesis)
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
        elif isinstance(o, ConceptEdgeEvidence):
            return self._encode_concept_edge_evidence(o)
        elif isinstance(o, OtherHypothesisEvidence):
            return self._encode_other_hypothesis_evidence(o)
        elif isinstance(o, VisualSimilarityEvidence):
            return self._encode_visual_similarity_evidence(o)
        elif isinstance(o, AttributeSimilarityEvidence):
            return self._encode_attribute_similarity_evidence(o)
        elif isinstance(o, ConceptEdgeHypothesis):
            return self._encode_concept_edge_hypothesis(o)
        elif isinstance(o, ObjectHypothesis):
            return self._encode_object_hypothesis(o)
        elif isinstance(o, ObjectDuplicateHypothesis):
            return self._encode_object_duplicate_hypothesis(o)
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

        Edges are encoded as a list of edge ids. These can be looked up in
        the KnowledgeGraph's edges dictionary.
        """
        return {'id': node.id,
                'label': node.label,
                'name': node.name,
                'edges': [edge_id for edge_id in node.edges.keys()],
                'hypothesized': node.hypothesized}
    # end _encode_node

    def _encode_concept(self, concept: Concept):
        """
        Encodes a Concept node into a json serializable dictionary.

        Adds a 'type' field whose value is 'concept'.

        commonsense_nodes is encoded as a list of CommonSenseNode ids. 
        These can be looked up in the KnowledgeGraph's commonsense_nodes
        dictionary. 
        """
        # First, encode it as a Node.
        node_dict = self._encode_node(concept)
        # Then, add the extra information from it being a Concept.
        node_dict.update({'type': 'concept',
                          'concept_type': concept.concept_type,
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

        Adds a 'type' field whose value is 'object'

        Ignores the appearance attribute. The Object's appearance can be
        re-calculated from its smallest bounding box and its image's file.
        """
        # First, encode it as an Instance.
        node_dict = self._encode_instance(object_node)
        # Then, add extra information from it being an Object.
        node_dict.update({'type': 'object',
                          'scene_graph_objects': object_node.scene_graph_objects,
                          'attributes': object_node.attributes})
        return node_dict
    # end _encode_object

    def _encode_action(self, action: Action):
        """
        Encodes an Action node into a json serializable dictionary.

        Adds a 'type' field whose value is 'action'.

        subject and object are encoded as the ids of Object nodes. 

        Have to call object 'obj' because object is a reserved term.
        """
        # First, encode it as an Instance.
        node_dict = self._encode_instance(action)
        # Then, add extra information from it being an Action.
        node_dict.update({'type': 'action',
                          'subject': action.subject.id,
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
        """
        return {'id': evidence.id,
                'score': evidence.score}
    # end _encode_evidence

    def _encode_concept_edge_evidence(self, ce_evidence: ConceptEdgeEvidence):
        """
        Encodes a piece of ConceptEdgeEvidence into a json serializble dict.

        Adds a 'type' field whose value is 'concept_edge'.

        edge is encoded as its Edge id.
        """
        evidence_dict = self._encode_evidence(ce_evidence)
        evidence_dict.update({'type': 'concept_edge',
                              'edge': ce_evidence.edge.id})
        return evidence_dict
    # end _encode_concept_edge_evidence

    def _encode_other_hypothesis_evidence(self, 
                                          oh_evidence: OtherHypothesisEvidence):
        """
        Encodes a piece of OtherHypothesisEvidence into a json serializable dict.

        Adds a 'type' field whose value is 'other_hypothesis'.

        hypothesis is encoded as the hypothesis' id.
        """
        evidence_dict = self._encode_evidence(oh_evidence)
        evidence_dict.update({'type': 'other_hypothesis',
                              'hypothesis': oh_evidence.hypothesis.id})
        return evidence_dict
    # end _encode_other_hypothesis_evidence

    def _encode_visual_similarity_evidence(self, 
                                        vs_evidence: VisualSimilarityEvidence):
        """
        Encodes a piece of VisualSimilarityEvidence into a json serializable
        dict.

        Adds a 'type' field whose value is 'visual_similarity'

        object_1 and object_2 are encoded as Node ids.
        """
        evidence_dict = self._encode_evidence(vs_evidence)
        evidence_dict.update({'type': 'visual_similarity',
                              'object_1': vs_evidence.object_1.id,
                              'object_2': vs_evidence.object_2.id})
        return evidence_dict
    # end _encode_visual_similarity_evidence

    def _encode_attribute_similarity_evidence(self,
                                    as_evidence: AttributeSimilarityEvidence):
        """
        Encodes a piece of AttributeSimilarityEvidence into a json serializable
        dict.

        Adds a 'type' field whose value is 'attribute_similarity'.

        object_1 and object_2 are encoded as Node ids.
        """
        evidence_dict = self._encode_evidence(as_evidence)
        evidence_dict.update({'type': 'attribute_similarity',
                              'object_1': as_evidence.object_1.id,
                              'object_2': as_evidence.object_2.id})
        return evidence_dict
    # end _encode_attribute_similarity_evidence

    def _encode_hypothesis(self, hypothesis: Hypothesis):
        """
        Encodes a Hypothesis into a json serializable dict.

        premises is encoded as a list of Hypothesis ids.
        """
        return {'id': hypothesis.id,
                'name': hypothesis.name,
                'score': hypothesis.score,
                'evidence': hypothesis.evidence,
                'premises': [h_id for h_id in hypothesis.premises.keys()]}
    # end _encode_hypothesis

    def _encode_concept_edge_hypothesis(self, 
                                        ce_hypothesis: ConceptEdgeHypothesis):
        """
        Encodes a ConceptEdgeHypothesis into a json serializable dict.

        Adds a 'type' field with 'concept_edge' as its value.

        source_instance and target_instance are encoded as Node ids.

        edge is encoded as an Edge id.
        """
        h_dict = self._encode_hypothesis(ce_hypothesis)
        h_dict.update({'type': 'concept_edge',
                       'source_instance': ce_hypothesis.source_instance.id,
                       'target_instance': ce_hypothesis.target_instance.id,
                       'edge': ce_hypothesis.edge.id})
        return h_dict
    # end _encode_concept_edge_hypothesis

    def _encode_object_hypothesis(self, obj_hypothesis: ObjectHypothesis):
        """
        Encodes an ObjectHypothesis into a json serializable dict.

        Adds a 'type' field with 'object' as its value.

        object is a hypothesized Object which should be in the 
        KnowledgeGraph. It is encoded as its id.

        concept_edge_hypotheses is encoded as a list of Hypothesis id.
        """
        h_dict = self._encode_hypothesis(obj_hypothesis)
        h_dict.update({'type': 'object',
                       'object': obj_hypothesis.obj.id,
                       'concept_edge_hypotheses': [h.id for h in 
                                        obj_hypothesis.concept_edge_hypotheses]})
        return h_dict
    # end _encode_object_hypothesis

    def _encode_object_duplicate_hypothesis(self, 
                                    od_hypothesis: ObjectDuplicateHypothesis):
        """
        Encodes an ObjectDuplicateHypothesis into a json serializable dict.

        Adds a 'type' field with 'object_duplicate' as its value.

        object_1 and object_2 are encoded as their Node ids.

        edge is a hypothesized Edge which does not exist in the knowledge graph, 
        so the whole Edge is encoded in the hypothesis.
        """
        h_dict = self._encode_hypothesis(od_hypothesis)
        h_dict.update({'type': 'object_duplicate',
                       'object_1': od_hypothesis.object_1.id,
                       'object_2': od_hypothesis.object_2.id,
                       'edge': od_hypothesis.edge})
        return h_dict
    # end _encode_object_duplicate_hypothesis

    def _encode_solution(self, solution: Solution):
        """
        Encodes a Solution into a json serializable dict.

        accepted_hypotheses is encoded as a list of Hypothesis ids.
        """
        return {'id': solution.id,
                'parameters': solution.parameters,
                'accepted_hypotheses': [h_id for h_id in 
                                        solution.accepted_hypotheses.keys()],
                'energy': solution.energy}
    # end _encode_solution
# end class SensemakingDataEncoder