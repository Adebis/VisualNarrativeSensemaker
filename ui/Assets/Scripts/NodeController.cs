using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using TMPro;

public class NodeController : MonoBehaviour
{
    // Prefabs
    public GameObject bbox_prefab;

    // The Node this node game object represents.
    public Node node;

    // The node's outline game object.
    private GameObject outline;
    // The node's fill game object.
    private GameObject fill;
    // The node's text game object.
    private GameObject text;
    // The node's bounding box object, if it has one.
    private GameObject bounding_box;

    // The controllers for the scene's images, keyed by the id of the image they 
    // display.
    private Dictionary<int, SceneImageController> scene_image_controllers;

    // The node's original scale when it was instantiated.
    private Vector3 original_scale;
    private Vector3 target_scale;
    // How long it should take to change the scale of the node, in seconds.
    private float scale_change_time = 0.15f;
    // A reference velocity for use in smoothly changing the node's scale.
    private Vector3 scale_change_velocity = Vector3.zero;
    // The factor by which the node's scale should change when it's moused over.
    private float mouseover_scale_factor = 1.25f;

    // Monobehaviors don't have constructors, so call this initialization
    // function after the Node game object is created instead.
    public void Initialize(Node node, 
        Dictionary<int, SceneImageController> scene_image_controllers)
    {
        // Call start in case it hasn't been called before Initialization.
        this.Start();
        this.bounding_box = null;
        this.scene_image_controllers = scene_image_controllers;
        this.node = node;
        // Set the fill and outline colors according to the type of node.
        if (this.node is ObjectNode)
        {
            this.SetFillColor(Color.white);
            this.SetOutlineColor(Color.black);
        }
        else if (this.node is ActionNode)
        {
            this.SetFillColor(Color.white);
            this.SetOutlineColor(Color.blue);
        }
        // Set the text that this node displays.
        this.SetText(node.name);
        // Hide the text initially.
        this.text.SetActive(false);
        
        // If this is an object node, make a bounding box for it.
        if (this.node is ObjectNode)
        {
            var object_node = (ObjectNode)this.node;
            // Make the bounding box a child of the image it's for.
            var scene_image = this.scene_image_controllers[object_node.image_ids[0]];
            this.bounding_box = Instantiate(bbox_prefab, Vector3.zero, 
                Quaternion.identity, scene_image.gameObject.transform);
            // Set its four points according to its bounding box info.
            var bbox = object_node.BoundingBox;
            // Top-left, top-right, bottom-right, bottom-left, top-left
            Vector3[] points = new Vector3[5];
            // The bounding box info's x and y values are for the top-left 
            // point of the node, but unity measures from the bottom-right.
            float x = scene_image.x + bbox.x;
            float y = scene_image.y + scene_image.Height - bbox.y;
            //float y = image_data.
            float z = -5;
            points[0] = new Vector3(x, y, z);
            points[1] = new Vector3(x + bbox.w, y, z);
            points[2] = new Vector3(x + bbox.w, y - bbox.h, z);
            points[3] = new Vector3(x, y - bbox.h, z);
            points[4] = new Vector3(x, y, z);
            this.bounding_box.GetComponent<LineRenderer>().positionCount = 5;
            this.bounding_box.GetComponent<LineRenderer>().SetPositions(points);
            // Hide it initially.
            this.bounding_box.SetActive(false);
        }
    }

    // Start is called before the first frame update
    void Start()
    {
        this.original_scale = this.transform.localScale;
        this.target_scale = this.transform.localScale;
        this.outline = gameObject.transform.Find("outline").gameObject;
        this.fill = gameObject.transform.Find("fill").gameObject;
        this.text = gameObject.transform.Find("text").gameObject;
    }

    // Update is called once per frame
    void Update()
    {

    }

    void FixedUpdate()
    {
        // Smoothly change scale to the target scale. 
        if (this.target_scale != this.transform.localScale)
        {
            this.transform.localScale = Vector3.SmoothDamp(current: this.transform.localScale, 
                target: this.target_scale, 
                currentVelocity: ref this.scale_change_velocity,
                smoothTime: this.scale_change_time);
        }
    }

    void OnMouseEnter()
    {
        // On mouse-over, grow the node.
        print("MouseEnter node " + this.node.name);
        if (this.node is ActionNode)
        {
            print("Subject: " + ((ActionNode)this.node).subject.name);
            if (((ActionNode)this.node).object_ is not null)
                print("Object: " + ((ActionNode)this.node).object_.name);
        }
        this.target_scale = this.original_scale * this.mouseover_scale_factor;
        // Reveal the node's text.
        this.text.SetActive(true);
        // If this node has a none-null bounding box, reveal it.
        if (this.bounding_box is not null)
        {
            this.bounding_box.SetActive(true);
        }
    }

    void OnMouseExit()
    {
        // If the node isn't being moused over anymore, shrink the node.
        this.target_scale = this.original_scale;
        // Hide the node's text.
        this.text.SetActive(false);
        // If this node has a none-null bounding box, hide it.
        if (this.bounding_box is not null)
        {
            this.bounding_box.SetActive(false);
        }
    }

    private void SetFillColor(Color fill_color)
    {
        this.fill.GetComponent<SpriteRenderer>().color = fill_color;
    }

    private void SetOutlineColor(Color outline_color)
    {
        this.outline.GetComponent<SpriteRenderer>().color = outline_color;
    }

    private void SetText(string text)
    {
        this.text.GetComponent<TMP_Text>().text = text;
    }

    // The node's game object's size.
    public Vector3 Size
    {
        get { return this.gameObject.transform.localScale; }
    }
}