using Newtonsoft.Json.Linq;
using System;
using System.Collections;
using System.Collections.Generic;
using Unity.VisualScripting;
using UnityEditor.UI;
using UnityEngine;
using UnityEngine.UIElements;

using App = MainApplication;

public class Evidence
{
    private EvidenceImport imported_data;

    public int id;
    public float score;

    public Evidence(EvidenceImport imported_data)
    {
        this.imported_data = imported_data;

        this.id = imported_data.id;
        this.score = imported_data.score;
    }

    // Returns this evidence's score according to a given solution.
    public virtual float GetWeightedScore(SolutionSet solution_set, Solution solution)
    {
        return this.score;
    }

    // Returns this evidence's score without influence from a given solution.
    public float GetRawScore()
    {
        return this.score;
    }

    // Properties
    public EvidenceImport ImportedData
    {
        get { return this.imported_data; }
    }
}

public class VisualSimEv : Evidence
{
    public ObjectNode object_1;
    public ObjectNode object_2;

    public VisualSimEv(VisualSimEvImport imported_data) : base(imported_data)
    {

    }

    public void PopulateNodes(Dictionary<int, Node> all_nodes)
    {
        this.object_1 = (ObjectNode)all_nodes[this.ImportedData.object_1_id];
        this.object_2 = (ObjectNode)all_nodes[this.ImportedData.object_2_id];
    }

    // Returns the base score times the solution's parameter set's visual_sim_ev_weight.
    public override float GetWeightedScore(SolutionSet solution_set, Solution solution)
    {
        float score = this.score * solution.parameter_set.visual_sim_ev_weight;

        return score;
    }

    // Properties
    public new VisualSimEvImport ImportedData
    {
        get { return (VisualSimEvImport)base.ImportedData; }
    }
}

public class AttributeSimEv : Evidence
{
    public ObjectNode object_1;
    public ObjectNode object_2;

    public AttributeSimEv(AttributeSimEvImport imported_data) : base(imported_data)
    {

    }

    public void PopulateNodes(Dictionary<int, Node> all_nodes)
    {
        this.object_1 = (ObjectNode)all_nodes[this.ImportedData.object_1_id];
        this.object_2 = (ObjectNode)all_nodes[this.ImportedData.object_2_id];
    }

    // Returns the base score times the solution's parameter set's attribute_sim_ev_weight.
    public override float GetWeightedScore(SolutionSet solution_set, Solution solution)
    {
        float score = this.score * solution.parameter_set.attribute_sim_ev_weight;

        return score;
    }

    // Properties
    public new AttributeSimEvImport ImportedData
    {
        get { return (AttributeSimEvImport)base.ImportedData; }
    }
}

public class CausalPathEv : Evidence
{
    public ActionNode source_action;
    public ActionNode target_action;
    public ConceptNode source_concept;
    public ConceptNode target_concept;
    public GraphPath concept_path;
    public string direction;

    public CausalPathEv(CausalPathEvImport imported_data) : base(imported_data)
    {
        this.concept_path = new GraphPath(imported_data.concept_path);
        this.direction = imported_data.direction;
    }

    public void PopulateNodes(Dictionary<int, Node> all_nodes)
    {
        this.source_action = (ActionNode)all_nodes[this.ImportedData.source_action_id];
        this.target_action = (ActionNode)all_nodes[this.ImportedData.target_action_id];
        this.source_concept = (ConceptNode)all_nodes[this.ImportedData.source_concept_id];
        this.target_concept = (ConceptNode)all_nodes[this.ImportedData.target_concept_id];
        this.concept_path.PopulateNodes(all_nodes);
    }

    public void PopulateEdges(Dictionary<int, Edge> all_edges)
    {
        this.concept_path.PopulateEdges(all_edges);
    }

    // Returns the base score times the solution's parameter set's causal_path_ev_weight.
    public override float GetWeightedScore(SolutionSet solution_set, Solution solution)
    {
        float score = this.score * solution.parameter_set.causal_path_ev_weight;

        return score;
    }

    // Properties
    public new CausalPathEvImport ImportedData
    {
        get { return (CausalPathEvImport)base.ImportedData; }
    }
}

public class MultiCausalPathEv : Evidence
{
    public ActionNode source_action;
    public ActionNode target_action;
    public List<ConceptNode> source_concepts;
    public List<ConceptNode> target_concepts;
    public MultiGraphPath concept_path;
    public string direction;

    public MultiCausalPathEv(MultiCausalPathEvImport imported_data) : base(imported_data)
    {
        this.source_concepts = new List<ConceptNode>();
        this.target_concepts = new List<ConceptNode>();
        this.concept_path = new MultiGraphPath(imported_data.concept_path);
        this.direction = imported_data.direction;
    }

    public void PopulateNodes(Dictionary<int, Node> all_nodes)
    {
        this.source_action = (ActionNode)all_nodes[this.ImportedData.source_action_id];
        this.target_action = (ActionNode)all_nodes[this.ImportedData.target_action_id];

        foreach (int concept_id in this.ImportedData.source_concept_ids)
        {
            this.source_concepts.Add((ConceptNode)all_nodes[concept_id]);
        }
        foreach (int concept_id in this.ImportedData.target_concept_ids)
        {
            this.target_concepts.Add((ConceptNode)all_nodes[concept_id]);
        }

        this.concept_path.PopulateNodes(all_nodes);
    }

    public void PopulateEdges(Dictionary<int, Edge> all_edges)
    {
        this.concept_path.PopulateEdges(all_edges);
    }

    // Returns the base score times the solution's parameter set's causal_path_ev_weight.
    public override float GetWeightedScore(SolutionSet solution_set, Solution solution)
    {
        float score = this.score * solution.parameter_set.causal_path_ev_weight;

        return score;
    }

    public override string ToString()
    {
        string return_string = "";

        return_string = $"Score: {this.score}. Path:\n";
        return_string = this.concept_path.ToString();

        return return_string;
    }

    // Properties
    public new MultiCausalPathEvImport ImportedData
    {
        get { return (MultiCausalPathEvImport)base.ImportedData; }
    }
}

public class ContinuityEv : Evidence
{
    public ActionNode source_action;
    public ActionNode target_action;
    public ObjectNode source_object;
    public ObjectNode target_object;
    public SameObjectHyp joining_hyp;

    public ContinuityEv(ContinuityEvImport imported_data) : base(imported_data)
    {

    }

    public void PopulateNodes(Dictionary<int, Node> all_nodes)
    {
        this.source_action = (ActionNode)all_nodes[this.ImportedData.source_action_id];
        this.target_action = (ActionNode)all_nodes[this.ImportedData.target_action_id];
        this.source_object = (ObjectNode)all_nodes[this.ImportedData.source_object_id];
        this.target_object = (ObjectNode)all_nodes[this.ImportedData.target_object_id];
    }

    public void PopulateHypotheses(Dictionary<int, Hypothesis> all_hypotheses)
    {
        this.joining_hyp = (SameObjectHyp)all_hypotheses[this.ImportedData.joining_hyp_id];
    }


    public override float GetWeightedScore(SolutionSet solution_set, Solution solution)
    {
        float return_score = 0;
        // If the joining hypothesis was accepted, add 1.
        if (solution.accepted_hypotheses.ContainsKey(this.joining_hyp.id))
        {
            //return_score += this.joining_hyp.GetScore(solution_set, solution);
            return_score += 1;
        }
        // Multiply by the continuity_ev_weight.
        return_score *= solution.parameter_set.continuity_ev_weight;
        return return_score;
    }

    public new float GetRawScore()
    {
        // Return the raw scores of the joining hypothesis.
        float return_score = 0;

        return_score += this.joining_hyp.GetRawVisualSimilarityScore();
        return_score += this.joining_hyp.GetRawAttributeSimilarityScore();

        return return_score;
    }

    // Properties
    public new ContinuityEvImport ImportedData
    {
        get { return (ContinuityEvImport)base.ImportedData; }
    }
}

public class Hypothesis
{
    private HypothesisImport imported_data;

    public int id;
    public string name;
    public List<int> premise_ids;

    public Dictionary<int, Hypothesis> premises;

    // All of the contradictions that the hypothesis is incident on.
    // Keyed by parameter set id, then solution id.
    public Dictionary<int, List<Contradiction>> contradictions;

    // Whether or not this hypothesis was accepted in a solution set and solution.
    // Keyed by tuple of solution set ID and solution ID.
    private Dictionary<Tuple<int, int>, bool> accepted;
    // What individual score this Hypothesis got in a solution set.
    // Keyed by solution set ID.
    private Dictionary<int, float> individual_score;

    // The EdgeController controlling this hypothesis' edge, if any.
    public EdgeController controller;

    public Hypothesis(HypothesisImport imported_data)
    {
        this.imported_data = imported_data;

        this.id = imported_data.id;
        this.name = imported_data.name;
        this.premise_ids = new List<int>(imported_data.premise_ids);


        this.premises = new Dictionary<int, Hypothesis>();

        this.accepted = new Dictionary<Tuple<int, int>, bool>();
        this.individual_score = new Dictionary<int, float>();
        this.contradictions = new Dictionary<int, List<Contradiction>>();

        this.controller = null;
    }

    public void PopulateContradictions(Dictionary<int, SolutionSet> solution_sets)
    {
        foreach (int image_set_id in solution_sets.Keys) 
        {
            SolutionSet solution_set = solution_sets[image_set_id];
            List<Contradiction> contradiction_list = new List<Contradiction>();
            foreach (Contradiction contradiction in solution_set.contradictions)
            {
                if (contradiction.HasHypothesis(this))
                    contradiction_list.Add(contradiction);
            }
            this.contradictions[solution_set.id] = contradiction_list;
        }
    }

    public void PopulateSolutionSets(Dictionary<int, SolutionSet> all_solution_sets)
    {
        foreach (SolutionSet solution_set in all_solution_sets.Values)
        {
            this.individual_score[solution_set.id] = solution_set.individual_scores[this.id];
            foreach (Solution solution in solution_set.solutions)
            {
                if (solution.accepted_hypotheses.ContainsKey(this.id))
                    this.accepted[new Tuple<int, int>(solution_set.id, solution.id)] = true;
                else
                    this.accepted[new Tuple<int, int>(solution_set.id, solution.id)] = false;
            }
        }
    }

    public bool Accepted(SolutionSet solution_set, Solution solution)
    {
        return this.Accepted(solution_set.id, solution.id);
    }
    public bool Accepted(int solution_set_id, int solution_id)
    {
        return this.accepted[new Tuple<int, int>(solution_set_id, solution_id)];
    }

    public float IndividualScore(int solution_set_id)
    {
        return this.individual_score[solution_set_id];
    }

    // Gets this hypothesis' score in the given SolutionSet and Solution.
    public virtual float GetScore(SolutionSet solution_set, Solution solution)
    {
        return -10000000;
    }

    // Get the ID in an ID pair which does not match the one passed in.
    private int GetOtherID(HashSet<int> id_pair, int id)
    {
        foreach (int id_item in id_pair)
        {
            if (id_item != id)
                return id_item;
        }
        return id;
    }

    // Gets a list of the Contradictions that this hypothesis and the hypothesis
    // passed in share together.
    public List<Contradiction> GetSharedContradictions(Hypothesis other_hypothesis)
    {
        var cons = new List<Contradiction>();
        foreach (Contradiction contradiction in this.AllContradictions)
        {
            if (contradiction.HasHypothesis(this) && contradiction.HasHypothesis(other_hypothesis))
            {
                cons.Add(contradiction);
            }
        }
        return cons;
    }

    // Properties
    // Gets a list of the hypotheses that contradict this hypothesis.


    // Properties
    public HypothesisImport ImportedData
    {
        get { return this.imported_data; }
    }
    public List<Contradiction> AllContradictions
    {
        get
        {
            List<Contradiction> all_contradictions = new List<Contradiction>();
            foreach (int image_set_id in this.contradictions.Keys)
            {
                all_contradictions.AddRange(this.contradictions[image_set_id]);
            }
            return all_contradictions;
        }
    }
    public virtual List<Evidence> AllEvidence
    {
        get { return new List<Evidence>(); }
    }
}

public class SameObjectHyp : Hypothesis
{
    public ObjectNode object_1;
    public ObjectNode object_2;
    public Edge edge;
    public VisualSimEv visual_sim_ev;
    public AttributeSimEv attribute_sim_ev;

    public SameObjectHyp(SameObjectHypImport imported_data) : base(imported_data)
    {
        this.visual_sim_ev = new VisualSimEv(imported_data.visual_sim_ev);
        this.attribute_sim_ev = new AttributeSimEv(imported_data.attribute_sim_ev);
        this.edge = new Edge(imported_data.edge, hypothesis: this);
    }

    public void PopulateNodes(Dictionary<int, Node> all_nodes)
    {
        this.object_1 = (ObjectNode)all_nodes[this.ImportedData.object_1_id];
        this.object_2 = (ObjectNode)all_nodes[this.ImportedData.object_2_id];
        this.edge.PopulateNodes(all_nodes);
        this.visual_sim_ev.PopulateNodes(all_nodes);
        this.attribute_sim_ev.PopulateNodes(all_nodes);
    }

    public void PopulateCommonSenseEdges(Dictionary<int, CommonSenseEdge> all_commonsense_edges)
    {
        this.edge.PopulateCommonSenseEdges(all_commonsense_edges);
    }

    public override float GetScore(SolutionSet solution_set, Solution solution)
    {
        float return_score = 0;
        return_score += this.visual_sim_ev.GetWeightedScore(solution_set, solution);
        return_score += this.attribute_sim_ev.GetWeightedScore(solution_set, solution);
        return return_score;
    }

    public float GetIndividualScore(SolutionSet solution_set, Solution solution)
    {
        float individual_score = 0;
        individual_score += this.GetVisualSimilarityScore(solution_set, solution);
        individual_score += this.GetAttributeSimilarityScore(solution_set, solution);
        return individual_score;
    }

    public float GetVisualSimilarityScore(SolutionSet solution_set, Solution solution)
    {
        return this.visual_sim_ev.GetWeightedScore(solution_set, solution);
    }
    public float GetRawVisualSimilarityScore()
    {
        return this.visual_sim_ev.GetRawScore();
    }

    public float GetAttributeSimilarityScore(SolutionSet solution_set, Solution solution)
    {
        return this.attribute_sim_ev.GetWeightedScore(solution_set, solution);
    }
    public float GetRawAttributeSimilarityScore()
    {
        return this.attribute_sim_ev.GetRawScore();
    }

    public override string ToString()
    {
        string to_string = "Hypothesis " + this.id.ToString() + ": " + this.object_1.name + " is "
            + this.object_2.name + ". Score: " + this.IndividualScore(App.Instance.active_solution_set.id).ToString()
            + ". Accepted: " + this.Accepted(App.Instance.active_solution_set.id, App.Instance.active_solution.id).ToString();

        return to_string;
    }

    // Properties
    public new SameObjectHypImport ImportedData
    {
        get { return (SameObjectHypImport)base.ImportedData; }
    }
    public override List<Evidence> AllEvidence
    {
        get 
        {
            return new List<Evidence>() {this.visual_sim_ev, this.attribute_sim_ev};
        }
    }
}

public class CausalSequenceHyp : Hypothesis
{
    public ActionNode source_action;
    public ActionNode target_action;
    public Edge edge;
    // The causal path edge with the source and target actions as its
    // endpoints instead of concept nodes.
    public Edge scene_edge;
    public List<CausalPathEv> causal_path_evs;
    public List<MultiCausalPathEv> multi_causal_path_evs;
    public List<ContinuityEv> continuity_evs;
    public string direction;
    public Dictionary<int, float> affect_curve_scores;

    public CausalSequenceHyp(CausalSequenceHypImport imported_data) : base(imported_data)
    {
        this.causal_path_evs = new List<CausalPathEv>();
        foreach (CausalPathEvImport data in imported_data.causal_path_evs)
        {
            this.causal_path_evs.Add(new CausalPathEv(data));
        }
        this.multi_causal_path_evs = new List<MultiCausalPathEv>();
        foreach (MultiCausalPathEvImport data in imported_data.multi_causal_path_evs)
        {
            this.multi_causal_path_evs.Add(new MultiCausalPathEv(data));
        }
        this.continuity_evs = new List<ContinuityEv>();
        foreach (ContinuityEvImport data in imported_data.continuity_evs)
        {
            this.continuity_evs.Add(new ContinuityEv(data));
        }
        this.edge = new Edge(imported_data.edge, hypothesis: this);
        this.scene_edge = new Edge(imported_data.edge, hypothesis: this);
        this.direction = imported_data.direction;
        // Resolve string parameterset id keys into ints.
        this.affect_curve_scores = new Dictionary<int, float>();
        foreach (AffectCurveScoresImport acs_import in imported_data.affect_curve_scores)
        {
            this.affect_curve_scores[acs_import.pset_id] = acs_import.score;
        }
    }

    public void PopulateNodes(Dictionary<int, Node> all_nodes)
    {
        this.source_action = (ActionNode)all_nodes[this.ImportedData.source_action_id];
        this.target_action = (ActionNode)all_nodes[this.ImportedData.target_action_id];
        this.edge.PopulateNodes(all_nodes);
        // Flip the source and targets of the scene edge if this hypothesis' direction is backwards.
        if (this.direction == "CausalFlowDirection.BACKWARD")
        {
            this.scene_edge.source = this.target_action;
            this.scene_edge.target = this.source_action;
        }
        else
        {
            this.scene_edge.source = this.source_action;
            this.scene_edge.target = this.target_action;
        }

        foreach (CausalPathEv ev in this.causal_path_evs)
        {
            ev.PopulateNodes(all_nodes);
        }
        foreach (MultiCausalPathEv ev in this.multi_causal_path_evs)
        {
            ev.PopulateNodes(all_nodes);
        }
        foreach (ContinuityEv ev in this.continuity_evs)
        {
            ev.PopulateNodes(all_nodes);
        }
    }

    public void PopulateEdges(Dictionary<int, Edge> all_edges)
    {
        foreach (CausalPathEv ev in this.causal_path_evs)
        {
            ev.PopulateEdges(all_edges);
        }
        foreach (MultiCausalPathEv ev in this.multi_causal_path_evs)
        {
            ev.PopulateEdges(all_edges);
        }
    }

    public void PopulateHypotheses(Dictionary<int, Hypothesis> all_hypotheses)
    {
        foreach (ContinuityEv ev in this.continuity_evs)
        {
            ev.PopulateHypotheses(all_hypotheses);
        }
    }

    public void PopulateCommonSenseEdges(Dictionary<int, CommonSenseEdge> all_commonsense_edges)
    { 
        this.edge.PopulateCommonSenseEdges(all_commonsense_edges);
        this.scene_edge.PopulateCommonSenseEdges(all_commonsense_edges);
    }

    public override float GetScore(SolutionSet solution_set, Solution solution)
    {
        float return_score = 0;
        foreach(CausalPathEv ev in this.causal_path_evs)
        {
            return_score += ev.GetWeightedScore(solution_set, solution);
        }
        foreach(ContinuityEv ev in this.continuity_evs)
        {
            return_score += ev.GetWeightedScore(solution_set, solution);
        }
        foreach (MultiCausalPathEv ev in this.multi_causal_path_evs)
        {
            return_score += ev.GetWeightedScore(solution_set, solution);
        }
        // Add affect curve score.
        return_score += this.affect_curve_scores[solution.parameter_set.id];
        return return_score;
    }

    /*
    public float GetTotalScore(SolutionSet solution_set, Solution solution)
    {
        float total_score = 0;
        total_score += this.GetCausalPathScore(solution_set, solution);
        total_score += this.GetContinuityScore(solution_set, solution);
        return total_score;
    }
    */

    public float GetCausalPathScore(SolutionSet solution_set, Solution solution)
    {
        float total_score = 0;
        foreach (CausalPathEv ev in this.causal_path_evs)
        {
            total_score += ev.GetWeightedScore(solution_set, solution);
        }
        foreach (MultiCausalPathEv ev in this.multi_causal_path_evs)
        {
            total_score += ev.GetWeightedScore(solution_set, solution);
        }
        return total_score;
    }
    public float GetRawCausalPathScore()
    {
        float total_score = 0;
        foreach (CausalPathEv ev in this.causal_path_evs)
        {
            total_score += ev.GetRawScore();
        }
        foreach (MultiCausalPathEv ev in this.multi_causal_path_evs)
        {
            total_score += ev.GetRawScore();
        }
        return total_score;
    }

    public float GetContinuityScore(SolutionSet solution_set, Solution solution)
    {
        float total_score = 0;
        foreach (ContinuityEv ev in this.continuity_evs)
        {
            total_score += ev.GetWeightedScore(solution_set, solution);
        }
        return total_score;
    }
    public float GetRawContinuityScore()
    {
        float total_score = 0;
        foreach (ContinuityEv ev in this.continuity_evs)
        {
            total_score += ev.GetRawScore();
        }
        return total_score;
    }

    // Properties
    public new CausalSequenceHypImport ImportedData
    {
        get { return (CausalSequenceHypImport)base.ImportedData; }
    }
    public override List<Evidence> AllEvidence
    {
        get 
        {
            List<Evidence> all_evidence = new List<Evidence>();
            all_evidence.AddRange(this.causal_path_evs);
            all_evidence.AddRange(this.multi_causal_path_evs);
            all_evidence.AddRange(this.continuity_evs);
            return all_evidence;
        }
    }
}

public class HypothesisSet
{
    private HypothesisSetImport imported_data;

    public int id;
    public Dictionary<int, Hypothesis> hypotheses;
    public bool is_all_or_ex;

    public HypothesisSet(HypothesisSetImport imported_data)
    {
        this.imported_data = imported_data;
        this.id = imported_data.id;
        this.is_all_or_ex = imported_data.is_all_or_ex;
        this.hypotheses = new Dictionary<int, Hypothesis>();
    }

    public void PopulateHypotheses(Dictionary<int, Hypothesis> all_hypotheses)
    {
        foreach (int hypothesis_id in this.imported_data.hypothesis_ids)
        {
            this.hypotheses[hypothesis_id] = all_hypotheses[hypothesis_id];
        }
    }

    public bool HasHypothesis(Hypothesis hyp)
    {
        if (this.hypotheses.ContainsKey(hyp.id))
            return true;
        else
            return false;
    }

    // Properties
    public HypothesisSetImport ImportedData
    {
        get { return this.imported_data; }
    }
}

public class CausalHypChain : HypothesisSet
{
    public List<int> hyp_id_sequence;

    public CausalHypChain(CausalHypChainImport imported_data) : base(imported_data)
    {
        this.hyp_id_sequence = new List<int>();
        foreach (int hyp_id in imported_data.hyp_id_sequence)
        {
            this.hyp_id_sequence.Add(hyp_id);
        }
    }

    // Properties
    public new CausalHypChainImport ImportedData
    {
        get { return (CausalHypChainImport)base.ImportedData; }
    }
}