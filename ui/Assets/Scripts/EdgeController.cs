using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class EdgeController : MonoBehaviour
{
    private Edge edge;
    private NodeController source_controller;
    private NodeController target_controller;

    private LineRenderer line_renderer;
    private EdgeCollider2D edge_collider;

    // Initialize this edge controller with the edge it represents, as well as
    // the NodeControllers of its start and end nodes.
    public void Initialize(Edge edge, NodeController source_controller, 
        NodeController target_controller)
    {
        this.edge = edge;
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
        print("mousing over edge " + this.edge.source.name + "|" + this.edge.target.name);
    }
}
