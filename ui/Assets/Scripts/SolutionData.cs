using JetBrains.Annotations;
using Newtonsoft.Json.Linq;
using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics.Tracing;
using System.Linq;
using Unity.VisualScripting.FullSerializer;
using UnityEditor.Experimental.GraphView;
using UnityEditor.UI;

public class ParameterSet
{
    private ParameterSetImport imported_data;

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

    public ParameterSet(ParameterSetImport imported_data)
    {
        this.imported_data = imported_data;

        this.id = imported_data.id;
        this.name = imported_data.name;
        this.visual_sim_ev_weight = imported_data.visual_sim_ev_weight;
        this.visual_sim_ev_thresh = imported_data.visual_sim_ev_thresh;
        this.attribute_sim_ev_weight = imported_data.attribute_sim_ev_weight;
        this.attribute_sim_ev_thresh = imported_data.attribute_sim_ev_thresh;
        this.causal_path_ev_weight = imported_data.causal_path_ev_weight;
        this.causal_path_ev_thresh = imported_data.causal_path_ev_thresh;
        this.continuity_ev_weight = imported_data.continuity_ev_weight;
        this.continuity_ev_thresh = imported_data.continuity_ev_thresh;
        this.density_weight = imported_data.density_weight;
        this.affect_curve = imported_data.affect_curve;
        this.affect_curve_weight = imported_data.affect_curve_weight;
        this.affect_curve_thresh = imported_data.affect_curve_thresh;
    }

    /*
    public ParameterSet(int id,
        string name,
        float visual_sim_ev_weight,
        float attribute_sim_ev_weight,
        float causal_path_ev_weight,
        float continuity_ev_weight,
        float density_weight)
    {
        this.imported_data = null;

        this.id = id;
        this.name = name;
        this.visual_sim_ev_weight = visual_sim_ev_weight;
        this.attribute_sim_ev_weight = attribute_sim_ev_weight;
        this.causal_path_ev_weight = causal_path_ev_weight;
        this.continuity_ev_weight = continuity_ev_weight;
        this.density_weight = density_weight;
    }
    */

    public string ToJson()
    {
        string json_string = "{";
        json_string += "\"name\":" + "\"" + this.name + "\",";
        json_string += "\"visual_sim_ev_weight\":" + this.visual_sim_ev_weight.ToString() + ",";
        json_string += "\"visual_sim_ev_thresh\":" + this.visual_sim_ev_thresh.ToString() + ",";
        json_string += "\"attribute_sim_ev_weight\":" + this.attribute_sim_ev_weight.ToString() + ",";
        json_string += "\"attribute_sim_ev_thresh\":" + this.attribute_sim_ev_thresh.ToString() + ",";
        json_string += "\"causal_path_ev_weight\":" + this.causal_path_ev_weight.ToString() + ",";
        json_string += "\"causal_path_ev_thresh\":" + this.causal_path_ev_thresh.ToString() + ",";
        json_string += "\"continuity_ev_weight\":" + this.continuity_ev_weight.ToString() + ",";
        json_string += "\"continuity_ev_thresh\":" + this.continuity_ev_thresh.ToString() + ",";
        json_string += "\"density_weight\":" + this.density_weight.ToString() + ",";
        json_string += "\"affect_curve\":[";
        foreach (int affect_number in this.affect_curve)
        {
            json_string += affect_number.ToString() + ",";
        }
        json_string = json_string.TrimEnd(',');
        json_string += "],";
        json_string += "\"affect_curve_weight\":" + this.affect_curve_weight.ToString() + ",";
        json_string += "\"affect_curve_thresh\":" + this.affect_curve_thresh.ToString();
        json_string += "}";
        return json_string;
    }
}

public class SolutionSet
{
    private SolutionSetImport imported_data;

    public int id;
    public ParameterSet parameter_set;
    public Dictionary<int, float> individual_scores;
    public Dictionary<HashSet<int>, float> paired_scores;
    public Dictionary<int, HypothesisSet> hyp_sets;
    public List<Contradiction> contradictions;
    public List<Solution> solutions;

    public SolutionSet(SolutionSetImport imported_data)
    {
        this.imported_data = imported_data;

        this.id = imported_data.id;
        this.individual_scores = new Dictionary<int, float>();
        foreach (IndividualScoreImport data in imported_data.individual_scores)
        {
            this.individual_scores[data.id] = data.score;
        }
        this.paired_scores = new Dictionary<HashSet<int>, float>();
        foreach (PairedScoreImport data in imported_data.paired_scores)
        {
            HashSet<int> id_pair = new HashSet<int>(data.id_pair);
            this.paired_scores[id_pair] = data.score;
        }

        // Hypothesis Sets
        this.hyp_sets = new Dictionary<int, HypothesisSet>();
        // Causal hypothesis chains
        foreach (CausalHypChainImport data in imported_data.hyp_sets.causal_hyp_chains)
        {
            CausalHypChain new_hyp_set = new CausalHypChain(data);
            this.hyp_sets[new_hyp_set.id] = new_hyp_set;
        }
        // General hypothesis sets.
        foreach (HypothesisSetImport data in imported_data.hyp_sets.hypothesis_sets)
        {
            HypothesisSet new_hyp_set = new HypothesisSet(data);
            this.hyp_sets[new_hyp_set.id] = new_hyp_set;
        }

        // Contradictions
        this.contradictions = new List<Contradiction>();
        // In-image transitivity contradictions.
        foreach (InImageTransConImport data in imported_data.contradictions.in_image_trans_cons)
        {
            InImageTransCon new_contradiction = new InImageTransCon(data);
            this.contradictions.Add(new_contradiction);
        }
        // Between-image transitivity contradictions.
        foreach (TweenImageTransConImport data in imported_data.contradictions.tween_image_trans_cons)
        {
            TweenImageTransCon new_contradiction = new TweenImageTransCon(data);
            this.contradictions.Add(new_contradiction);
        }
        // Causal hyp flow contradictions
        foreach (CausalHypFlowConImport data in imported_data.contradictions.causal_hyp_flow_cons)
        {
            CausalHypFlowCon new_contradiction = new CausalHypFlowCon(data);
            this.contradictions.Add(new_contradiction);
        }
        // Causal chain flow contradictions.
        foreach (CausalChainFlowConImport data in imported_data.contradictions.causal_chain_flow_cons)
        {
            CausalChainFlowCon new_contradiction = new CausalChainFlowCon(data);
            new_contradiction.PopulateHypothesisSets(hyp_sets);
            this.contradictions.Add(new_contradiction);
        }
        // Causal cycle contradictions.
        foreach (CausalCycleConImport data in imported_data.contradictions.causal_cycle_cons)
        {
            CausalCycleCon new_contradiction = new CausalCycleCon(data);
            new_contradiction.PopulateHypothesisSets(hyp_sets);
            this.contradictions.Add(new_contradiction);
        }

        // Solutions
        this.solutions = new List<Solution>();
        foreach (SolutionImport data in imported_data.solutions)
        {
            Solution new_solution = new Solution(data);
            new_solution.PopulateContradictions(this.contradictions);
            new_solution.PopulateHypothesisSets(hyp_sets);
            this.solutions.Add(new_solution);
        }
    }

    public void PopulateNodes(Dictionary<int, Node> all_nodes)
    {
        foreach (Contradiction contradiction in this.contradictions)
        {
            if (contradiction is InImageTransCon)
            {
                ((InImageTransCon)contradiction).PopulateNodes(all_nodes);
            }
            else if (contradiction is TweenImageTransCon)
            {
                ((TweenImageTransCon)contradiction).PopulateNodes(all_nodes);
            }
        }
    }

    public void PopulateParameterSet(Dictionary<int, ParameterSet> all_parameter_sets)
    {
        this.parameter_set = all_parameter_sets[imported_data.parameter_set_id];
        foreach (Solution solution in this.solutions)
        {
            solution.PopulateParameterSet(all_parameter_sets);
        }
    }

    public void PopulateHypotheses(Dictionary<int, Hypothesis> all_hypotheses)
    {
        foreach (HypothesisSet hyp_set in this.hyp_sets.Values)
        {
            if (hyp_set is CausalHypChain)
            {
                ((CausalHypChain)hyp_set).PopulateHypotheses(all_hypotheses);
            }
            else
            {
                hyp_set.PopulateHypotheses(all_hypotheses);
            }
        }

        foreach (Contradiction contradiction in this.contradictions)
        {
            if (contradiction is InImageTransCon)
            {
                ((InImageTransCon)contradiction).PopulateHypotheses(all_hypotheses);
            }
            else if (contradiction is TweenImageTransCon)
            {
                ((TweenImageTransCon)contradiction).PopulateHypotheses(all_hypotheses);
            }
            else if (contradiction is CausalHypFlowCon)
            {
                ((CausalHypFlowCon)contradiction).PopulateHypotheses(all_hypotheses);
            }
        }

        foreach (Solution solution in this.solutions)
        {
            solution.PopulateHypotheses(all_hypotheses);
        }
    }

    public void PopulateImages(Dictionary<int, ImageData> all_images)
    {
        foreach (Contradiction contradiction in this.contradictions)
        {
            if (contradiction is CausalHypFlowCon)
            {
                ((CausalHypFlowCon)contradiction).PopulateImages(all_images);
            }
            else if (contradiction is CausalChainFlowCon)
            {
                ((CausalChainFlowCon)contradiction).PopulateImages(all_images);
            }
            else if (contradiction is CausalCycleCon)
            {
                ((CausalCycleCon)contradiction).PopulateImages(all_images);
            }
        }
    }

    // Gets the paired score between two hypotheses.
    // If the hypotheses don't have a paired score in this solution, returns null.
    public float? GetPairedScore(Hypothesis hyp_1, Hypothesis hyp_2)
    {
        HashSet<int> id_pair = new HashSet<int>() { hyp_1.id, hyp_2.id };
        if (!this.paired_scores.ContainsKey(id_pair))
        {
            return null;
        }
        return this.paired_scores[id_pair];
    }

    // Get all the Contradictions that a Hypothesis is involved in.
    public List<Contradiction> GetContradictions(Hypothesis hypothesis)
    {
        List<Contradiction> return_list = new List<Contradiction>();
        foreach (Contradiction contradiction in this.contradictions)
        {
            if (contradiction.HasHypothesis(hypothesis))
            {
                return_list.Add(contradiction);
            }
        }
        return return_list;
    }
}

public class Solution
{
    private SolutionImport imported_data;

    public int id;
    public ParameterSet parameter_set;
    public Dictionary<int, Hypothesis> accepted_hypotheses;
    public Dictionary<int, HypothesisSet> accepted_hypothesis_sets;
    public List<Rejection> rejections;

    public Solution(SolutionImport imported_data)
    {
        this.imported_data = imported_data;

        this.id = imported_data.id;
        this.accepted_hypotheses = new Dictionary<int, Hypothesis>();
        this.accepted_hypothesis_sets = new Dictionary<int, HypothesisSet>();

        // Rejections
        this.rejections = new List<Rejection>();
        // Hypothesis contradiction rejections.
        foreach (HypConRejectionImport data in imported_data.rejections.hyp_con_rejections)
        {
            HypConRejection new_rejection = new HypConRejection(data);
            this.rejections.Add(new_rejection);
        }
        // Hypothesis set contradiction rejections.
        foreach (HypSetConRejectionImport data in imported_data.rejections.hyp_set_con_rejections)
        {
            HypSetConRejection new_rejection = new HypSetConRejection(data);
            this.rejections.Add(new_rejection);
        }
        // Causal cycle rejections.
        foreach (CausalCycleRejectionImport data in imported_data.rejections.causal_cycle_rejections)
        {
            CausalCycleRejection new_rejection = new CausalCycleRejection(data);
            this.rejections.Add(new_rejection);
        }
    }
    
    public void PopulateContradictions(List<Contradiction> all_contradictions)
    {
        foreach (Rejection rejection in this.rejections)
        {
            if (rejection is HypConRejection)
                ((HypConRejection)rejection).PopulateContradictions(all_contradictions);
            else if (rejection is HypSetConRejection)
                ((HypSetConRejection)rejection).PopulateContradictions(all_contradictions);
            else if (rejection is CausalCycleRejection)
                ((CausalCycleRejection)rejection).PopulateContradictions(all_contradictions);
        }
    }

    public void PopulateParameterSet(Dictionary<int, ParameterSet> all_parameter_sets)
    {
        this.parameter_set = all_parameter_sets[imported_data.parameter_set_id];
    }

    public void PopulateHypotheses(Dictionary<int, Hypothesis> all_hypotheses)
    {
        foreach (int id in imported_data.accepted_hypothesis_ids)
        {
            this.accepted_hypotheses.Add(id, all_hypotheses[id]);
        }
        foreach (Rejection rejection in this.rejections)
        {
            if (rejection is HypConRejection)
                ((HypConRejection)rejection).PopulateHypotheses(all_hypotheses);
            else if (rejection is HypSetConRejection)
                ((HypSetConRejection)rejection).PopulateHypotheses(all_hypotheses);
            else if (rejection is CausalCycleRejection)
                ((CausalCycleRejection)rejection).PopulateHypotheses(all_hypotheses);
        }
    }

    public void PopulateHypothesisSets(Dictionary<int, HypothesisSet> all_hypothesis_sets)
    {
        foreach (int id in imported_data.accepted_hyp_set_ids)
        {
            this.accepted_hypothesis_sets.Add(id, all_hypothesis_sets[id]);
        }

        foreach (Rejection rejection in this.rejections)
        {
            if (rejection is HypSetConRejection)
                ((HypSetConRejection)rejection).PopulateHypothesisSets(all_hypothesis_sets);
        }
    }

    // Gets all the Rejections for a hypothesis.
    public List<Rejection> GetRejections(Hypothesis hypothesis)
    {
        List<Rejection> return_list = new List<Rejection>();
        foreach (Rejection rejection in this.rejections)
        {
            if (rejection.rejected_hyp == hypothesis)
                return_list.Add(rejection);
        }
        return return_list;
    }

    // Returns whether a Hypothesis was accepted in this Solution or not.
    public bool IsAccepted(Hypothesis hypothesis)
    {
        return this.accepted_hypotheses.ContainsKey(hypothesis.id);
    }

    // Properties
    public SolutionImport ImportedData
    {
        get { return this.imported_data; }
    }
}