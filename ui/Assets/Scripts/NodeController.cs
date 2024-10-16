using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using TMPro;
using System.Linq;

public class NodeController : MonoBehaviour
{
    // Prefabs
    public GameObject bbox_prefab;
    public GameObject scene_text_prefab;

    // The GUI controller
    private GUIController gui_controller;

    // The Node this node game object represents.
    public Node node;
    // If this node was made by a hypothesis, this is the hypothesis.
    private Hypothesis hypothesis;

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
    // The factor by which the node's scale should change while it's moused over.
    private float mouseover_scale_factor = 1.3f;
    // The factor by which the node's scale should change when it's focused.
    private float focus_scale_factor = 1.2f;
    // The factor by which the node's scale should change when it's clicked down on.
    private float clicked_scale_factor = 1.3f;

    // Whether this node is focused.
    public bool focused;
    // Whether this node is locked as focused.
    public bool focus_locked;

    // Monobehaviors don't have constructors, so call this initialization
    // function after the Node game object is created instead.
    public void Initialize(Node node, 
        Dictionary<int, SceneImageController> scene_image_controllers,
        GUIController gui_controller,
        Hypothesis hypothesis = null)
    {   
        this.gui_controller = gui_controller;
        this.hypothesis = hypothesis;

        this.focused = false;
        this.focus_locked = false;
        this.original_scale = this.transform.localScale;
        this.target_scale = this.transform.localScale;
        this.outline = gameObject.transform.Find("outline").gameObject;
        this.fill = gameObject.transform.Find("fill").gameObject;
        this.text = Instantiate(scene_text_prefab,
            new Vector3(this.transform.position.x, this.transform.position.y - 15, 0),
            Quaternion.identity);

        this.bounding_box = null;
        this.scene_image_controllers = scene_image_controllers;
        this.node = node;
        // Set the fill and outline colors according to the type of node
        // and whether it was hypothesized or not.
        Color instance_fill_color = new Color(0.9f, 0.9f, 0.9f, 1);
        Color hypothesized_fill_color = new Color(0, 0.9f, 0, 1);
        if (this.node is ObjectNode)
        {
            if (hypothesis != null)
            {
                this.SetFillColor(hypothesized_fill_color);
                this.SetOutlineColor(Color.black);
            }
            else
            {
                this.SetFillColor(instance_fill_color);
                this.SetOutlineColor(Color.black);
            }
        }
        else if (this.node is ActionNode)
        {
            this.SetFillColor(instance_fill_color);
            this.SetOutlineColor(Color.blue);
        }
        // Set the text that this node displays.
        this.SetText(node.name);
        // Hide the text initially.
        this.text.SetActive(false);
        
        // If this is a non-hypothesized object node, make a bounding box for it.
        if (this.node is ObjectNode && hypothesis is null)
        {
            var object_node = (ObjectNode)this.node;
            // Make the bounding box a child of the image it's for.
            var scene_image = this.scene_image_controllers[object_node.images.Keys.First<int>()];
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

    // Clean up all of this node's related game objects.
    public void Deinitialize()
    {
        // Outline
        GameObject.Destroy(this.outline);
        // Fill
        GameObject.Destroy(this.fill);
        // Text
        GameObject.Destroy(this.text);
        this.text = null;
        // Bounding box.
        GameObject.Destroy(this.bounding_box);
        this.bounding_box = null;
    }

    // Start is called before the first frame update
    void Start()
    {
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

    public void MouseEnter()
    {
        // Focus this node.
        this.Focus();
        // Scale it up to the mouseover scale factor.
        this.target_scale = this.original_scale * this.mouseover_scale_factor;
        // Brighten the node a bit.
        this.ChangeFillColor(0.1f, 0.1f, 0.1f, 0);
    }

    public void MouseExit()
    {
        // Unfocus this node.
        this.Unfocus();
        // If focus locked, the node shoulld still be focused. Scale the node to its focused scale.
        if (this.focus_locked)
        {
            this.target_scale = this.original_scale * this.focus_scale_factor;
        }
        // Redarken the node a bit.
        this.ChangeFillColor(-0.1f, -0.1f, -0.1f, 0);
    }

    private void OnMouseDown()
    {
        // Shrink the node while it's pressed.
        this.target_scale = this.original_scale * this.clicked_scale_factor;
        // Darken the node a bit.
        this.ChangeFillColor(-0.2f, -0.2f, -0.2f, 0);
    }

    void OnMouseUpAsButton()
    {
        // Grow the node back to mouseover size.
        this.target_scale = this.original_scale * this.mouseover_scale_factor;
        this.ToggleFocusLock();
        // Rebrighten the node a bit.
        this.ChangeFillColor(0.2f, 0.2f, 0.2f, 0);
    }

    public void ToggleFocusLock()
    {
        // Lock or unlock the node as focused.
        if (this.focus_locked)
        {
            this.focus_locked = false;
        }
        else
        {
            this.focus_locked = true;
        }
    }

    // Focus this node.
    public void Focus()
    {
        print("Focusing node " + this.node.name);
        if (this.node is ActionNode)
        {
            print("Subject: " + ((ActionNode)this.node).subject.name);
            if (((ActionNode)this.node).object_ is not null)
                print("Object: " + ((ActionNode)this.node).object_.name);
        }
        // Grow the node.
        this.target_scale = this.original_scale * this.focus_scale_factor;
        // Reveal the node's text.
        this.text.SetActive(true);
        // If this node has a none-null bounding box, reveal it.
        if (this.bounding_box is not null)
        {
            this.bounding_box.SetActive(true);
        }
        // Show the node's info in the info box. 
        //this.gui_controller.SetInfoText(this.node.name);

        // Flag that the node is focused.
        this.focused = true;
    }

    // Unfocus this node.
    public void Unfocus()
    {
        // If the node is locked as focused, don't unfocus it.
        if (this.focus_locked) 
        {
            return;
        }
        // Shrink the node.
        this.target_scale = this.original_scale;
        // Hide the node's text.
        this.text.SetActive(false);
        // If this node has a none-null bounding box, hide it.
        if (this.bounding_box is not null)
        {
            this.bounding_box.SetActive(false);
        }

        // Flag that the node is not focused.
        this.focused= false;
    }

    private void SetFillColor(Color fill_color)
    {
        this.fill.GetComponent<SpriteRenderer>().color = fill_color;
    }
    
    private void ChangeFillColor(float r_diff, float g_diff, float b_diff, float a_diff)
    {
        var current_color = this.fill.GetComponent<SpriteRenderer>().color;
        var new_color = new Color(current_color.r + r_diff, 
            current_color.g + g_diff,
            current_color.b + b_diff,
            current_color.a + a_diff);
        this.SetFillColor(new_color);
    }

    private void SetOutlineColor(Color outline_color)
    {
        this.outline.GetComponent<SpriteRenderer>().color = outline_color;
    }

    private void SetText(string text)
    {
        this.text.GetComponent<TextMeshPro>().text = text;
    }

    // Properties
    // Whether or not this node controller's node is made from a hypothesis.
    public bool Hypothesized
    {
        get { return (this.hypothesis != null ? true : false); }
    }
    // The node's game object's size.
    public Vector3 Size
    {
        get { return this.gameObject.transform.localScale; }
    }
}