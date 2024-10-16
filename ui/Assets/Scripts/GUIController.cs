using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

using App = MainApplication;

public class GUIController : MonoBehaviour
{

    // UI Elements from the editor.
    public Canvas ui_canvas;

    // UI Elements fetched programmatically.
    // NOTE: The Panel UI element is actually a game object with a rect
    // transform and an Image component.
    private GameObject control_panel;
    private Toggle hypothesized_toggle;

    private GameObject info_canvas;

    private GameObject setup_menu;

    // For GUI elements.
    private GUIStyle info_box_style;

    private string info_text = "";

    // Variables for the Update loop
    GameObject last_moused_over_object = null;
    GameObject last_clicked_object = null;

    // Used in callback function.
    GameObject last_moused_over_info_object = null;

    private bool canon_only = false;
    private bool neighbor_only = false;

    void Start()
    {
        this.info_text = "";
        this.info_box_style = new GUIStyle();

        // Get the UI elements.
        // The control panel.
        this.control_panel = ui_canvas.gameObject.transform.Find("ControlPanel").gameObject;
        // The control panel's toggles.
        this.hypothesized_toggle = this.control_panel.transform.Find("HypothesizedToggle").gameObject.GetComponent<Toggle>();
        this.hypothesized_toggle.onValueChanged.AddListener(delegate { HypothesizedToggleChanged(this.hypothesized_toggle); });
        // Disable the control panel initially.
        this.control_panel.SetActive(false);

        // The info canvas.
        this.info_canvas = ui_canvas.gameObject.transform.Find("InfoCanvas").gameObject;
        // Disable the info canvas initially.
        this.info_canvas.SetActive(false);

        // The setup menu.
        this.setup_menu = ui_canvas.gameObject.transform.Find("SetupMenu").gameObject;

        // Whether we're only showing canon causal hypotheses.
        this.canon_only = false;
        this.neighbor_only = false;
    }


    private void Update()
    {
        // Raycast a point down from the mouse's location.
        Vector2 mouse_origin = App.Instance.main_camera.ScreenToWorldPoint(Input.mousePosition);
        RaycastHit2D hit = Physics2D.Raycast(mouse_origin, Vector2.zero);
        GameObject moused_over_object = null;
        if (!(hit.transform is null))
        {
            Transform object_hit = hit.transform;
            moused_over_object = object_hit.gameObject;
            //print("Object hit: " + object_hit.name);
            // Check if it's a node.
            if (!(moused_over_object.GetComponent<NodeController>() is null))
            {
                moused_over_object.GetComponent<NodeController>().MouseEnter();
                Node moused_over_node = moused_over_object.GetComponent<NodeController>().node;
                // Display some info in the info canvas about this node. 
                string info_text = ($"Node {moused_over_node.name}");
                if (moused_over_node is ActionNode)
                {
                    ActionNode action_node = (ActionNode)moused_over_node;
                    info_text += ($"\nSentiment: {action_node.concept_nodes.Values.First().sentiment}");
                }
                this.SetInfoCanvasText(info_text);
            }
            else if (!(moused_over_object.GetComponent<EdgeController>() is null))
            {
                moused_over_object.GetComponent<EdgeController>().MouseEnter();
            }//end else if
        }

        if (!(this.last_moused_over_object is null) && !(this.last_moused_over_object == moused_over_object))
        {
            if (!(this.last_moused_over_object.GetComponent<NodeController>() is null))
            {
                this.last_moused_over_object.GetComponent<NodeController>().MouseExit();
            }
            else if (!(this.last_moused_over_object.GetComponent<EdgeController>() is null))
            {
                this.last_moused_over_object.GetComponent<EdgeController>().MouseExit();
            }//end else if
        }
        this.last_moused_over_object = moused_over_object;

        // Handle mouse clicks. 
        if (Input.GetMouseButtonUp(0))
        {
            if (!(this.last_moused_over_object is null))
            {
                GameObject clicked_object = this.last_moused_over_object;

                // If the currently clicked object is a hypothesized edge that was rejected,
                // show in info_text the reason for its rejection.
                if (!(clicked_object is null))
                {
                    if (this.IsEdge(clicked_object) && clicked_object.GetComponent<EdgeController>().Hypothesized)
                    {
                        Hypothesis hyp = clicked_object.GetComponent<EdgeController>().Hypothesis;
                        string info_text = "";
                        if (!hyp.Accepted(App.Instance.active_solution_set.id, App.Instance.active_solution.id))
                        {
                            info_text = "Rejection explanations: ";
                            // Get the rejections and explanations from the active solution
                            // for this hypothesis.
                            foreach (Rejection rejection in App.Instance.active_solution.GetRejections(hyp))
                            {
                                info_text += rejection.explanation + "\n";
                            }

                            this.SetInfoText(info_text);
                        }
                    }
                }

                // If there is a last clicked object, see what the currently clicked
                // object is and do something specific to the combinations of objects
                // last clicked and currently clicked.
                if (!(clicked_object is null) && !(this.last_clicked_object is null))
                {
                    // If they're both hypothesis edges, show information about them.
                    if (this.IsEdge(last_clicked_object) && this.IsEdge(clicked_object)
                        && last_clicked_object.GetComponent<EdgeController>().Hypothesized
                        && clicked_object.GetComponent<EdgeController>().Hypothesized)
                    {
                        Hypothesis hyp_1 = last_clicked_object.GetComponent<EdgeController>().Hypothesis;
                        Hypothesis hyp_2 = clicked_object.GetComponent<EdgeController>().Hypothesis;
                        // Don't compare a hypothesis with itself.
                        if (hyp_1 != hyp_2)
                        {
                            string info_text = "";
                            // The paired score from the active solution set for these two hypotheses.
                            float? paired_score = App.Instance.active_solution_set.GetPairedScore(hyp_1, hyp_2);
                            if (paired_score is not null)
                                info_text += "Paired Score: " + paired_score.ToString();
                            // What Contradictions both hypotheses share.
                            List<Contradiction> shared_contradictions = hyp_1.GetSharedContradictions(hyp_2);
                            
                            info_text += "\nShared Contradictions:";
                            foreach (var contradiction in shared_contradictions)
                            {
                                info_text += "\n" + contradiction.ToString();
                            }
                            this.SetInfoText(info_text);
                        }// end if
                    }
                }
                this.last_clicked_object = clicked_object;
            }
            else
            {
                this.last_clicked_object = null;
            }
        }

        // Handle keyboard inputs.
        // esc toggles the SetupMenu.
        if (Input.GetKeyDown(KeyCode.Escape))
        {
            if (this.setup_menu.activeSelf)
            {
                this.setup_menu.SetActive(false);
            }
            else
            {
                this.setup_menu.SetActive(true);
            }
        }
        // 'i' toggles the info canvas.
        else if (Input.GetKeyDown(KeyCode.I))
        {
            if (this.info_canvas.activeSelf)
            {
                this.info_canvas.SetActive(false);
            }
            else
            {
                this.info_canvas.SetActive(true);
            }
        }
        // Pressing 'c' cycles the active solution set.
        else if (Input.GetKeyDown(KeyCode.C))
        {
            // Enable all hypothesis edges.
            foreach (EdgeController controller in App.Instance.edge_controllers.Values)
            {
                if (controller.Hypothesized)
                {
                    if (controller.Hypothesis is CausalSequenceHyp)
                    {
                        controller.direction_arrow.SetActive(true);
                        controller.gameObject.SetActive(true);
                    }
                }
            }
            this.canon_only = false;
            this.neighbor_only = false;
            App.Instance.CycleActiveSolutionSet();
        }
        // Pressing 'g' toggles all causal hypothesis edges except for the "golden"
        // canon causal hypothesis set.
        else if (Input.GetKeyDown(KeyCode.G))
        {
            if (this.canon_only == false)
            {
                // Toggle off all non-canon causal hypothesis edges.
                foreach (EdgeController controller in App.Instance.edge_controllers.Values)
                {
                    if (controller.Hypothesized)
                    {
                        if (controller.Hypothesis is CausalSequenceHyp)
                        {
                            if (!controller.is_canon_hyp)
                            {
                                // Disable the direction arrow as well.
                                controller.direction_arrow.SetActive(false);
                                controller.gameObject.SetActive(false);
                            }
                        }
                    }
                }
                this.canon_only = true;
            }
            else
            {
                // Toggle on all non-canon causal hypothesis edges.
                foreach (EdgeController controller in App.Instance.edge_controllers.Values)
                {
                    if (controller.Hypothesized)
                    {
                        if (controller.Hypothesis is CausalSequenceHyp)
                        {
                            if (!controller.is_canon_hyp)
                            {
                                // Enable the direction arrow as well.
                                controller.direction_arrow.SetActive(true);
                                controller.gameObject.SetActive(true);
                            }
                        }
                    }
                }
                this.canon_only = false;
            }
        }
        // Pressing 'n' toggles only showing neighboring CausalSequenceHyps. 
        else if (Input.GetKeyDown(KeyCode.N))
        {
            if (this.neighbor_only == false)
            {
                // Toggle off all non-neighboring causal hypothesis edges.
                foreach (EdgeController controller in App.Instance.edge_controllers.Values)
                {
                    if (controller.Hypothesized)
                    {
                        if (controller.Hypothesis is CausalSequenceHyp)
                        {
                            if (Mathf.Abs(controller.EndImageIndex - controller.StartImageIndex) > 1)
                            {
                                // Disable the direction arrow as well.
                                controller.direction_arrow.SetActive(false);
                                controller.gameObject.SetActive(false);
                            }
                        }
                    }
                }
                this.neighbor_only = true;
            }
            else
            {
                // Toggle on all non-neighboring causal hypothesis edges.
                foreach (EdgeController controller in App.Instance.edge_controllers.Values)
                {
                    if (controller.Hypothesized)
                    {
                        if (controller.Hypothesis is CausalSequenceHyp)
                        {
                            if (Mathf.Abs(controller.EndImageIndex - controller.StartImageIndex) > 1)
                            {
                                // Enable the direction arrow as well.
                                controller.direction_arrow.SetActive(true);
                                controller.gameObject.SetActive(true);
                            }
                        }
                    }
                }
                this.neighbor_only = false;
            }
        }

        // Pressing 'del' deinitialzied the current scene.
        else if (Input.GetKeyDown(KeyCode.Delete))
        {
            if (App.Instance.initialized)
            {
                App.Instance.Deinitialize();
            }
        }
    }

    // Release references to any game objects that have to be
    // deleted on deinitialization.
    public void Deinitialize()
    {
        this.last_moused_over_object = null;
        this.last_clicked_object = null;
    }

    private void OnEnable()
    {
        // Subscribe to events from edge controllers.
        EdgeController.OnMouseEnterAction += OnEdgeMouseEnter;
        //EdgeController.OnPointerExited
    }

    private void OnDisable()
    {
        // Unsubcribe from all events.
        EdgeController.OnMouseEnterAction -= OnEdgeMouseEnter;
    }

    // Set the text shown in the info box.
    public void SetInfoText(string text)
    {
        this.info_text = text;
    }

    // Add text to the info box's text.
    public void AddInfoText(string text)
    {
        this.info_text += "/n" + text;
    }

    void OnGUI()
    {
        /*
        this.info_box_style = GUI.skin.box;
        this.info_box_style.alignment = TextAnchor.UpperCenter;
        this.info_box_style.wordWrap = true;
        // Make a general info box on the bottom of the screen. 
        GUI.Box(new Rect(10, Screen.height - 250, Screen.width - 10, 250), this.info_text, style: this.info_box_style);*
        */
    }

    // Listeners for UI elements.
    void HypothesizedToggleChanged(Toggle toggle)
    {
        this.SetInfoText("Hypothesized toggle is currently " + toggle.isOn.ToString());
        // If the toggle is set to On, tell the main controller to enable all hypothesized elements.
        // Otherwise, tell the main controller to disable all hypothesized elements.
        if (toggle.isOn)
        {
            App.Instance.EnableHypothesized();
        }
        else if (!toggle.isOn)
        {
            App.Instance.DisableHypothesized();
        }
    }

    // Determines whether a game object is an Edge.
    // Returns true if it is, false otherwise.
    public bool IsEdge(GameObject game_object)
    {
        if (game_object.GetComponent<EdgeController>() != null)
            return true;
        else
            return false;
    }

    // Updates some components according to the current active solution set.
    public void UpdateSolutionSet()
    {
        this.UpdateInfoCanvasText();
    }

    // Sets the text for the Text_TMP element of the info canvas.
    private void SetInfoCanvasText(string text)
    {
        this.info_canvas.transform.Find("InfoScrollView").Find("Viewport").Find("Content").GetComponent<TMP_Text>().text = text;
    }

    // Update the info canvas text.
    private void UpdateInfoCanvasText()
    {
        if (this.last_moused_over_info_object is null)
            return;
        // Start with the name of the current active parameter set.
        SolutionSet active_solution_set = App.Instance.active_solution_set;
        Solution active_solution = App.Instance.active_solution;
        ParameterSet active_parameter_set = active_solution.parameter_set;
        string info_text = $"Active Parameter Set: {active_parameter_set.name}\n";
        // The if the last moused over info game object is an edge.
        if (this.last_moused_over_info_object.GetComponent<EdgeController>() is not null)
        {
            EdgeController edge_controller = this.last_moused_over_info_object.GetComponent<EdgeController>();
            Edge edge = edge_controller.edge;
            info_text += $" Edge {edge.id}";
            info_text += $"\n {edge}";

            // If the edge came from a hypothesis, its hypothesis field will be non-null.
            if (edge.hypothesis != null)
            {
                // The hypothesis ID and type.
                info_text += $"\n\n Hypothesis {edge.hypothesis.id}";
                info_text += $"\n {edge.hypothesis.GetType()}";
                // Its score.
                info_text += $"\n Score: {edge.EdgeController.GetHypothesisInfoScoreText()}";

                // Whether the hypothesis was accepted or rejected.
                bool accepted = active_solution.accepted_hypotheses.ContainsKey(edge.hypothesis.id);
                info_text += $"\n Accepted: {accepted}";
                if (!accepted)
                {
                    // If the hypothesis was rejected, find all its rejections and list them.
                    info_text += $"\n Rejections:";
                    foreach (Rejection rejection in active_solution.GetRejections(edge.hypothesis))
                    {
                        info_text += $"\n     {rejection.explanation}";
                        // Hypothesis contradiction rejection.
                        if (rejection is HypConRejection)
                        {

                        }
                    }
                }

                // List its evidence.
                info_text += $"\n Evidence: ";
                foreach (Evidence ev in edge.hypothesis.AllEvidence)
                {
                    info_text += $"\n    Type: {ev.GetType()}, score: {ev.GetWeightedScore(active_solution_set, active_solution)}";
                    // Evidence subtype specific information
                    // For causal path evidence, get the edge leading from the first step.
                    if (ev is CausalPathEv)
                    {
                        CausalPathEv cp_ev = (CausalPathEv)ev;
                        info_text += $"\n        {cp_ev.concept_path.steps[0].next_edge}";
                    }
                    else if (ev is MultiCausalPathEv)
                    {
                        MultiCausalPathEv cp_ev = (MultiCausalPathEv)ev;
                        info_text += $"\n        {cp_ev}";
                    }
                    // For continuity evidence, show the joining SameObjectHyp.
                    else if (ev is ContinuityEv)
                    {
                        ContinuityEv c_ev = (ContinuityEv)ev;
                        info_text += ($"\n        {c_ev.joining_hyp.edge} " +
                            $"(accepted: {c_ev.joining_hyp.Accepted(active_solution_set, active_solution)})");
                    }
                }

                // List its contradictions.
                // The contradiction, the hypothesis this hypothesis contradicts with,
                // and whether the other hypothesis was accepted or not.
                info_text += $"\n Contradictions: ";
                foreach (Contradiction contradiction in active_solution_set.GetContradictions(edge.hypothesis))
                {
                    // Check what type of contradiction it is so we can print its information.
                    if (contradiction is InImageTransCon)
                    {
                        var con = (InImageTransCon)contradiction;
                        Hypothesis other_hyp = con.GetOtherHypothesis(edge.hypothesis);
                        bool other_hyp_accepted = active_solution.accepted_hypotheses.ContainsKey(other_hyp.id);
                        info_text += $"\n     InImageTransCon with hyp {other_hyp} ({other_hyp_accepted}). ";
                        info_text += $"\n         obj_1: {con.obj_1.name}, obj_2: {con.obj_2.name}, shared_obj: {con.shared_obj.name}.";
                    }
                    else if (contradiction is TweenImageTransCon)
                    {
                        var con = (TweenImageTransCon)contradiction;
                        Hypothesis other_hyp = con.GetOtherHypothesis(edge.hypothesis);
                        bool other_hyp_accepted = active_solution.accepted_hypotheses.ContainsKey(other_hyp.id);
                        bool joining_hyp_accepted = active_solution.accepted_hypotheses.ContainsKey(con.joining_hyp.id);
                        bool hyp_set_accepted = active_solution.accepted_hypothesis_sets.ContainsKey(con.hyp_set_id);
                        info_text += $"\n     InImageTransCon with hyp {other_hyp.id} (accepted: {other_hyp_accepted}). ";
                        info_text += $"\n         obj_1: {con.obj_1.name}, obj_2: {con.obj_2.name}, shared_obj: {con.shared_obj.name}.";
                        info_text += $"\n         joining_hyp: {con.joining_hyp.id} (accepted: {joining_hyp_accepted}), hyp set: {con.hyp_set_id} (accepted: {hyp_set_accepted}).";
                    }
                    else if (contradiction is CausalChainFlowCon)
                    {
                        var con = (CausalChainFlowCon)contradiction;
                        bool hyp_set_1_accepted = active_solution.accepted_hypothesis_sets.ContainsKey(con.hyp_set_1.id);
                        bool hyp_set_2_accepted = active_solution.accepted_hypothesis_sets.ContainsKey(con.hyp_set_2.id);
                        info_text += $"\n     CausalChainFlowCon with hyp_set {con.hyp_set_1} (accepted: {hyp_set_1_accepted}) ";
                        info_text += $"and hyp_set {con.hyp_set_2} (accepted: {hyp_set_2_accepted}) ";
                    }
                }// end foreach
            }

            this.SetInfoCanvasText(info_text);
        }// end if
    }

    // Functions subscribed to actions.
    // Subscribed to EdgeController.OnMouseEnterAction, which is called by EdgeController.MouseEnter
    public void OnEdgeMouseEnter(GameObject game_object)
    {
        // Update the last moused over info object.
        this.last_moused_over_info_object = game_object;
        /// Update the info canvas text.
        this.UpdateInfoCanvasText();

    }
}//end class GUIController