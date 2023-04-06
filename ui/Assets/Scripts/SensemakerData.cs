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
        // Decode the parameter sets.
        JToken psets_token = sensemaker_data_token["parameter_sets"];
        sensemaker_data.parameter_sets = this.DecodeParameterSets(psets_token);
        // Decode the solutions
        JToken solutions_token = sensemaker_data_token["solutions"];
        sensemaker_data.solutions = this.DecodeSolutions(solutions_token,
            sensemaker_data.parameter_sets,
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
                case "ConceptEdgeHyp":
                {
                    var new_h = new ConceptEdgeHyp(h_token);
                    hypotheses[new_h.id] = new_h;
                    break;
                }
                case "NewObjectHyp":
                {
                    var new_h = new NewObjectHyp(h_token);
                    hypotheses[new_h.id] = new_h;
                    break;
                }
                case "SameObjectHyp":
                {
                    var new_h = new SameObjectHyp(h_token);
                    hypotheses[new_h.id] = new_h;
                    break;
                }
                case "PersistObjectHyp":
                {
                    var new_h = new PersistObjectHyp(h_token);
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
                if (evidence is ConceptEdgeEv)
                {
                    var concept_edge_ev = (ConceptEdgeEv)evidence;
                    concept_edge_ev.edge = knowledge_graph.edges[concept_edge_ev.edge_id];
                }
                // Other hypothesis evidence refrences an existing hypotheiss.
                else if (evidence is OtherHypEv)
                {
                    var oh_evidence = (OtherHypEv)evidence;
                    oh_evidence.hypothesis = hypotheses[oh_evidence.hypothesis_id];
                }
                // Visual similarity evidence references two ObjectNodes.
                else if (evidence is VisualSimEv)
                {
                    var visual_sim_ev = (VisualSimEv)evidence;
                    visual_sim_ev.object_1 = (ObjectNode)knowledge_graph.nodes[visual_sim_ev.object_1_id];
                    visual_sim_ev.object_2 = (ObjectNode)knowledge_graph.nodes[visual_sim_ev.object_2_id];
                }
                // Attribute similarity evidence references two ObjectNodes.
                else if (evidence is AttributeSimEv)
                {
                    var attribute_sim_ev = (AttributeSimEv)evidence;
                    attribute_sim_ev.object_1 = (ObjectNode)knowledge_graph.nodes[attribute_sim_ev.object_1_id];
                    attribute_sim_ev.object_2 = (ObjectNode)knowledge_graph.nodes[attribute_sim_ev.object_2_id];
                }
            }
            // Concept edge hypotheses reference two instance Nodes and an Edge.
            if (hypothesis is ConceptEdgeHyp)
            {
                var ce_h = (ConceptEdgeHyp)hypothesis;
                ce_h.source_instance = knowledge_graph.nodes[ce_h.source_instance_id];
                ce_h.target_instance = knowledge_graph.nodes[ce_h.target_instance_id];
                ce_h.edge = knowledge_graph.edges[ce_h.edge_id];
            }
            // Object hypotheses reference a set of concept edge hypotheses
            // and an ObjectNode.
            // Its ObjectNode references a set of Concept node and a set of Images.
            else if (hypothesis is NewObjectHyp)
            {
                var obj_h = (NewObjectHyp)hypothesis;
                obj_h.obj = (ObjectNode)knowledge_graph.nodes[obj_h.object_id];
                foreach (int ce_h_id in obj_h.concept_edge_hyps_ids)
                {
                    obj_h.concept_edge_hyps[ce_h_id] = (ConceptEdgeHyp)hypotheses[ce_h_id];
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
            else if (hypothesis is SameObjectHyp)
            {
                var od_h = (SameObjectHyp)hypothesis;
                od_h.object_1 = (ObjectNode)knowledge_graph.nodes[od_h.object_1_id];
                od_h.object_2 = (ObjectNode)knowledge_graph.nodes[od_h.object_2_id];
                od_h.edge.source = knowledge_graph.nodes[od_h.edge.source_id];
                od_h.edge.target = knowledge_graph.nodes[od_h.edge.target_id];
            }
            // Object persistence hypotheses reference an object node, an
            // offscreen object hypothesis, and an object duplicate hypothesis.
            else if (hypothesis is PersistObjectHyp)
            {
                var op_h = (PersistObjectHyp)hypothesis;
                op_h.object_ = (ObjectNode)knowledge_graph.nodes[op_h.object_id];
                op_h.new_object_hyp = (NewObjectHyp)hypotheses[op_h.offscreen_obj_h_id];
                op_h.same_object_hyp = (SameObjectHyp)hypotheses[op_h.same_object_h_id];
            }
        }
        return hypotheses;
    }

    private Dictionary<int, ParameterSet> DecodeParameterSets(JToken token)
    {
        var parameter_sets = new Dictionary<int, ParameterSet>();
        foreach (JToken pset_token in token)
        {
            var new_pset = new ParameterSet(pset_token);
            parameter_sets[new_pset.id] = new_pset;
        }
        return parameter_sets;
    }

    private Dictionary<int, Dictionary<int, Solution>> DecodeSolutions(
        JToken token, Dictionary<int, ParameterSet> parameter_sets,
        Dictionary<int, Hypothesis> hypotheses)
    {
        // Solutions is first keyed by parameter set id, then by solution id.
        var solutions = new Dictionary<int, Dictionary<int, Solution>>();
        foreach (int pset_id in parameter_sets.Keys)
        {
            solutions[pset_id] = new Dictionary<int, Solution>();
        }

        // The token passed in is a list of lists. Each dictionary has
        // "parameter_set", and int, and "solutions".
        // In "solutions" is a list of the actual solution objects.
        foreach (JToken solution_set_list_token in token)
        {
            foreach (JToken solution_token in solution_set_list_token)
            {
                var solution = new Solution(solution_token);
                solutions[solution.parameters_id][solution.id] = solution;
            }
        }

        // Resolve hypothesis and parameter set references within each solution.
        foreach (int pset_id in solutions.Keys)
        {
            foreach (int solution_id in solutions[pset_id].Keys)
            {
                // Resolve references to hypotheses.
                foreach (int h_id in solutions[pset_id][solution_id].accepted_hypothesis_ids)
                {
                    solutions[pset_id][solution_id].accepted_hypotheses.Add(
                        h_id, hypotheses[h_id]);
                }
                // Resolve reference to parameter set.
                solutions[pset_id][solution_id].parameters = parameter_sets[pset_id];
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
    // Parameter sets keyed by their ids.
    public Dictionary<int, ParameterSet> parameter_sets;
    // Solutions are keyed by parameter set id, then solution id.
    public Dictionary<int, Dictionary<int, Solution>> solutions;
}