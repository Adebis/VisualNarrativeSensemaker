using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public abstract class JsonCreationConverter<T>: JsonConverter
{
    // This converter is not being used to convert anything.
    public override bool CanConvert(Type objectType)
    {
        return typeof(T).IsAssignableFrom(objectType);
    }
    // The convert also isn't being used to write anything into json.
    public override void WriteJson(JsonWriter writer, object value, 
        JsonSerializer serializer)
    {
        throw new NotImplementedException();
    }
    public override bool CanWrite
    {
        get { return false; }
    }

    // This converter can read json.
    public override bool CanRead
    {
        get { return true; }
    }

    protected abstract T Create(Type objectType, JObject jObject);

    public override object ReadJson(JsonReader reader, Type objectType, 
        object existingValue, JsonSerializer serializer)
    {
        // Load the JObject from the reader stream.
        JObject j_object = JObject.Load(reader);
        // Create target object based on JObject.
        T target = Create(objectType, j_object);
        serializer.Populate(j_object.CreateReader(), target);

        return target;
    }
}

public class SensemakerDataConverter : JsonCreationConverter<SensemakerData>
{
    protected override SensemakerData Create(Type objectType, JObject j_object)
    {
        JToken sensemaker_data_token = j_object["sensemaker_data"];
        SensemakerData sensemaker_data = new SensemakerData();

        // Decode the knowledge graph. 
        JToken kg_token = sensemaker_data_token["knowledge_graph"];
        sensemaker_data.knowledge_graph = new KnowledgeGraph(kg_token);
        // Decode the hypothesis list into a dictionary keyed by id.
        JToken h_list_token = sensemaker_data_token["hypotheses"];
        sensemaker_data.hypotheses = this.DecodeHypotheses(h_list_token,
            sensemaker_data.knowledge_graph);
        // Decode the solutions
        JToken solutions_token = sensemaker_data_token["solutions"];
        sensemaker_data.solutions = this.DecodeSolutions(solutions_token,
            sensemaker_data.hypotheses);
        return sensemaker_data;
    }

    // Decode the dictionary of hypotheses from its JToken
    private Dictionary<int, Hypothesis> DecodeHypotheses(JToken token,
        KnowledgeGraph knowledge_graph)
    {
        var hypotheses = new Dictionary<int, Hypothesis>();
        // Check the hypothesis' type and create the matching hypothesis subtype.
        foreach (JToken h_token in token)
        {
            switch((string)h_token["type"])
            {
                case "concept_edge":
                {
                    var new_h = new ConceptEdgeHypothesis(h_token);
                    hypotheses[new_h.id] = new_h;
                    break;
                }
                case "object":
                {
                    var new_h = new ObjectHypothesis(h_token);
                    hypotheses[new_h.id] = new_h;
                    break;
                }
                case "object_duplicate":
                {
                    var new_h = new ObjectDuplicateHypothesis(h_token);
                    hypotheses[new_h.id] = new_h;
                    break;
                }
            }
        }
        // Resolve all references within hypotheses.
        foreach (var hypothesis in hypotheses.Values)
        {
            // Resolve all premises.
            foreach (int premise_id in hypothesis.premise_ids)
            {
                hypothesis.premises[premise_id] = hypotheses[premise_id];
            }
            // Resolve evidence references.
            foreach (var evidence in hypothesis.evidence)
            {
                // Concept edge evidence references an existing concept edge.
                if (evidence is ConceptEdgeEvidence)
                {
                    var ce_evidence = (ConceptEdgeEvidence)evidence;
                    ce_evidence.edge = knowledge_graph.edges[ce_evidence.edge_id];
                }
                // Other hypothesis evidence refrences an existing hypotheiss.
                else if (evidence is OtherHypothesisEvidence)
                {
                    var oh_evidence = (OtherHypothesisEvidence)evidence;
                    oh_evidence.hypothesis = hypotheses[oh_evidence.hypothesis_id];
                }
                // Visual similarity evidence references two ObjectNodes.
                else if (evidence is VisualSimilarityEvidence)
                {
                    var vs_evidence = (VisualSimilarityEvidence)evidence;
                    vs_evidence.object_1 = (ObjectNode)knowledge_graph.nodes[vs_evidence.object_1_id];
                    vs_evidence.object_2 = (ObjectNode)knowledge_graph.nodes[vs_evidence.object_2_id];
                }
                // Attribute similarity evidence references two ObjectNodes.
                else if (evidence is AttributeSimilarityEvidence)
                {
                    var as_evidence = (AttributeSimilarityEvidence)evidence;
                    as_evidence.object_1 = (ObjectNode)knowledge_graph.nodes[as_evidence.object_1_id];
                    as_evidence.object_2 = (ObjectNode)knowledge_graph.nodes[as_evidence.object_2_id];
                }
            }
            // Concept edge hypotheses reference two instance Nodes and an Edge.
            if (hypothesis is ConceptEdgeHypothesis)
            {
                var ce_h = (ConceptEdgeHypothesis)hypothesis;
                ce_h.source_instance = knowledge_graph.nodes[ce_h.source_instance_id];
                ce_h.target_instance = knowledge_graph.nodes[ce_h.target_instance_id];
                ce_h.edge = knowledge_graph.edges[ce_h.edge_id];
            }
            // Object hypotheses reference a set of concept edge hypotheses
            // and an ObjectNode.
            // Its ObjectNode references a set of Concept node and a set of Images.
            else if (hypothesis is ObjectHypothesis)
            {
                var obj_h = (ObjectHypothesis)hypothesis;
                obj_h.obj = (ObjectNode)knowledge_graph.nodes[obj_h.object_id];
                foreach (int ce_h_id in obj_h.concept_edge_hypothesis_ids)
                {
                    obj_h.concept_edge_hypotheses[ce_h_id] = (ConceptEdgeHypothesis)hypotheses[ce_h_id];
                }
                foreach (int concept_id in obj_h.obj.concept_ids)
                {
                    obj_h.obj.concepts[concept_id] = (ConceptNode)knowledge_graph.nodes[concept_id];
                }
                foreach (int image_id in obj_h.obj.image_ids)
                {
                    obj_h.obj.images[image_id] = knowledge_graph.images[image_id];
                }
            }
            // Object duplicate hypotheses reference two ObjectNodes.
            // Its Edge references two Nodes.
            else if (hypothesis is ObjectDuplicateHypothesis)
            {
                var od_h = (ObjectDuplicateHypothesis)hypothesis;
                od_h.object_1 = (ObjectNode)knowledge_graph.nodes[od_h.object_1_id];
                od_h.object_2 = (ObjectNode)knowledge_graph.nodes[od_h.object_2_id];
                od_h.edge.source = knowledge_graph.nodes[od_h.edge.source_id];
                od_h.edge.target = knowledge_graph.nodes[od_h.edge.target_id];
            }
        }
        return hypotheses;
    }

    private Dictionary<int, Dictionary<int, Solution>> DecodeSolutions(
        JToken token, Dictionary<int, Hypothesis> hypotheses)
    {
        // Solutions is first keyed by parameter set id, then by solution id.
        var solutions = new Dictionary<int, Dictionary<int, Solution>>();

        // The token passed in is a list of dictionaries. Each dictionary has
        // "parameter_set", and int, and "solutions".
        // In "solutions" is a list of the actual solution objects.
        foreach (JToken solution_set_token in token)
        {
            int parameter_set_id = (int)solution_set_token["parameter_set"];
            solutions[parameter_set_id] = new Dictionary<int, Solution>();
            foreach (JToken solution_token in solution_set_token["solutions"])
            {
                var new_solution = new Solution(solution_token);
                solutions[parameter_set_id][new_solution.id] = new_solution;
            }
        }

        // Resolve references to hypotheses within each solution.
        foreach (int pset_id in solutions.Keys)
        {
            foreach (int solution_id in solutions[pset_id].Keys)
            {
                foreach (int h_id in solutions[pset_id][solution_id].accepted_hypothesis_ids)
                {
                    solutions[pset_id][solution_id].accepted_hypotheses.Add(
                        h_id, hypotheses[h_id]);
                }
            }
        }

        return solutions;
    }
}

// Struct for the JSON data that the sensemaker outputs.
public struct SensemakerData
{
    public KnowledgeGraph knowledge_graph;
    // Hypotheses keyed by their ids.
    public Dictionary<int, Hypothesis> hypotheses;
    // Solutions are keyed by parameter set id, then solution id.
    public Dictionary<int, Dictionary<int, Solution>> solutions;
}