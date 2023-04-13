using System.IO;
using Newtonsoft.Json;

using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.UI;

public class Main : MonoBehaviour
{
    // Prefabs
    public GameObject node_prefab;
    public RawImage scene_image_prefab;

    // Game objects
    public Canvas scene_canvas;
    public Camera main_camera;
    private CameraController main_camera_controller;
    

    // A dictionary of scene images, keyed by the id of the image they display.
    private Dictionary<int, SceneImageController> scene_image_controllers;
    // A dictionary of node controllers, keyed by the id of the node they
    // represent.
    private Dictionary<int, NodeController> node_controllers;

    // The name of the output json file that should be loaded.
    public string output_file_name;

    // Start is called before the first frame update
    void Start()
    {
        // Find the output directory, which should be under ../../data/outputs/
        string top_directory = Path.GetDirectoryName(Path.GetDirectoryName(Application.dataPath));
        // Go two directories up from Assets to get to VisualNarrativeSensemaker/
        string output_file_directory = Path.Join(top_directory, "\\data\\outputs\\");
        string output_file_path = output_file_directory + output_file_name;
        print("Loading output file at " + output_file_path);
        string json_text = File.ReadAllText(output_file_path);
        SensemakerData sensemaker_data = JsonConvert.DeserializeObject<SensemakerData>(
            json_text, new SensemakerDataConverter());

        // Load and draw the images. 
        this.scene_image_controllers = new Dictionary<int, SceneImageController>();
        //var new_scene_image = Instantiate(this.scene_image_prefab);
        float x_offset = 0;
        foreach (ImageData image_data in sensemaker_data.knowledge_graph.images.Values)
        {
            // Make a new scene image ui element.
            var new_scene_image = Instantiate(this.scene_image_prefab, this.scene_canvas.transform);
            var new_scene_image_controller =  new_scene_image.GetComponent<SceneImageController>();
            // Initialize its controller.
            new_scene_image_controller.Initialize(image_data, x_offset);
            this.scene_image_controllers[image_data.id] = new_scene_image_controller;
            // Make sure the next image is additionally offset by this image's 
            // full width.
            x_offset += new_scene_image.GetComponent<RectTransform>().sizeDelta.x;
        }

        // Set the camera to a point midway between the images.
        this.main_camera_controller = this.main_camera.GetComponent<CameraController>();
        float rightmost_x = 0;
        float topmost_y = 0;
        foreach (var scene_image_controller in this.scene_image_controllers.Values)
        {
            if (scene_image_controller.x + scene_image_controller.Width > rightmost_x)
            {
                rightmost_x = scene_image_controller.x + scene_image_controller.Width;
            }
            if (scene_image_controller.y + scene_image_controller.Height > topmost_y)
            {
                topmost_y = scene_image_controller.y + scene_image_controller.Height;
            }
        }
        Vector3 midway_point = new Vector3(rightmost_x / 2, 
            topmost_y / 2, 
            main_camera.transform.position.z);
        this.main_camera_controller.SetNextPosition(midway_point);
        // Set the camera's size such that it encompasses all of the images.
        float camera_size = (rightmost_x + 50) * Screen.height / Screen.width * 0.5f;
        this.main_camera_controller.SetNextSize(camera_size);

        this.node_controllers = new Dictionary<int, NodeController>();
        // Make a node.
        var new_node_game_object = Instantiate(this.node_prefab, 
            new Vector3(0, 0, 0), Quaternion.identity);
        var new_node_controller = new_node_game_object.GetComponent<NodeController>();
        new_node_controller.Initialize(sensemaker_data.knowledge_graph.nodes[0]);
        this.node_controllers[new_node_controller.node.id] = new_node_controller;
    }

    // Update is called once per frame
    void Update()
    {
        
    }
}