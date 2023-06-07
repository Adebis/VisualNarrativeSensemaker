using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class EdgeController : MonoBehaviour
{
    private GUIController gui_controller;
    private NodeController source_controller;
    private NodeController target_controller;

    public Edge edge;
    private Hypothesis hypothesis;

    private LineRenderer line_renderer;
    private EdgeCollider2D edge_collider;

    public bool focused;
    public bool focus_locked;

    // Initialize this edge controller with the edge it represents, as well as
    // the NodeControllers of its start and end nodes.
    public void Initialize(Edge edge, NodeController source_controller, 
        NodeController target_controller, GUIController gui_controller,
        Hypothesis hypothesis = null)
    {
        this.focused = false;
        this.focus_locked = false;
        this.gui_controller = gui_controller;
        this.edge = edge;
        this.hypothesis = hypothesis;
        this.source_controller = source_controller;
        this.target_controller = target_controller;
        this.line_renderer = this.gameObject.GetComponent<LineRenderer>();

        // Set two points on the line renderer at the source and target node's
        // locations. 
        this.line_renderer.positionCount = 2;
        Vector3[] positions = new Vector3[2]{
            this.source_controller.gameObject.transform.position,
            this.target_controller.gameObject.transform.position};
        this.line_renderer.SetPositions(positions);
        // Set the same points for the edge collider.
        this.edge_collider = this.gameObject.GetComponent<EdgeCollider2D>();
        List<Vector2> points = new List<Vector2>{
            this.source_controller.gameObject.transform.position,
            this.target_controller.gameObject.transform.position};
        this.edge_collider.SetPoints(points);

        // Set the colors of the line renderer.
        // White
        Color line_color = new Color(0.9f, 0.9f, 0.9f, 1);
        // Hypothesized edge.
        if (hypothesis != null)
        {
            // Green
            line_color = new Color(0, 0.9f, 0, 1);
        }
        this.line_renderer.startColor = line_color;
        this.line_renderer.endColor = line_color;
    }

    // Whether or not this edge controller's edge is made from a hypothesis.
    public bool Hypothesized()
    {
        return (this.hypothesis != null ? true : false);
    }

    // Start is called before the first frame update
    void Start()
    {
        
    }

    // Update is called once per frame
    void Update()
    {
        
    }

    void OnMouseEnter()
    {
        this.Focus();
    }

    private void OnMouseExit()
    {
        this.Unfocus();
    }

    // Focus this edge.
    public void Focus()
    {
        print("Focusing edge " + this.edge.ToString());
        // Reveal the edge's relationship.
        //this.text.SetActive(true);
        // Show the edge's info in the info box. 
        this.gui_controller.SetInfoText(this.edge.ToString());

        // Flag that the edge is focused.
        this.focused = true;
    }

    // Unfocus this edge.
    public void Unfocus()
    {
        // If the edge is locked as focused, don't unfocus it.
        if (this.focus_locked)
        {
            return;
        }

        // Flag that the node is not focused.
        this.focused = false;
    }
}
