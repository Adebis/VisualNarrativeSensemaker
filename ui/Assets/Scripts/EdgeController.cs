using System;
using System.Collections;
using System.Collections.Generic;
using System.Dynamic;
using TMPro;
using Unity.Mathematics;
using UnityEngine;
using UnityEngine.Experimental.GlobalIllumination;
using UnityEngine.EventSystems;
using UnityEngine.Events;

using App = MainApplication;
using System.Linq;

public class EdgeController : MonoBehaviour
{
    // Prefabs
    public GameObject scene_text_prefab;
    public GameObject edge_arrow_prefab;

    // Delegates.
    //public delegate void PointerEnterAction();
    //public delegate void PointerExitAction();

    //public static event PointerEnterAction OnPointerEntered;
    //public static event PointerExitAction OnPointerExited;

    public static System.Action<GameObject> OnMouseEnterAction;
    //public static System.Action<GameObject> OnPointerExitAction;

    private GUIController gui_controller;
    private NodeController source_controller;
    private NodeController target_controller;

    public Edge edge;
    // To view in editor.
    public string edge_label;
    public int edge_id;

    private Hypothesis hypothesis;

    private LineRenderer line_renderer;
    private EdgeCollider2D edge_collider;
    // The Edge's text game object.
    private GameObject text;
    // The Edge's direction arrow game object, if any.
    public GameObject direction_arrow;
    // The line's original color, for when it gets changed.
    public Color original_color;

    // The midpoint that the direction arrow appear at.
    private Vector3 deflected_midpoint;

    public bool focused;
    public bool focus_locked;

    // The multiplier an edge grows to when it's highlighted.
    private float focus_width_multiplier;

    public bool is_canon_hyp;

    // Initialize this edge controller with the edge it represents, as well as
    // the NodeControllers of its start and end nodes.
    public void Initialize(Edge edge, NodeController source_controller, 
        NodeController target_controller, GUIController gui_controller,
        int parallel_edge_count, Hypothesis hypothesis = null)
    {
        this.focus_width_multiplier = 2.0f;

        this.focused = false;
        this.focus_locked = false;
        this.gui_controller = gui_controller;
        this.edge = edge;

        this.hypothesis = hypothesis;
        this.source_controller = source_controller;
        this.target_controller = target_controller;
        this.line_renderer = this.gameObject.GetComponent<LineRenderer>();
        this.direction_arrow = null;

        this.edge_label = edge.ToString();
        this.edge_id = edge.id;
        this.is_canon_hyp = false;

        // Set two points on the line renderer at the source and target node's
        // locations. 
        // Set a mid-point in-between the two endpoints that is deflected perpendicular
        // to the line between the two end-points. The distance the mid point is
        // deflected is based on the number of other parallel edges that already
        // exist between this edge's two endpoints.
        Vector3 source_point = this.source_controller.gameObject.transform.position;
        Vector3 target_point = this.target_controller.gameObject.transform.position;
        Vector3 original_midpoint = (source_point + target_point) / 2;

        // Get the line perpendicular to the one between the source and target points.
        // Z should be the same value for every point.

        // The line from the source point to the target point.
        Vector3 original_line = target_point - source_point;
        // The line perpendicular to the line from source to target points.
        // Set the perp line z to 0 so we're only calculating in 2d.
        Vector3 perp_line = new Vector3(original_line.y,
            original_line.x,
            0);
        // Travel in the direction of the perpendicular line a distance
        // based on the number of parallel edges there are between this
        // edge's two endpoints.
        float deflection_interval = 5f;
        float deflection_distance = deflection_interval * parallel_edge_count;
        this.deflected_midpoint = original_midpoint + perp_line.normalized * deflection_distance;

        this.line_renderer.positionCount = 3;
        Vector3[] node_positions = new Vector3[3]{
            source_point,
            this.deflected_midpoint,
            target_point};
        this.line_renderer.SetPositions(node_positions);
        // Set the same points for the edge collider.
        this.edge_collider = this.gameObject.GetComponent<EdgeCollider2D>();
        List<Vector2> points = new List<Vector2>{
            source_point,
            this.deflected_midpoint,
            target_point};
        this.edge_collider.SetPoints(points);

        // Hypothesized edge.
        if (hypothesis != null)
        {
            // Tell the Hypothesis that this edge controller is controlling it.
            hypothesis.controller = this;
            // Use a different color per hypothesis type.
            // Blue for SameObjectHyp
            if (hypothesis is CausalSequenceHyp)
            {
                // Make a direction arrow and have it point to the target node of this causal sequence hypothesis' scene edge.
                // The scene edge is the hypothesis' leads-to edge, but with scene action nodes instead of concept nodes.
                // This leads-to edge correctly points in the hypothesis' direction, so it doesn't need to be reversed
                // if the direction is backwards.
                Node target_node = ((CausalSequenceHyp)hypothesis).scene_edge.target;
                Node source_node = ((CausalSequenceHyp)hypothesis).scene_edge.source;
                Vector3 target_node_position = target_node.NodeController.transform.position;
                Vector3 source_node_position = source_node.NodeController.transform.position;
                Vector2 direction = target_node_position - source_node_position;
                direction.Normalize();
                float angle = Mathf.Atan2(direction.y, direction.x) * Mathf.Rad2Deg;
                Quaternion rotation = Quaternion.Euler(Vector3.forward * (angle - 90f));
                this.direction_arrow = Instantiate(original: this.edge_arrow_prefab,
                    position: this.deflected_midpoint,
                    rotation: rotation);
                //this.direction_arrow.transform.position = midpoint;
            }
        }

        // Set the line color.
        this.SetLineColor();

        // Place the text slightly below the deflected midpoint.
        this.text = Instantiate(scene_text_prefab,
            new Vector3(this.deflected_midpoint.x, this.deflected_midpoint.y - 10, 0),
            Quaternion.identity);

        // Set the mouseover text.
        this.SetMouseoverText();
    }

    // Clean up all of the edge's related game objects.
    public void Deinitialize()
    {
        // Text
        GameObject.Destroy(this.text);
        this.text = null;
        // Direction arrow
        GameObject.Destroy(this.direction_arrow);
        this.direction_arrow = null;
    }

    // Set things based on the current active solution set. 
    private void SetLineColor()
    {
        this.is_canon_hyp = false;
        // Set the line color for this edge.
        // Set the colors of the line renderer.
        // White
        Color line_color = new Color(0.9f, 0.9f, 0.9f, 1);
        // Hypothesized edge.
        if (hypothesis != null)
        {
            // Use a different color per hypothesis type.
            // Blue for SameObjectHyp
            if (hypothesis is SameObjectHyp)
            {
                line_color = new Color(0, 0, 0.9f, 1);
            }
            // Green for CausalSequenceHyp
            else if (hypothesis is CausalSequenceHyp)
            {
                // Slightly different green if it also has any multi causal path evidence.
                CausalSequenceHyp cs_hyp = (CausalSequenceHyp)hypothesis;
                if (cs_hyp.multi_causal_path_evs.Count > 0)
                    line_color = new Color(0.6f, 0.88f, 0.75f);
                else
                    line_color = new Color(0, 0.9f, 0, 1);
                // Look at its starting and ending images. Normalize them to 0, 1, and 2 by subtracting
                // the lowest image index. If this hyp has the canon score of its pair of images,
                // make it gold; it's a canon sequence hypothesis.
                int lowest_index = App.Instance.sensemaker_data.knowledge_graph.lowest_image_index;
                int start_image_index = cs_hyp.source_action.images.Values.First().index - lowest_index;
                int end_image_index = cs_hyp.target_action.images.Values.First().index - lowest_index;
                float canon_score = float.MaxValue;
                if (start_image_index == 0 && end_image_index == 1)
                {
                    canon_score = App.Instance.canon_0_1_score;
                }
                else if (start_image_index == 1 && end_image_index == 2)
                {
                    canon_score = App.Instance.canon_1_2_score;
                }
                else if (start_image_index == 0 && end_image_index == 2)
                {
                    canon_score = App.Instance.canon_0_2_score;
                }
                float score = cs_hyp.GetScore(App.Instance.active_solution_set, App.Instance.active_solution);
                if (score >= canon_score)
                {
                    // This is a canon hypothesis!
                    // Unless it's a rejected hypothesis.
                    // Check that it's accepted first.
                    if (this.hypothesis.Accepted(App.Instance.active_solution_set, App.Instance.active_solution))
                    {
                        this.is_canon_hyp = true;
                        line_color = new Color(1.0f, 0.84f, 0.0f);
                    }//end if
                }
            }

            // If the hypothesis was accepted, make it fully opaque.
            if (hypothesis.Accepted(App.Instance.active_solution_set.id, App.Instance.active_solution.id))
                line_color.a = 1.0f;
            // Otherwise, make it darker and semi-transparent.
            else
                line_color *= 0.5f;
        }
        this.original_color = line_color;
        this.SetLineColor(this.original_color);
    }
    private void SetMouseoverText()
    {
        string mouseover_text = this.edge.relationship;
        if (this.hypothesis != null)
        {
            mouseover_text += "\nScore: " + this.hypothesis.IndividualScore(App.Instance.active_solution_set.id).ToString();
        }
        this.SetText(mouseover_text);
        this.text.SetActive(false);
    }

    // Update this edge for the current solution set.
    public void UpdateSolutionSet()
    {
        this.SetLineColor();
        this.SetMouseoverText();
    }

    // Start is called before the first frame update
    void Start()
    {
        
    }

    // Update is called once per frame
    void Update()
    {
        
    }

    private void SetText(string text)
    {
        this.text.GetComponent<TextMeshPro>().text = text;
    }

    public void SetLineColor(Color color)
    {
        this.line_renderer.startColor = color;
        this.line_renderer.endColor = color;
    }

    void OnMouseUpAsButton()
    {
        // Lock or unlock this edge as focused.
        this.ToggleFocusLock();
        // Make this edge's nodes match this Edge's focus lock state.
        this.edge.source.NodeController.focus_locked = this.focus_locked;
        this.edge.target.NodeController.focus_locked = this.focus_locked;
    }

    public void ToggleFocusLock()
    {
        // Lock or unlock this edge as focused.
        if (this.focus_locked)
        {
            this.focus_locked = false;
        }
        else
        {
            this.focus_locked = true;
        }
    }

    public void MouseEnter()
    {
        this.Focus();
        // If this is a Hypothesized edge, trigger the focus of every contradicting hypothesis.
        if (this.Hypothesized)
        {
            SolutionSet active_solution_set = App.Instance.active_solution_set;
            Solution active_solution = App.Instance.active_solution;
            foreach (Contradiction contradiction in active_solution_set.GetContradictions(this.hypothesis))
            {
                // Treat each contradiction type differently.
                if (contradiction is InImageTransCon)
                {
                    Hypothesis hyp = ((InImageTransCon)contradiction).GetOtherHypothesis(this.hypothesis);
                    
                    // Set its color to red.
                    // Keep it dim/transparent if it's a rejected hypothesis.
                    Color con_color = new Color(0.9f, 0, 0, 1);
                    if (!active_solution.IsAccepted(hyp))
                    {
                        con_color *= 0.5f;
                    }
                    hyp.controller.SetLineColor(con_color);

                    hyp.controller.Focus();
                }
                else if (contradiction is TweenImageTransCon)
                {
                    Hypothesis hyp = ((TweenImageTransCon)contradiction).GetOtherHypothesis(this.hypothesis);
                    Hypothesis joining_hyp = ((TweenImageTransCon)contradiction).joining_hyp;
                    // Set its color to purple.
                    // Keep it dim/transparent if it's a rejected hypothesis.
                    Color con_color = new Color(0.9f, 0, 0.9f, 1);
                    if (!active_solution.IsAccepted(hyp))
                    {
                        con_color *= 0.5f;
                    }
                    hyp.controller.SetLineColor(con_color);
                    // Set the joining hypothesis to a different color.
                    Color joining_color = new Color(0, 0, 0.9f, 1);
                    if (!active_solution.IsAccepted(joining_hyp))
                    {
                        joining_color *= 0.5f;
                    }
                    joining_hyp.controller.SetLineColor(joining_color);

                    hyp.controller.Focus();
                    joining_hyp.controller.Focus();
                }
                else if (contradiction is CausalHypFlowCon)
                {
                    Hypothesis other_hyp = ((CausalHypFlowCon)contradiction).GetOtherHypothesis(this.hypothesis);

                    // Set its color to red.
                    // Keep it dim/transparent if it's a rejected hypothesis.
                    Color con_color = new Color(0.9f, 0, 0, 1);
                    if (!active_solution.IsAccepted(other_hyp))
                    {
                        con_color *= 0.5f;
                    }
                    other_hyp.controller.SetLineColor(con_color);

                    other_hyp.controller.Focus();
                }
            }
        }

        // Invoke MouseEnterAction functions.
        if (OnMouseEnterAction != null)
        {
            OnMouseEnterAction.Invoke(this.gameObject);
        }

    }

    public void MouseExit()
    {
        this.Unfocus();
        // If this is a Hypothesized edge, trigger the unfocus of every contradicting hypothesis.
        if (this.Hypothesized)
        {
            SolutionSet active_solution_set = App.Instance.active_solution_set;
            foreach (Contradiction contradiction in active_solution_set.GetContradictions(edge.hypothesis))
            {
                if (contradiction is HypothesisCon)
                {
                    Hypothesis other_hyp = ((HypothesisCon)contradiction).GetOtherHypothesis(this.hypothesis);
                    // Treat each contradiction type differently.
                    if (contradiction is InImageTransCon)
                    {
                        other_hyp.controller.SetLineColor(other_hyp.controller.original_color);
                        other_hyp.controller.Unfocus();
                    }
                    else if (contradiction is TweenImageTransCon)
                    {
                        Hypothesis joining_hyp = ((TweenImageTransCon)contradiction).joining_hyp;
                        other_hyp.controller.SetLineColor(other_hyp.controller.original_color);
                        joining_hyp.controller.SetLineColor(joining_hyp.controller.original_color);
                        other_hyp.controller.Unfocus();
                        joining_hyp.controller.Unfocus();
                    }
                    else if (contradiction is CausalHypFlowCon)
                    {
                        other_hyp.controller.SetLineColor(other_hyp.controller.original_color);
                        other_hyp.controller.Unfocus();
                    }
                }
            }
        }
    }

    // Focus this edge.
    public void Focus()
    {
        print("Focusing edge " + this.edge.ToString());
        // Trigger the mouse enter of the nodes this edge connects to as well.
        this.edge.source.NodeController.MouseEnter();
        this.edge.target.NodeController.MouseEnter();
        // Reveal the edge's text.
        this.text.SetActive(true);
        // Show the edge's info in the info box. 
        //string info_text = this.edge.ToString();
        string mouseover_text = this.edge.relationship;
        if (!(this.hypothesis is null))
        {
            //float score = this.hypothesis.GetScore(App.Instance.active_solution_set, App.Instance.active_solution);
            //info_text += $"\nScore: {score}";
            mouseover_text += $"\nScore: {this.GetHypothesisMouseoverScoreText()}";
        }
        //this.gui_controller.SetInfoText(info_text);
        this.SetText(mouseover_text);

            // Make the edge thicker.
        this.line_renderer.widthMultiplier = this.focus_width_multiplier;

        // Flag that the edge is focused.
        this.focused = true;
    }

    private string GetHypothesisMouseoverScoreText()
    {
        string score_text = "";

        if (this.hypothesis is null)
        {
            return "";
        }

        SolutionSet solution_set = App.Instance.active_solution_set;
        Solution solution = App.Instance.active_solution;

        // Make different score text for each type of hypothesis.
        if (this.hypothesis is SameObjectHyp)
        {
            var hyp = (SameObjectHyp)this.hypothesis;
            // Total individual score.
            score_text += $"{hyp.GetIndividualScore(solution_set, solution)}" + "\n";
        }
        else if (this.hypothesis is CausalSequenceHyp)
        {
            var hyp = (CausalSequenceHyp)this.hypothesis;
            // Total individual score + continuity score.
            score_text += $"{hyp.GetScore(solution_set, solution)}" + "\n";
        }

        score_text.TrimEnd('\n');

        return score_text;
    }

    // Make and return the score text for this edge's hypothesis.
    public string GetHypothesisInfoScoreText()
    {
        string score_text = "";

        if (this.hypothesis is null)
        {
            return "";
        }

        SolutionSet solution_set = App.Instance.active_solution_set;
        Solution solution = App.Instance.active_solution;
        KnowledgeGraph knowledge_graph = App.Instance.sensemaker_data.knowledge_graph;

        // Make different score text for each type of hypothesis.
        if (this.hypothesis is SameObjectHyp)
        {
            var hyp = (SameObjectHyp)this.hypothesis;
            // Total individual score.
            score_text += $"Total score: {hyp.GetIndividualScore(solution_set, solution)}" + "\n";

            // All hypotheses have a density component to their score.
            // Each hypothesis increases density by 2 / (n * (n - 1)).
            // Get the number of instances from the knowledge graph. This is n.
            int n = knowledge_graph.instance_count;
            float density_increase = 2.0f / (n * (n - 1));
            float density_score = density_increase * solution.parameter_set.density_weight;

            // Density score, with raw score and density weight.
            score_text += ($"Density score: {density_score}"
                + $" (raw score: {density_increase}, weight: {solution.parameter_set.density_weight})"
                + "\n");

            // Visual similarity score. (with raw score and visual_sim_ev_weight)
            score_text += ($"VisualSimilarity score: {hyp.GetVisualSimilarityScore(solution_set, solution)} " +
                $"(raw score: {hyp.GetRawVisualSimilarityScore()}, weight: {solution.parameter_set.visual_sim_ev_weight})" + 
                "\n");

            // Attribute similarity score. (with raw score and attribute_sim_ev_weight)
            score_text += ($"AttributeSimilarity score: {hyp.GetAttributeSimilarityScore(solution_set, solution)} " +
                $"(raw score: {hyp.GetRawAttributeSimilarityScore()}, weight: {solution.parameter_set.attribute_sim_ev_weight})" + 
                "\n");
        }
        else if (this.hypothesis is CausalSequenceHyp)
        {
            var hyp = (CausalSequenceHyp)this.hypothesis;
            // Total individual score + continuity score.
             score_text += $"Total score: {hyp.GetScore(solution_set, solution)}" + "\n";

            // All hypotheses have a density component to their score.
            // Each hypothesis increases density by 2 / (n * (n - 1)).
            // Get the number of instances from the knowledge graph. This is n.
            int n = knowledge_graph.instance_count;
            float density_increase = 2 / (n * (n - 1));
            float density_score = density_increase * solution.parameter_set.density_weight;

            // Density score, with raw score and density weight.
            score_text += ($"Density score: {density_score}"
                + $" (raw score: {density_increase}, weight: {solution.parameter_set.density_weight})"
                + "\n");

            // Total causal path score. (with causal_path_ev_weight)
            score_text += ($"CausalPath score: {hyp.GetCausalPathScore(solution_set, solution)} " +
                $"(raw score: {hyp.GetRawCausalPathScore()}, weight: {solution.parameter_set.causal_path_ev_weight})" +
                $"\n");

            // Individual causal path evidence scores.

            // Continuity score. (with continuity_ev_weight)
            score_text += ($"Continuity score: {hyp.GetContinuityScore(solution_set, solution)} " +
                $"(raw score: {hyp.GetRawContinuityScore()}, weight: {solution.parameter_set.continuity_ev_weight})" +
                $"\n");

            // Affect curve score.
            score_text += ($"Affect curve score: {hyp.affect_curve_scores[solution.parameter_set.id]}");
        }

        score_text.TrimEnd('\n');

        return score_text;
    }

    // Unfocus this edge.
    public void Unfocus()
    {
        // If the edge is locked as focused, don't unfocus it.
        if (this.focus_locked)
        {
            return;
        }
        // Trigger the mouse exit of the nodes this edge connects to as well.
        this.edge.source.NodeController.MouseExit();
        this.edge.target.NodeController.MouseExit();
        // Hide the edge's text.
        this.text.SetActive(false);
        // Return the edge's width to default.
        this.line_renderer.widthMultiplier = 1.0f;

        // Flag that the node is not focused.
        this.focused = false;
    }

    // Properties
    // Whether or not this edge controller's edge is made from a hypothesis.
    public bool Hypothesized
    {
        get { return (this.hypothesis != null ? true : false); }
    }
    public Hypothesis Hypothesis
    {
        get { return this.hypothesis; }
    }
    public int StartImageIndex
    {
        get 
        { 
            if (this.hypothesis != null)
            {
                int start_image_index = -1;
                if (this.hypothesis is CausalSequenceHyp)
                {
                    CausalSequenceHyp cs_hyp = (CausalSequenceHyp)this.hypothesis;
                    start_image_index = cs_hyp.source_action.images.Values.First().index;
                }
                else if (this.hypothesis is SameObjectHyp)
                {
                    SameObjectHyp so_hyp = (SameObjectHyp)this.hypothesis;
                    start_image_index = so_hyp.object_1.images.Values.First().index;
                }
                return start_image_index;
            }
            else
            {
                return -1;
            }
        }
    }
    public int EndImageIndex
    {
        get
        {
            if (this.hypothesis != null)
            {
                int start_image_index = -1;
                if (this.hypothesis is CausalSequenceHyp)
                {
                    CausalSequenceHyp cs_hyp = (CausalSequenceHyp)this.hypothesis;
                    start_image_index = cs_hyp.target_action.images.Values.First().index;
                }
                else if (this.hypothesis is SameObjectHyp)
                {
                    SameObjectHyp so_hyp = (SameObjectHyp)this.hypothesis;
                    start_image_index = so_hyp.object_2.images.Values.First().index;
                }
                return start_image_index;
            }
            else
            {
                return -1;
            }
        }
    }
}
