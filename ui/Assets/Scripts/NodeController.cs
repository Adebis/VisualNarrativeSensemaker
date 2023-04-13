using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class NodeController : MonoBehaviour
{
    // The Node this node game object represents.
    public Node node;

    private Vector3 target_scale;
    // How long it should take to change the scale of the node, in seconds.
    private float scale_change_time = 0.25f;
    // A reference velocity for use in smoothly changing the node's scale.
    private Vector3 scale_change_velocity = Vector3.zero;
    // The factor by which the node's scale should change when it's moused over.
    private float mouseover_scale_factor = 1.25f;

    // Monobehaviors don't have constructors, so call this initialization
    // function after the Node game object is created instead.
    public void Initialize(Node node)
    {
        this.node = node;
    }

    // Start is called before the first frame update
    void Start()
    {
        this.target_scale = this.transform.localScale;
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
        //print("MouseEnter node " + this.node.name);
        this.target_scale = this.transform.localScale * this.mouseover_scale_factor;
    }

    void OnMouseExit()
    {
        this.target_scale = this.transform.localScale / this.mouseover_scale_factor;
    }
}
