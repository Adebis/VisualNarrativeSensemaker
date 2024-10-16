using System.IO;
using Newtonsoft.Json;

using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.UI;
using System.Diagnostics;
using UnityEngine.Rendering;
using System.Threading.Tasks;
using System;
using System.Diagnostics.Tracing;

// Singleton entry point for the application.
public class MainApplication : MonoBehaviour
{
    // The singleton instance property.
    public static MainApplication Instance
    {
        get;
        private set;
    }

    // Prefabs
    public GameObject node_prefab;
    public GameObject edge_prefab;
    public RawImage scene_image_prefab;

    // Game objects
    public Canvas scene_canvas;
    public Camera main_camera;

    // Controllers
    private CameraController main_camera_controller;
    private GUIController gui_controller;

    // Server communicator.
    public NetworkHandler network_handler;

    // Data read from the sensemaker's output json.
    public SensemakerData sensemaker_data;
    // A dictionary of scene images, keyed by the id of the image they display.
    private Dictionary<int, SceneImageController> scene_image_controllers;
    // A dictionary of node controllers, keyed by the id of the node they
    // represent.
    private Dictionary<int, NodeController> node_controllers;
    public Dictionary<int, EdgeController> edge_controllers;

    // A dictionary to count the number of actions each pair of objects 
    // shares.
    // Keyed by a tuple of the ids of the objects, with the smaller id first
    // and the larger id second.
    public Dictionary<Tuple<int, int>, int> shared_action_counts;

    // The name of the output json file that should be loaded.
    public string output_file_name;

    // What text should be displayed in the info box.
    public string info_text;

    // The currently active solution set.
    public SolutionSet active_solution_set;
    // The currently active solution.
    public Solution active_solution;

    // The highest scoring causal sequence hypothesis between each image.
    public CausalSequenceHyp canon_0_1_hyp;
    public CausalSequenceHyp canon_1_2_hyp;
    public CausalSequenceHyp canon_0_2_hyp;

    // The score of the highest scoring causal sequence hypothesis
    // between each image. 
    public float canon_0_1_score;
    public float canon_1_2_score;
    public float canon_0_2_score;

    private float node_z;

    private bool initialization_started;
    public bool initialized;

    // To ensure there is only ever one reference of this singleton,
    // have this object delete itself if there is an Instance and it's not
    // this object.
    // Otherwise, assign the public static Instance to this object.
    private void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(this);
        }
        else
        {
            Instance = this;
        }
    }

    // Start is called before the first frame update
    void Start()
    {
        this.network_handler = this.gameObject.GetComponent<NetworkHandler>();
        this.initialized = false;
        this.initialization_started = false;
    }

    // Run the program with a given image set and parameter set.
    // Returns whether the run successfully started or not.
    // Image set is a list of image IDs.
    // Parameter sets is a list of ParameterSet object.
    // Force generate output is whether or not we want to force the
    // sensemaker to generate an output file
    // even if there's an existing output file for this image set.
    public bool Run(List<int> image_set_ids, 
        List<ParameterSet> parameter_sets, 
        bool force_generate_output)
    {
        // Check if the network handler is connected before trying to initialize.
        if (!this.network_handler.connected)
        {
            print("MainApplication.Run: network handler not yet connected. Stopping run.");
            return false;
        }
        StartCoroutine(this.Initialize(image_set_ids, parameter_sets, force_generate_output));
        return true;
    }

    private IEnumerator Initialize(List<int> image_set_ids, 
        List<ParameterSet> parameter_sets, 
        bool force_generate_output)
    {
        this.initialization_started = true;
        string top_directory = Path.GetDirectoryName(Path.GetDirectoryName(Application.dataPath));

        //List<int> image_set_ids = new List<int>();

        // Read the image_sets.json file.
        //string input_file_directory = Path.Join(top_directory, "\\data\\inputs\\");
        //string input_file_name = "image_sets.json";
        //string input_file_path = Path.Join(input_file_directory, input_file_name);
        //string json_text = File.ReadAllText(input_file_path);
        // Decode the json into import-specific classes.
        //var input_file_data = JsonConvert.DeserializeObject<List<List<int>>>(json_text);
        // 
        //image_set_ids = input_file_data[0];

        // Set 13 - kitchen, bike ride, picnic
        //image_set_ids = new List<int> { 2402873, 2391830, 2406899 };
        // Set 14 - bikes with dogs
        //image_set_ids = new List<int> { 2384081, 2361867, 2329428 };

        this.output_file_name = $"output_{image_set_ids[0]}_{image_set_ids[1]}_{image_set_ids[2]}.json";

        this.node_z = -0.1f;

        this.gui_controller = this.gameObject.GetComponent<GUIController>();
        // Find the output directory, which should be under ../../data/outputs/

        // Go two directories up from Assets to get to VisualNarrativeSensemaker/
        string output_file_directory = Path.Join(top_directory, "\\data\\outputs\\");
        string output_file_path = output_file_directory + output_file_name;

        // See if the file exists.
        bool output_file_exists = File.Exists(output_file_path);

        // If not, or if we're force generating output, first have the sensemaker parse the image set.
        // Debug:
        force_generate_output = false;

        if (!output_file_exists || force_generate_output)
        {
            /*
            Process process = new Process();

            // The python file should be under /src/main.py.
            string main_script_path = Path.Join(top_directory, "\\src\\main.py");
            //main_script_path = Path.Join(top_directory, "\\src\\test.py");
            //string python_3_12_path = "C:\\Users\\zevsm\\AppData\\Local\\Programs\\Python\\Python312\\python.exe";

            process.StartInfo.FileName = "python.exe";
            process.StartInfo.Arguments = $"{main_script_path} {image_set_ids[0]} {image_set_ids[1]} {image_set_ids[2]}";
            process.StartInfo.WorkingDirectory = top_directory;
            process.Start();
            //process = Process.Start(start_info);
            process.WaitForExit();
            //Process.Start("IExplore.exe", "www.northwindtraders.com");
            */
            string message = "execute_function?";
            string message_json = "{\"function_name\": \"run_sensemaker\",\"image_set_ids\": [";
            // Image set IDs
            bool first = true;
            foreach (int image_set_id in image_set_ids)
            {
                if (!first)
                    message_json += ",";
                message_json += image_set_id.ToString();
                if (first)
                    first = false;
            }
            message_json += "],";
            // Parameter sets.
            message_json += "\"parameter_sets\":[";
            foreach (ParameterSet parameter_set in parameter_sets)
            {
                message_json += parameter_set.ToJson();
                message_json += ",";
            }
            // Trim the trailing comma.
            message_json = message_json.TrimEnd(',');

            message_json += "]";

            message_json += "}";
            message += message_json;
            this.network_handler.SendMessage_(message);
            // Wait for a return message indicating that the sensemaker has finished running.
            while (true)
            {
                string return_message = this.network_handler.ReadMessage(true);
                if (return_message is not null)
                {
                    print("Return message: " + return_message);
                    break;
                }//end if
                yield return new WaitForSeconds(0.1f);
            }// end while
        }

        print("Loading output file at " + output_file_path);

        SensemakerDataReader sensemaker_data_reader = new SensemakerDataReader();
        this.sensemaker_data = sensemaker_data_reader.ReadSensemakerData(output_file_path);
        if (this.sensemaker_data is null)
        {
            Console.WriteLine("No valid sensemaker data. Aborting initialization.");
            yield break;
        }

        // Get the first parameter set.
        var first_pset = sensemaker_data.parameter_sets.ToList()[0].Value;
        // Get the solution set for this parameter set.
        var solution_set = sensemaker_data.solution_sets[first_pset.id];
        // Get the first solution.
        var solution = solution_set.solutions[0];
        // Set this solution set and solution as the active ones.
        this.active_solution_set = solution_set;
        this.active_solution = solution;

        this.DetermineCanonCausalSequence();

        this.InitializeImages();
        this.InitializeKnowledgeGraph();

        int new_edge_id_counter = -1;
        // Make edges for all same object hypotheses and causal sequence hypotheses.
        foreach (var hypothesis in sensemaker_data.hypotheses.Values)
        {
            if (hypothesis is SameObjectHyp)
            {
                var same_object_hyp = (SameObjectHyp)hypothesis;
                this.InitializeEdge(same_object_hyp.edge, same_object_hyp);
            }
            else if (hypothesis is CausalSequenceHyp)
            {
                var cs_hyp = (CausalSequenceHyp)hypothesis;
                this.InitializeEdge(cs_hyp.scene_edge, cs_hyp);
                /*
                // If this causal sequence hyp has any multi-step causal hypotheses:
                foreach (MultiCausalPathEv ev in cs_hyp.multi_causal_path_evs)
                {
                    Node source_action_node = cs_hyp.scene_edge.source;
                    Node target_action_node = cs_hyp.scene_edge.target;
                    Node source_concept_node = cs_hyp.edge.source;
                    Node target_concept_node = cs_hyp.edge.target;

                    // Get the middle action.
                    MultiStep middle_step = ev.concept_path.steps[1];

                    // Make a node out of it.
                    Node middle_node = middle_step.nodes[0];
                    // Place it between the source and target nodes.
                    Vector3 source_pos = source_action_node.NodeController.gameObject.transform.position;
                    Vector3 target_pos = target_action_node.NodeController.gameObject.transform.position;
                    Vector3 middle_pos = source_pos + (target_pos - source_pos) / 2;

                    this.InitializeNode(middle_node, middle_pos);

                    // Make an edge from the source node of this hypothesis to the middle node.

                    // Determine if the path starts at the source or the target node of this hypothesis.
                    Node true_source_action = null;
                    Node true_source_concept = null;
                    Node true_target_action = null;
                    Node true_target_concept = null;
                    string direction_arrow = "";
                    if (ev.concept_path.steps[0].nodes.Contains(source_concept_node))
                    {
                        true_source_action = source_action_node;
                        true_source_concept = source_concept_node;
                        true_target_action = target_action_node;
                        true_target_concept = target_concept_node;
                        direction_arrow = "->";
                    }
                    else
                    {
                        true_source_action = target_action_node;
                        true_source_concept = target_concept_node;
                        true_target_action = source_action_node;
                        true_target_concept = source_concept_node;
                        direction_arrow = "->";
                    }

                    if (ev.direction == "backward")
                    {
                        if (direction_arrow == "->")
                            direction_arrow = "<-";
                        else
                            direction_arrow = "->";
                    }

                    // For the relationship text, concatenate every cs edge + its weight.
                    string relationship_text = "";
                    float weight = 0;

                    Edge source_middle_edge = new Edge(id: new_edge_id_counter,
                        source: true_source_action,
                        target: middle_node,
                        relationship: "",
                        weight: 0f);
                }
                // Make an edge from the middle node to the target node. 
                */
            }
        }

        // Start with hypothesized elements disabled.
        //this.DisableHypothesized();

        // Do Action Sequence stuff here.

        /*
        // Grab a causal sequence hyp.
        CausalSequenceHyp causal_sequence_hyp = null;
        foreach (Hypothesis hyp in this.sensemaker_data.hypotheses.Values)
        {
            if (hyp is CausalSequenceHyp)
            {
                var cs_hyp = (CausalSequenceHyp)hyp;
                // Make sure it has some multi causal path evidence.
                if (cs_hyp.multi_causal_path_evs.Count == 0)
                    continue;
                // And that it's one of the accepted hypotheses for the first solution set.
                if (!this.active_solution.accepted_hypotheses.ContainsKey(cs_hyp.id))
                    continue;
                causal_sequence_hyp = cs_hyp;
                break;
            }
        }
        // Get its source and target actions nodes. 
        ActionNode source_action = causal_sequence_hyp.source_action;
        ActionNode target_action = causal_sequence_hyp.target_action;
        // Make new node controllers for them and place them at the bottom of the scene,
        // underneath their respective images.
        SceneImageController source_image_controller = this.scene_image_controllers[source_action.images.Keys.First<int>()];
        SceneImageController target_image_controller = this.scene_image_controllers[target_action.images.Keys.First<int>()];

        float source_x = source_image_controller.x + source_image_controller.Width / 2;
        float source_y = source_image_controller.y - 40;
        Vector3 source_action_position = new Vector3(source_x, source_y, this.node_z);
        int source_node_controller_index = -source_action.id;
        this.InitializeNode(source_action, source_action_position, node_controller_index: source_node_controller_index);

        float target_x = target_image_controller.x + target_image_controller.Width / 2;
        float target_y = target_image_controller.y - 40;
        Vector3 target_action_position = new Vector3(target_x, target_y, this.node_z);
        int target_node_controller_index = -target_action.id;
        this.InitializeNode(target_action, target_action_position, node_controller_index: target_node_controller_index);

        // Make an edge between the two actions whose text contains
        // all of the causal path ev edge relationships.
        // and whose score is the sum of the causal path ev scores for this
        // solution set.
        string relationship_text = "";
        float weight = 0;
        foreach (CausalPathEv ev in causal_sequence_hyp.causal_path_evs)
        {
            GraphPath path = ev.concept_path;
            // Get the edge.
            Edge path_edge = path.steps[0].next_edge;
            // The source and target of the edge should be ConceptNodes, which
            // will line up with the Nodes of the path's steps.
            // Write the text such that the source action is always first and the target action is always last.
            string edge_string = ""; 
            if (source_action.HasConcept((ConceptNode)path_edge.source))
                edge_string = $"{path_edge.source}->{path_edge.relationship}({path_edge.weight})->{path_edge.target}\n";
            else
                edge_string = $"{path_edge.target}<-{path_edge.relationship}({path_edge.weight})<-{path_edge.source}\n";
            relationship_text += edge_string;

            // Sum the scores for each causal path ev.
            weight += ev.GetWeightedScore(this.active_solution_set, this.active_solution);
        }
        relationship_text += $"Total Weight: {weight}";

        Edge causal_sequence_edge = new Edge(id: -1,
            source: source_action,
            target: target_action,
            relationship: relationship_text,
            weight: weight);

        // Make the edge's game object.
        var edge_object = Instantiate(this.edge_prefab, Vector3.zero,
            Quaternion.identity);
        // Get and initialize the edge controller.
        var source_node_controller = source_action.NodeController;
        var target_node_controller = target_action.NodeController;
        var edge_controller = edge_object.GetComponent<EdgeController>();
        edge_controller.Initialize(causal_sequence_edge, source_node_controller, target_node_controller, this.gui_controller, 0);
        this.edge_controllers[causal_sequence_edge.id] = edge_controller;
        // Give the edge a reference to its edge controller.
        causal_sequence_edge.SetEdgeController(edge_controller);

        // For the first multi causal path ev
        // Make an intermediary node representing the middle concept of the path.
        // Place it at the midpoint between the actions, but lower in the y. 
        // Make an edge from source to middle
        // Make an edge from from middle to target
        */

        initialized = true;
    }

    // Deinitialize and return to a state before initialization.
    public void Deinitialize()
    {
        Console.WriteLine("Deinitializing main app");
        // Deinitialize scene images.
        foreach (SceneImageController controller in this.scene_image_controllers.Values)
        {
            GameObject scene_image_object = controller.gameObject;
            GameObject.Destroy(scene_image_object);
        }
        this.scene_image_controllers.Clear();

        // Deinitialize nodes.
        foreach (NodeController controller in this.node_controllers.Values)
        {
            // Deinitialize the node before destroying it.
            controller.Deinitialize();
            GameObject node_object = controller.gameObject;
            GameObject.Destroy(node_object);
        }
        this.node_controllers.Clear();

        // Deinitialize edges.
        foreach (EdgeController controller in this.edge_controllers.Values)
        {
            // Deinitialize the edge before destroying it.
            controller.Deinitialize();
            GameObject edge_object = controller.gameObject;
            GameObject.Destroy(edge_object);
        }
        this.edge_controllers.Clear();

        // Deinitialize data.
        //  active solution set
        this.active_solution_set = null;
        //  active solution
        this.active_solution = null;
        //  sensemaker data
        this.sensemaker_data = null;

        

        // Reset initialization variables.
        this.initialized = false;
        this.initialization_started = false;
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
            var new_scene_image_controller = new_scene_image.GetComponent<SceneImageController>();
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
        this.shared_action_counts = new Dictionary<Tuple<int, int>, int>();
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
        var scene_image = this.scene_image_controllers[object_node.images.Keys.First<int>()];
        var bounding_box = object_node.scene_graph_objects[0].bounding_box;
        float x = scene_image.x + bounding_box.x;
        float y = scene_image.y + scene_image.Height - bounding_box.y;
        float mid_x = x + bounding_box.w / 2;
        float mid_y = y - bounding_box.h / 2;
        Vector3 midpoint = new Vector3(mid_x, mid_y, this.node_z);

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

        // Some pairs of objects have more than one action between them. In that case,
        // we have to count the number of actions currently between them and deflect
        // the midpoint perpendicular to the true midpoint. 
        if (action_node.object_ is not null)
        {
            var object_position = this.node_controllers[action_node.object_.id].transform.position;
            float max_x = Mathf.Max(subject_position.x, object_position.x);
            float min_x = Mathf.Min(subject_position.x, object_position.x);
            float max_y = Mathf.Max(subject_position.y, object_position.y);
            float min_y = Mathf.Min(subject_position.y, object_position.y);
            Vector3 original_midpoint = new Vector3(min_x + (max_x - min_x) / 2, 
                min_y + (max_y - min_y) / 2, this.node_z);
            // Get the id pair for the subject and object of this action.
            int smaller_id = Math.Min(action_node.subject.id, action_node.object_.id);
            int larger_id = Math.Max(action_node.subject.id, action_node.object_.id);
            Tuple<int, int> id_pair = new Tuple<int, int>(smaller_id, larger_id);
            if (!this.shared_action_counts.ContainsKey(id_pair))
                this.shared_action_counts[id_pair] = 0;
            // Get how many actions this subject and object share. 
            int shared_action_count = this.shared_action_counts[id_pair];

            // Calculate the deflected midpoint.
            // The line from the source point to the target point.
            Vector3 original_line = object_position - subject_position;
            // The line perpendicular to the line from source to target points.
            // Set perp_line z to 0 so we're only calculating in 2d.
            Vector3 perp_line = new Vector3(original_line.y,
                original_line.x,
                0);
            // Travel in the direction of the perpendicular line a distance
            // based on the number of actions there are between this
            // action's two endpoints objects.
            float deflection_interval = 10f;
            float deflection_distance = deflection_interval * shared_action_count;
            Vector3 deflected_midpoint = original_midpoint + perp_line.normalized * deflection_distance;

            // Set the midpoint to the deflected midpoint.
            midpoint = deflected_midpoint;

            // Increase the shared action count.
            this.shared_action_counts[id_pair] += 1;
        }
        else
        {
            // If the Action only has a subject, put its node a random distance 
            // away in a random direction from its subject's node.
            float diameter = 2 * subject_controller.Size.x;
            float x_distance = UnityEngine.Random.Range(1 * diameter, 4 * diameter);
            float y_distance = UnityEngine.Random.Range(1 * diameter, 4 * diameter);
            // Randomly negate the distances.
            if (UnityEngine.Random.Range(1, 2) == 1)
            {
                x_distance *= -1;
            }
            if (UnityEngine.Random.Range(1, 2) == 1)
            {
                y_distance *= -1;
            }
            midpoint = new Vector3(subject_position.x + x_distance,
                subject_position.y + y_distance, this.node_z);
        }
        
        this.InitializeNode(action_node, midpoint);
    }

    // Initialize a node at the position passed in.
    // Optionally pass in a node controller index, to index the node controller that's
    // created for this node in the global node_controller dictionary. 
    private void InitializeNode(Node node, Vector3 position, Hypothesis hypothesis = null,
        int? node_controller_index = null)
    {
        var node_object = Instantiate(this.node_prefab, position, 
            Quaternion.identity);
        var node_controller = node_object.GetComponent<NodeController>();
        node_controller.Initialize(node, this.scene_image_controllers, this.gui_controller, hypothesis);
        if (node_controller_index is null)
            this.node_controllers[node.id] = node_controller;
        else
            this.node_controllers[(int)node_controller_index] = node_controller;
        // Give the node a reference to its node controller.
        node.SetNodeController(node_controller);
    }

    // Initialize an edge.
    private void InitializeEdge(Edge edge, Hypothesis hypothesis = null)
    {
        // Don't initialize the edge again if it's already been initialized.
        if (this.EdgeIsInitialized(edge))
        {
            return;
        }

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

        // Go through existing edge controllers and count how many edges have already
        // been made with these nodes as endpoints.
        int parallel_edge_count = 0;

        foreach (EdgeController existing_edge_controller in this.edge_controllers.Values)
        {
            if ((existing_edge_controller.edge.source.id == edge.source.id 
                && existing_edge_controller.edge.target.id == edge.target.id) ||
                (existing_edge_controller.edge.source.id == edge.target.id
                && existing_edge_controller.edge.target.id == edge.source.id))
            {
                parallel_edge_count += 1;
            }
        }

        // Make the edge's game object.
        var edge_object = Instantiate(this.edge_prefab, Vector3.zero, 
            Quaternion.identity);
        // Get and initialize the edge controller.
        var edge_controller = edge_object.GetComponent<EdgeController>();
        edge_controller.Initialize(edge, source_controller, target_controller, this.gui_controller, parallel_edge_count, hypothesis);
        this.edge_controllers[edge.id] = edge_controller;
        // Give the edge a reference to its edge controller.
        edge.SetEdgeController(edge_controller);
    }

    // Returns whether or not the given edge has already been initialized by the application.
    private bool EdgeIsInitialized(Edge edge)
    {
        if (this.edge_controllers.ContainsKey(edge.id))
            return true;
        else
            return false;
    }

    // Set the canon causal sequence hyps and their scores.
    public void DetermineCanonCausalSequence()
    {
        // Go through the causal sequence hypotheses and find the highest scoring
        // causal sequence hyp between each image. 
        // Make a dict of all causal sequence hyps indexed by the images they're between.
        int lowest_image_index = this.sensemaker_data.knowledge_graph.lowest_image_index;

        Dictionary<Tuple<int, int>, List<CausalSequenceHyp>> bridging_cs_hyps = new Dictionary<Tuple<int, int>, List<CausalSequenceHyp>>();
        foreach (Hypothesis hyp in this.sensemaker_data.hypotheses.Values)
        {
            if (!(hyp is CausalSequenceHyp))
                continue;
            // If this hypothesis was rejected, it can't be in the canon causal sequence.
            if (!hyp.Accepted(this.active_solution_set, this.active_solution))
                continue;
            CausalSequenceHyp cs_hyp = (CausalSequenceHyp)hyp;
            // Find out what image it starts at and what image it ends at.
            // Do this by getting the hypothesis' source action instance's image id
            // and target action instance's image id.
            ImageData start_image = cs_hyp.source_action.images.Values.First();
            ImageData end_image = cs_hyp.target_action.images.Values.First();
            Tuple<int, int> image_index_pair = new Tuple<int, int>(start_image.index, end_image.index);
            if (!bridging_cs_hyps.ContainsKey(image_index_pair))
                bridging_cs_hyps[image_index_pair] = new List<CausalSequenceHyp>();
            bridging_cs_hyps[image_index_pair].Add(cs_hyp);
        }
        int index_0 = 0 + lowest_image_index;
        int index_1 = 1 + lowest_image_index;
        int index_2 = 2 + lowest_image_index;
        // Between image 0 and 1
        Tuple<int, int> image_index_0_1 = new Tuple<int, int>(index_0, index_1);
        this.canon_0_1_score = 0;
        this.canon_0_1_hyp = null;
        if (bridging_cs_hyps.ContainsKey(image_index_0_1))
        {
            foreach (CausalSequenceHyp hyp in bridging_cs_hyps[image_index_0_1])
            {
                float score = hyp.GetScore(this.active_solution_set, this.active_solution);
                if (score > this.canon_0_1_score)
                {
                    this.canon_0_1_score = score;
                    this.canon_0_1_hyp = hyp;
                }
            }// end foreach
        }//end if
        // Between image 1 and 2
        Tuple<int, int> image_index_1_2 = new Tuple<int, int>(index_1, index_2);
        this.canon_1_2_score = 0;
        this.canon_1_2_hyp = null;
        if (bridging_cs_hyps.ContainsKey(image_index_1_2))
        {
            foreach (CausalSequenceHyp hyp in bridging_cs_hyps[image_index_1_2])
            {
                float score = hyp.GetScore(this.active_solution_set, this.active_solution);
                if (score > this.canon_1_2_score)
                {
                    this.canon_1_2_score = score;
                    this.canon_1_2_hyp = hyp;
                }
            }// end foreach
        }//end if
        // Between image 0 and 2
        Tuple<int, int> image_index_0_2 = new Tuple<int, int>(index_0, index_2);
        this.canon_0_2_score = 0;
        this.canon_0_2_hyp = null;
        if (bridging_cs_hyps.ContainsKey(image_index_0_2))
        {
            foreach (CausalSequenceHyp hyp in bridging_cs_hyps[image_index_0_2])
            {
                float score = hyp.GetScore(this.active_solution_set, this.active_solution);
                if (score > this.canon_0_2_score)
                {
                    this.canon_0_2_score = score;
                    this.canon_0_2_hyp = hyp;
                }
            }// end foreach
        }//end if
    }//end DetermineCanonCausalSequence

    // Cycle to the next solution set.
    public void CycleActiveSolutionSet()
    {
        // Get a list of all the ids of solution sets.
        List<int> solution_set_ids = this.sensemaker_data.solution_sets.Keys.ToList<int>();
        // Determine where the current active solution set is in the list.
        int current_index = solution_set_ids.IndexOf(this.active_solution_set.id);
        // Go to the next index, or to the first if we're already at the last index.
        current_index += 1;
        if (current_index >= solution_set_ids.Count)
        {
            current_index = 0;
        }
        SolutionSet next_solution_set = this.sensemaker_data.solution_sets[solution_set_ids[current_index]];
        // Set it as the new active solution set.
        this.SetActiveSolutionSet(next_solution_set);
    }

    // Switch to a different solution set.
    public void SetActiveSolutionSet(SolutionSet solution_set)
    {
        print("New active solution set: " + solution_set.id.ToString());
        this.active_solution_set = solution_set;
        this.active_solution = solution_set.solutions[0];
        // Determine what the canon causal sequence is now.
        this.DetermineCanonCausalSequence();
        // Tell each edge controller to update itself for the new solution set.
        foreach (EdgeController edge_controller in this.edge_controllers.Values)
        {
            edge_controller.UpdateSolutionSet();
        }
        // Tell the GUI controller that the solution set was updated.
        this.gui_controller.UpdateSolutionSet();
    }

    // Enable all hypothesized elements.
    public void EnableHypothesized()
    {
        // Enable hypothesized nodes.
        foreach (NodeController node_controller in this.node_controllers.Values)
        {
            if (node_controller.Hypothesized)
            {
                node_controller.gameObject.SetActive(true);
            }
        }
        // Enable hypothesized edges.
        foreach (EdgeController edge_controller in this.edge_controllers.Values)
        {
            if (edge_controller.Hypothesized)
            {
                edge_controller.gameObject.SetActive(true);
            }
        }
    }
    // Disable all hypothesized elements.
    public void DisableHypothesized()
    {
        // Disable hypothesized nodes.
        foreach (NodeController node_controller in this.node_controllers.Values)
        {
            if (node_controller.Hypothesized)
            {
                node_controller.gameObject.SetActive(false);
            }
        }
        // Disable hypothesized edges.
        foreach (EdgeController edge_controller in this.edge_controllers.Values)
        {
            if (edge_controller.Hypothesized)
            {
                edge_controller.gameObject.SetActive(false);
            }
        }
    }

    // Update is called once per frame
    void Update()
    {
        /*
        if (!this.initialization_started)
        {
            if (this.network_handler.connected)
            {
                this.initialization_started = true;
                StartCoroutine(this.Initialize());
            }
        }
        */
    }

    private void OnApplicationQuit()
    {
        // Tell the sensemaker listener to stop running when the application ends.
        //this.gameObject.GetComponent<NetworkHandler>().Stop();
    }

    // Properties
    public GUIController GUIController
    {
        get { return this.gui_controller; }
    }
    
}