
using JetBrains.Annotations;
using System;
using System.Collections.Generic;
using System.IO;
using Newtonsoft.Json;
using UnityEngine;

public class SensemakerDataReader
{
    public SensemakerDataReader()
    {

    }

    public SensemakerData ReadSensemakerData(string file_path)
    {
        string json_text = File.ReadAllText(file_path);
        // Decode the json into import-specific classes.
        SensemakerDatasImport sensemaker_datas_import = JsonUtility.FromJson<SensemakerDatasImport>(json_text);
        // Make actual classes from those import-specific classes.
        SensemakerDataImport sensemaker_data_import = sensemaker_datas_import.sensemaker_data;
        
        // Knowledge Graph.
        KnowledgeGraph knowledge_graph = new KnowledgeGraph(sensemaker_data_import.knowledge_graph);
        
        // Hypotheses
        Dictionary<int, Hypothesis> hypotheses = new Dictionary<int, Hypothesis>();
        HypothesesImport hypotheses_import = sensemaker_data_import.hypotheses;
        // Same object hyps
        foreach (SameObjectHypImport data in hypotheses_import.same_object_hyps)
        {
            SameObjectHyp new_hyp = new SameObjectHyp(data);
            new_hyp.PopulateNodes(knowledge_graph.nodes);
            new_hyp.PopulateCommonSenseEdges(knowledge_graph.commonsense_edges);
            hypotheses[data.id] = new_hyp;
        }
        // Causal sequence hyps.
        foreach (CausalSequenceHypImport data in hypotheses_import.causal_sequence_hyps)
        {
            CausalSequenceHyp new_hyp = new CausalSequenceHyp(data);
            new_hyp.PopulateNodes(knowledge_graph.nodes);
            new_hyp.PopulateCommonSenseEdges(knowledge_graph.commonsense_edges);
            new_hyp.PopulateEdges(knowledge_graph.edges);
            hypotheses[data.id] = new_hyp;
        }
        // Now that all hypotheses are created, populate hypotheses within those hypotheses.
        foreach (Hypothesis hyp in hypotheses.Values)
        {
            if (hyp is CausalSequenceHyp)
            {
                ((CausalSequenceHyp)hyp).PopulateHypotheses(hypotheses);
            }
        }

        // Parameter sets.
        Dictionary<int, ParameterSet> parameter_sets = new Dictionary<int, ParameterSet>();
        foreach (ParameterSetImport data in sensemaker_data_import.parameter_sets)
        {
            parameter_sets.Add(data.id, new ParameterSet(data));
        }

        // Solution sets
        // Keyed by the ID of the parameter set that created the solution set.
        Dictionary<int, SolutionSet> solution_sets = new Dictionary<int, SolutionSet>();
        foreach (SolutionSetImport data in sensemaker_data_import.solution_sets)
        {
            int parameter_set_id = data.parameter_set_id;
            SolutionSet new_solution_set = new SolutionSet(data);
            new_solution_set.PopulateParameterSet(parameter_sets);
            new_solution_set.PopulateNodes(knowledge_graph.nodes);
            new_solution_set.PopulateHypotheses(hypotheses);
            new_solution_set.PopulateImages(knowledge_graph.images);
            solution_sets[data.parameter_set_id] = new_solution_set;
        }

        // If any of the solution sets have no solutions, stop here.
        foreach (SolutionSet solution_set in solution_sets.Values)
        {
            if (solution_set.solutions.Count == 0)
            {
                Console.WriteLine("Sensemaker data read. No valid data.");
                return null;
            }
        }

        foreach (Hypothesis hyp in hypotheses.Values)
        {
            hyp.PopulateSolutionSets(solution_sets);
        }

        Console.WriteLine("Sensemaker data read.");
        return new SensemakerData(sensemaker_data_import,
            knowledge_graph,
            hypotheses,
            parameter_sets,
            solution_sets);
    }
}

public class SensemakerData
{
    public SensemakerDataImport imported_data;

    public KnowledgeGraph knowledge_graph;
    public Dictionary<int, Hypothesis> hypotheses;
    public Dictionary<int, ParameterSet> parameter_sets;
    // First key is a parameter set id. 
    public Dictionary<int, SolutionSet> solution_sets;

    public SensemakerData(SensemakerDataImport imported_data, 
        KnowledgeGraph knowledge_graph, 
        Dictionary<int, Hypothesis> hypotheses, 
        Dictionary<int, ParameterSet> parameter_sets,
        Dictionary<int, SolutionSet> solution_sets)
    {
        this.imported_data = imported_data;
        this.knowledge_graph = knowledge_graph;
        this.hypotheses = hypotheses;
        this.parameter_sets = parameter_sets;
        this.solution_sets = solution_sets;
    }
}

// Classes matching the structure of sensemaker data json files
// for deserialization.
[Serializable]
public class SensemakerDatasImport
{
    public SensemakerDataImport sensemaker_data;
}

[Serializable]
public class SensemakerDataImport
{
    public KnowledgeGraphImport knowledge_graph;
    public HypothesesImport hypotheses;
    public List<ParameterSetImport> parameter_sets;
    public List<SolutionSetImport> solution_sets;
}

[Serializable]
public class KnowledgeGraphImport
{
    public List<CommonSenseNodeImport> commonsense_nodes;
    public List<CommonSenseEdgeImport> commonsense_edges;
    public List<ImageImport> images;
    public List<ConceptImport> concepts;
    public List<ObjectImport> objects;
    public List<ActionImport> actions;
    public List<EdgeImport> edges;
}

[Serializable]
public class CommonSenseNodeImport
{
    public int id;
    public string uri;
    public List<string> labels;
    public List<int> edge_ids;
}

[Serializable]
public class CommonSenseEdgeImport
{
    public int id;
    public string uri;
    public List<string> labels;
    public string relation;
    public int start_node_id;
    public int end_node_id;
    public string start_node_uri;
    public string end_node_uri;
    public float weight;
    public string dimension;
    public string source;
    public string sentence;
}

[Serializable]
public class ImageImport
{
    public int id;
    public int index;
    public string file_path;
}

[Serializable]
public class NodeImport
{
    public int id;
    public string label;
    public string name;
    public List<int> edge_ids;
    public bool hypothesized;
    public string type;
}

[Serializable]
public class PolarityScoresImport
{
    public float neg;
    public float neu;
    public float pos;
    public float compound;
}

[Serializable]
public class ConceptImport: NodeImport
{
    public string concept_type;
    public SynsetImport synset;
    public List<int> commonsense_node_ids;
    public PolarityScoresImport polarity_scores;
    public float sentiment;
}

[Serializable]
public class InstanceImport: NodeImport
{
    public List<int> concept_ids;
    public List<int> image_ids;
    public float focal_score;
}

[Serializable]
public class ObjectImport: InstanceImport
{
    public List<SceneGraphObjectImport> scene_graph_objects;
    public List<string> attributes;
}

[Serializable]
public class ActionImport: InstanceImport
{
    public int subject_id;
    public int obj_id;
    public SceneGraphRelImport scene_graph_rel;
}

[Serializable]
public class EdgeImport
{
    public int id;
    public int source_id;
    public int target_id;
    public string relationship;
    public float weight;
    public int commonsense_edge_id;
}

[Serializable]
public class SceneGraphObjectImport
{
    public List<string> names;
    public List<SynsetImport> synsets;
    public int object_id;
    public BoundingBoxImport bounding_box;
    public int image_id;
    public List<string> attributes;
}

[Serializable]
public class SceneGraphRelImport
{
    public string predicate;
    public List<SynsetImport> synsets;
    public int relationship_id;
    public int object_id;
    public int subject_id;
    public int image_id;
}

[Serializable]
public class BoundingBoxImport
{
    public int h;
    public int w;
    public int x;
    public int y;
}

[Serializable]
public class SynsetImport
{
    public string name;
    public string word;
    public string pos;
    public string sense;
}

[Serializable]
public class StepImport
{
    public int id;
    public int node_id;
    public int next_step_id;
    public int next_edge_id;
    public int previous_step_id;
    public int previous_edge_id;
}

[Serializable]
public class MultiStepImport
{
    public int id;
    public List<int> node_ids;
    public int next_step_id;
    public List<int> next_edge_ids;
    public int previous_step_id;
    public List<int> previous_edge_ids;
}

[Serializable]
public class PathImport
{
    public int id;
    public List<StepImport> steps;
}

[Serializable]
public class MultiPathImport
{
    public int id;
    public List<MultiStepImport> steps;
}


[Serializable]
public class HypothesesImport
{
    public List<SameObjectHypImport> same_object_hyps;
    public List<CausalSequenceHypImport> causal_sequence_hyps;
}

[Serializable]
public class HypothesisImport
{
    public int id;
    public string name;
    public List<int> premise_ids;
    public string type;
}

[Serializable]
public class SameObjectHypImport: HypothesisImport
{
    public int object_1_id;
    public int object_2_id;
    public EdgeImport edge;
    public VisualSimEvImport visual_sim_ev;
    public AttributeSimEvImport attribute_sim_ev;
}

[Serializable]
public class AffectCurveScoresImport
{
    public int pset_id;
    public float score;
}

[Serializable]
public class CausalSequenceHypImport : HypothesisImport
{
    public int source_action_id;
    public int target_action_id;
    public EdgeImport edge;
    public List<CausalPathEvImport> causal_path_evs;
    public List<MultiCausalPathEvImport> multi_causal_path_evs;
    public List<ContinuityEvImport> continuity_evs;
    public string direction;
    public List<AffectCurveScoresImport> affect_curve_scores;
}

[Serializable]
public class HypothesisSetsImport
{
    public List<CausalHypChainImport> causal_hyp_chains;
    public List<HypothesisSetImport> hypothesis_sets;
}

[Serializable]
public class HypothesisSetImport
{
    public int id;
    public List<int> hypothesis_ids;
    public bool is_all_or_ex;
}

[Serializable]
public class CausalHypChainImport : HypothesisSetImport
{
    public List<int> hyp_id_sequence;
}

[Serializable]
public class EvidenceImport
{
    public int id;
    public float score;
    public string type;
}

[Serializable]
public class VisualSimEvImport: EvidenceImport
{
    public int object_1_id;
    public int object_2_id;
}

[Serializable]
public class AttributeSimEvImport: EvidenceImport
{
    public int object_1_id;
    public int object_2_id;
}

[Serializable]
public class CausalPathEvImport: EvidenceImport
{
    public int source_action_id;
    public int target_action_id;
    public int source_concept_id;
    public int target_concept_id;
    public PathImport concept_path;
    public string direction;
}

[Serializable]
public class MultiCausalPathEvImport: EvidenceImport
{
    public int source_action_id;
    public int target_action_id;
    public List<int> source_concept_ids;
    public List<int> target_concept_ids;
    public MultiPathImport concept_path;
    public string direction;
}

[Serializable]
public class ContinuityEvImport: EvidenceImport
{
    public int source_action_id;
    public int target_action_id;
    public int source_object_id;
    public int target_object_id;
    public int joining_hyp_id;
}

// Import class for parameter_sets json files.
[Serializable]
public class ParameterSetsImport
{
    public List<ParameterSetImport> parameter_sets;
}

[Serializable]
public class ParameterSetImport
{
    public int id;
    public string name;
    public float visual_sim_ev_weight;
    public float visual_sim_ev_thresh;
    public float attribute_sim_ev_weight;
    public float attribute_sim_ev_thresh;
    public float causal_path_ev_weight;
    public float causal_path_ev_thresh;
    public float continuity_ev_weight;
    public float continuity_ev_thresh;
    public float density_weight;
    public List<int> affect_curve;
    public float affect_curve_weight;
    public float affect_curve_thresh;
}

[Serializable]
public class SolutionSetImport
{
    public int id;
    public int parameter_set_id;
    public List<IndividualScoreImport> individual_scores;
    public List<PairedScoreImport> paired_scores;
    public HypothesisSetsImport hyp_sets;
    public ContradictionsImport contradictions;
    public List<SolutionImport> solutions;
}

[Serializable]
public class SolutionImport
{
    public int id;
    public int parameter_set_id;
    public List<int> accepted_hypothesis_ids;
    public List<int> accepted_hyp_set_ids;
    public float energy;
    public RejectionsImport rejections;
}

[Serializable]
public class IndividualScoreImport
{
    public int id;
    public float score;
}

[Serializable]
public class PairedScoreImport
{
    public List<int> id_pair;
    public float score;
}

[Serializable]
public class ContradictionsImport
{
    public List<InImageTransConImport> in_image_trans_cons;
    public List<TweenImageTransConImport> tween_image_trans_cons;
    public List<CausalHypFlowConImport> causal_hyp_flow_cons;
    public List<CausalChainFlowConImport> causal_chain_flow_cons;
    public List<CausalCycleConImport> causal_cycle_cons;
}

[Serializable]
public class ContradictionImport
{
    public int id;
    public string explanation;
    public string type;
}

[Serializable]
public class HypothesisConImport : ContradictionImport
{
    public int hypothesis_1_id;
    public int hypothesis_2_id;
}

[Serializable]
public class InImageTransConImport : HypothesisConImport
{
    public int obj_1_id;
    public int obj_2_id;
    public int shared_obj_id;
}

[Serializable]
public class TweenImageTransConImport : HypothesisConImport
{
    public int obj_1_id;
    public int obj_2_id;
    public int shared_obj_id;
    public int joining_hyp_id;
    public int hyp_set_id;
}

[Serializable]
public class CausalHypFlowConImport : HypothesisConImport
{
    public int image_1_id;
    public int image_2_id;
}

[Serializable]
public class HypothesisSetConImport : ContradictionImport
{
    public int hyp_set_1_id;
    public int hyp_set_2_id;
}

[Serializable]
public class CausalChainFlowConImport : HypothesisSetConImport
{
    public int image_1_id;
    public int image_2_id;
}

[Serializable]
public class CausalCycleConImport : ContradictionImport
{
    public int image_id;
    public int causal_chain_id;
    public List<int> subset_ids;
}

[Serializable]
public class RejectionsImport
{
    public List<HypConRejectionImport> hyp_con_rejections;
    public List<HypSetConRejectionImport> hyp_set_con_rejections;
    public List<CausalCycleRejectionImport> causal_cycle_rejections;
}

[Serializable]
public class RejectionImport
{
    public int rejected_hyp_id;
    public string explanation;
    public string type;
}

[Serializable]
public class HypConRejectionImport : RejectionImport
{
    public int contradicting_hyp_id;
    public int contradiction_id;
}

[Serializable]
public class HypSetConRejectionImport : RejectionImport
{
    public int contradicting_hyp_set_id;
    public int contradiction_id;
}

[Serializable]
public class ContradictionRejectionImport: RejectionImport
{
    public int contradicting_hyp_id;
    public int contradiction_id;
}

[Serializable]
public class CausalCycleRejectionImport : RejectionImport
{
    public List<int> contradicting_hyp_ids;
    public int contradiction_id;
}