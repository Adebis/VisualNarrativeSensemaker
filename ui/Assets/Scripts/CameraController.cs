using System.Collections;
using System.Collections.Generic;
using System.Diagnostics.Tracing;
using UnityEngine;

public class CameraController : MonoBehaviour
{
    // Set in editor
    public float key_pan_speed;
    public float mouse_pan_speed;
    public float zoom_speed;
    // Higher smoothness makes the camera take a shorter amount of time to
    // get to its next position. 
    public float smoothness;
    // Prevent the camera from zooming in further than this.
    public float minimum_size;
    // All speeds are scaled to the current camera size.
    // Use this value to set a baseline camera size. 
    private float base_size = 500;

    // Variables to help with movement.
    // The next position the camera will move towards.
    public Vector3 next_position;
    // The next orthographic size the camera will grow or shrink towards.
    public float next_size;
    // Where the mouse was in world-space coordinates when the camera began to zoom.
    public Vector3 mouse_start_position;

    // The camera this camera controller is controlling.
    private new Camera camera;

    // Start is called before the first frame update
    void Start()
    {
        this.next_position = new Vector3(0, 0, -10);
        this.next_size = 1;
        this.camera = this.gameObject.GetComponent<Camera>();
        this.mouse_start_position = this.camera.ScreenToWorldPoint(Input.mousePosition);
    }

    // Update is called once per frame
    void Update()
    {
        // WASD pans the camera.
        if (Input.GetKey(KeyCode.W))
        {
            this.next_position += new Vector3(0, this.KeyPanSpeed, 0);
        }
        if (Input.GetKey(KeyCode.A))
        {
            this.next_position += new Vector3(-this.KeyPanSpeed, 0, 0);
        }
        if (Input.GetKey(KeyCode.S))
        {
            this.next_position += new Vector3(0, -this.KeyPanSpeed, 0);
        }
        if (Input.GetKey(KeyCode.D))
        {
            this.next_position += new Vector3(this.KeyPanSpeed, 0, 0);
        }
        // Right click and drag pans the camera.
        if (Input.GetMouseButton(1))
        {
            float x_delta = Input.GetAxis("Mouse X");
            float y_delta = Input.GetAxis("Mouse Y");
            this.next_position += new Vector3(-x_delta, -y_delta, 0) * this.MousePanSpeed;
        }

        // Mouse wheel zooms the camera.
        if (Input.mouseScrollDelta.y != 0)
        {
            this.next_size += -Input.mouseScrollDelta.y * this.ZoomSpeed;
            // Also moves the camera such that the mouse stays in the same world position. 
            // If we're going to adjust the screen after this so that the mouse is in the same world space
            // coordinates as before the zoom, we need to log where the mouse started in world coords.
            this.mouse_start_position = this.camera.ScreenToWorldPoint(Input.mousePosition);
        }

        // Clamp the size.
        if (this.next_size < this.minimum_size)
        {
            this.next_size = this.minimum_size;
        }

        // Change the camera's size towards its new size.
        if (this.next_size != this.camera.orthographicSize)
        {
            /*this.camera.orthographicSize = (this.camera.orthographicSize +
                (this.next_size - this.camera.orthographicSize) * (Time.deltaTime * this.smoothness));
            // If it's close enough to its target size, snap to its target size.
            if (Mathf.Abs(this.next_size - this.camera.orthographicSize) < 1)
            {
                this.camera.orthographicSize = this.next_size;
            }*/
            // Snap camera to new zoom size. 
            this.camera.orthographicSize = this.next_size;

            // Get the vector of the mouse's movement in world-space.
            Vector3 mouse_diff = this.mouse_start_position - this.camera.ScreenToWorldPoint(Input.mousePosition);
            mouse_diff.z = 0;
            // Apply that same movement to the camera so the mouse is back where it was in world-space.
            this.gameObject.transform.position += mouse_diff;
            this.next_position = this.gameObject.transform.position;
        }

        // Move the camera towards its new position.
        if (this.next_position != this.gameObject.transform.position)
        {
            this.gameObject.transform.position = Vector3.Lerp(
                this.gameObject.transform.position,
                this.next_position,
                Time.deltaTime * this.smoothness);
            // If it's close enough to its target position, snap to its target
            // position.
            if ((this.next_position - this.gameObject.transform.position).magnitude < 1)
            {
                this.gameObject.transform.position = this.next_position;
            }
        }//end if
    }

    public void SetNextPosition(Vector3 next_position)
    {
        this.next_position = next_position;
    }
    public void SetNextSize(float next_size)
    {
        this.next_size = next_size;
    }

    // Scale all speeds to the size of the camera.
    public float KeyPanSpeed
    {
        get
        {
            return this.key_pan_speed * (this.camera.orthographicSize / this.base_size);
        }
    }
    public float MousePanSpeed
    {
        get
        {
            return this.mouse_pan_speed * (this.camera.orthographicSize / this.base_size);
        }
    }
    public float ZoomSpeed
    {
        get
        {
            return this.zoom_speed;
        }
    }
}
