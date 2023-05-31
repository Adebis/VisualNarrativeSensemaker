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
    public GameObject edge_prefab;
    public RawImage scene_image_prefab;

    // Game objects
    public Canvas scene_canvas;
    public Camera main_camera;
    private CameraController main_camera_controller;
    

    // Data read from the sensemaker's output json.
    private SensemakerData sensemaker_data;
    // A dictionary of scene images, keyed by the id of the image they display.
    private Dictionary<int, SceneImageController> scene_image_controllers;
    // A dictionary of node controllers, keyed by the id of the node they
    // represent.
    private Dictionary<int, NodeController> node_controllers;
    private Dictionary<int, EdgeController> edge_controllers;


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
        this.sensemaker_data = JsonConvert.DeserializeObject<SensemakerData>(
            json_text, new SensemakerDataConverter());

        this.InitializeImages();
        this.InitializeKnowledgeGraph();
    }

    private void InitializeImages()
    {
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
    }

    private void InitializeKnowledgeGraph()
    {
        // Instantiate the knowledge graph's nodes.
        this.node_controllers = new Dictionary<int, NodeController>();
        foreach (Node node in this.sensemaker_data.knowledge_graph.nodes.Values)
        {
            if (node is ObjectNode && !node.hypothesized)
            {
                this.InitializeSceneGraphObjectNode((ObjectNode)node);
            }
            else if (node is ActionNode && !node.hypothesized)
            {
                this.InitializeSceneGraphActionNode((ActionNode)node);
            }
        }
        // Now that all the nodes have been made, draw edges between them.
        this.edge_controllers = new Dictionary<int, EdgeController>();
        // Make edges only between non-hypothesized non-concept nodes for now.
        foreach (Node node in this.sensemaker_data.knowledge_graph.nodes.Values)
        {
            if (node.hypothesized || node is ConceptNode)
            {
                continue;
            }
            foreach (Edge edge in node.edges.Values)
            {
                // Don't parse this edge if either of its nodes are hypothesized
                // or are concepts.
                if (edge.source.hypothesized || edge.target.hypothesized ||
                    edge.source is ConceptNode || edge.target is ConceptNode)
                {
                    continue;
                }
                this.InitializeEdge(edge);
            }
        }
    }

    private void InitializeSceneGraphObjectNode(ObjectNode object_node)
    {
        // Calculate the midpoint of the node's bounding box.
        var scene_image = this.scene_image_controllers[object_node.image_ids[0]];
        var bounding_box = object_node.scene_graph_objects[0].bounding_box;
        float x = scene_image.x + bounding_box.x;
        float y = scene_image.y + scene_image.Height - bounding_box.y;
        float mid_x = x + bounding_box.w / 2;
        float mid_y = y - bounding_box.h / 2;
        Vector3 midpoint = new Vector3(mid_x, mid_y, 0);

        this.InitializeNode(object_node, midpoint);
    }
    private void InitializeSceneGraphActionNode(ActionNode action_node)
    {
        Vector3 midpoint = new Vector3();
        var subject_controller = this.node_controllers[action_node.subject.id];
        var subject_position = subject_controller.transform.position;
        // Not all Actions have objects.
        // If the Action has a subject and an object, calculate the midpoint
        // between the two and place the Action's node there.
        if (action_node.object_ is not null)
        {
            var object_position = this.node_controllers[action_node.object_.id].transform.position;
            float max_x = Mathf.Max(subject_position.x, object_position.x);
            float min_x = Mathf.Min(subject_position.x, object_position.x);
            float max_y = Mathf.Max(subject_position.y, object_position.y);
            float min_y = Mathf.Min(subject_position.y, object_position.y);
            midpoint = new Vector3(min_x + (max_x - min_x) / 2, 
                min_y + (max_y - min_y) / 2, 0);
        }
        else
        {
            // If the Action only has a subject, put its node a random distance 
            // away in a random direction from its subject's node.
            float diameter = 2 * subject_controller.Size.x;
            float x_distance = Random.Range(1 * diameter, 3 * diameter);
            float y_distance = Random.Range(1 * diameter, 3 * diameter);
            // Randomly negate the distances.
            if (Random.Range(1, 2) == 1)
            {
                x_distance *= -1;
            }
            if (Random.Range(1, 2) == 1)
            {
                y_distance *= -1;
            }
            midpoint = new Vector3(subject_position.x + x_distance,
                subject_position.y + y_distance, 0);
        }
        
        this.InitializeNode(action_node, midpoint);
    }

    // Initialize a node at the position passed in.
    private void InitializeNode(Node node, Vector3 position)
    {
        var node_object = Instantiate(this.node_prefab, position, 
            Quaternion.identity);
        var node_controller = node_object.GetComponent<NodeController>();
        node_controller.Initialize(node, this.scene_image_controllers);
        this.node_controllers[node.id] = node_controller;
    }

    // Initialize an edge.
    private void InitializeEdge(Edge edge)
    {
        // Make sure the edge's nodes have node controllers.
        if (!this.node_controllers.ContainsKey(edge.source.id))
        {
            print("Node " + edge.source.name + " has no node game object.");
            return;
        }
        if (!this.node_controllers.ContainsKey(edge.target.id))
        {
            print("Node " + edge.target.name + " has no node game object.");
            return;
        }
        // Get the node controllers for the source and target nodes of this edge.
        var source_controller = this.node_controllers[edge.source.id];
        var target_controller = this.node_controllers[edge.target.id];
        // Make the edge's game object.
        var edge_object = Instantiate(this.edge_prefab, Vector3.zero, 
            Quaternion.identity);
        // Get and initialize the edge controller.
        var edge_controller = edge_object.GetComponent<EdgeController>();
        edge_controller.Initialize(edge, source_controller, target_controller);
        this.edge_controllers[edge.id] = edge_controller;
    }

    // Update is called once per frame
    void Update()
    {
        
    }
}