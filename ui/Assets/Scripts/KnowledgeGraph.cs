using JetBrains.Annotations;
using Newtonsoft.Json.Linq;

using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine.UIElements;

public class KnowledgeGraph
{
    // The imported data for this knowledge graph.
    private KnowledgeGraphImport imported_data;

    // These dictionaries are keyed by ids of their respective items.
    public Dictionary<int, CommonSenseNode> commonsense_nodes;
    public Dictionary<int, CommonSenseEdge> commonsense_edges;
    public Dictionary<int, ImageData> images;
    public Dictionary<int, Node> nodes;
    public Dictionary<int, Edge> edges;

    // How many instances are in this knowledge graph.
    public int instance_count;

    public int lowest_image_index;

    public KnowledgeGraph(KnowledgeGraphImport imported_data)
    {
        this.instance_count = 0;
        this.imported_data = imported_data;

        // Commonsense nodes.
        this.commonsense_nodes = new Dictionary<int, CommonSenseNode>();
        foreach (CommonSenseNodeImport data in imported_data.commonsense_nodes)
        {
            this.commonsense_nodes.Add(data.id, new CommonSenseNode(data));
        }

        // Commonsense Edges.
        this.commonsense_edges = new Dictionary<int, CommonSenseEdge>();
        foreach (CommonSenseEdgeImport data in imported_data.commonsense_edges)
        {
            this.commonsense_edges.Add(data.id, new CommonSenseEdge(data));
        }

        // Images.
        this.lowest_image_index = int.MaxValue;
        this.images = new Dictionary<int, ImageData>();
        foreach (ImageImport data in imported_data.images)
        {
            this.images.Add(data.id, new ImageData(data));
            if (data.index < this.lowest_image_index)
                this.lowest_image_index = data.index;
        }

        // Nodes.
        this.nodes = new Dictionary<int, Node>();
        // Concept nodes.
        foreach (ConceptImport data in imported_data.concepts)
        {
            this.nodes.Add(data.id, new ConceptNode(data));
        }
        // Object nodes.
        foreach (ObjectImport data in imported_data.objects)
        {
            this.nodes.Add(data.id, new ObjectNode(data));
            this.instance_count += 1;
        }
        // Action nodes.
        foreach (ActionImport data in imported_data.actions)
        {
            this.nodes.Add(data.id, new ActionNode(data));
            this.instance_count += 1;
        }

        // Edges.
        this.edges = new Dictionary<int, Edge>();
        foreach (EdgeImport data in imported_data.edges)
        {
            this.edges.Add(data.id, new Edge(data));
        }

        // Now that all classes have been initialized, we
        // can resolve id references and populate whatever hasn't been
        // populated in those classes.
        // Populate items in nodes.
        foreach (Node node in this.nodes.Values)
        {
            node.PopulateEdges(this.edges);
            // Different node subclasses have different pieces of information
            // that need to be populated.
            if (node is ConceptNode)
            {
                ((ConceptNode)node).PopulateCommonSenseNodes(this.commonsense_nodes);
            }
            else if (node is InstanceNode)
            {
                if (node is ObjectNode)
                {
                    ((ObjectNode)node).PopulateImages(this.images);
                    ((ObjectNode)node).PopulateNodes(this.nodes);
                }
                else if (node is ActionNode)
                {
                    ((ActionNode)node).PopulateImages(this.images);
                    ((ActionNode)node).PopulateNodes(this.nodes);
                }
            }
        }

        // Populate items in edges.
        foreach (Edge edge in this.edges.Values)
        {
            edge.PopulateNodes(this.nodes);
            edge.PopulateCommonSenseEdges(this.commonsense_edges);
        }
    }

    public override string ToString()
    {
        string return_string = string.Format("Number of commonsense nodes: {0}\n",
            this.commonsense_nodes.Count);
        return_string += "Images: ";
        foreach (ImageData image in this.images.Values)
        {
            return_string += image.id.ToString() + '|';
        }
        return return_string;
    }
}

public class Edge
{
    private EdgeImport imported_data;

    public int id;
    public Node source;
    public Node target;
    public string relationship;
    public float weight;
    // Can be null.
    public CommonSenseEdge commonsense_edge;

    // The edge's game object controller.
    private EdgeController edge_controller;

    // The hypothesis that led to the creation of this Edge, if any.
    public Hypothesis hypothesis;

    public Edge(EdgeImport imported_data, Hypothesis hypothesis = null)
    {
        this.imported_data = imported_data;

        this.id = imported_data.id;
        this.source = null;
        this.target = null;
        this.relationship = imported_data.relationship;
        this.weight = imported_data.weight;
        this.commonsense_edge = null;
        this.edge_controller = null;
        this.hypothesis = hypothesis;
    }
    public Edge(int id, Node source, Node target, string relationship, float weight)
    {
        this.imported_data = null;
        this.id = id;
        this.source = source;
        this.target = target;
        this.relationship = relationship;
        this.weight = weight;
        this.commonsense_edge = null;
        this.edge_controller = null;
        this.hypothesis = null;
    }

    public void PopulateNodes(Dictionary<int, Node> all_nodes)
    {
        this.source = all_nodes[this.imported_data.source_id];
        this.target = all_nodes[this.imported_data.target_id];
    }

    public void PopulateCommonSenseEdges(Dictionary<int, CommonSenseEdge> all_commonsense_edges)
    {
        if (this.commonsense_edge is not null)
            this.commonsense_edge = all_commonsense_edges[this.imported_data.commonsense_edge_id];
    }

    public void SetEdgeController(EdgeController edge_controller)
    {
        this.edge_controller = edge_controller;
    }

    public override string ToString()
    {
        return (this.source.name + "->" + this.relationship + " (" + this.weight.ToString() + ")" 
            + "->" + this.target.name);
    }

    // Properties
    public EdgeController EdgeController
    {
        get { return edge_controller; }
    }
}

public class Node
{
    private NodeImport imported_data;

    public int id;
    public string label;
    public string name;
    public Dictionary<int, Edge> edges;
    public bool hypothesized;
    // The node's game object controller.
    private NodeController node_controller;

    public Node(NodeImport imported_data)
    {
        this.imported_data = imported_data;

        this.id = imported_data.id;
        this.label = imported_data.label;
        this.name = imported_data.name;
        
        this.edges = new Dictionary<int, Edge>();

        this.hypothesized = imported_data.hypothesized;
        this.node_controller = null;
    }

    public void SetNodeController(NodeController node_controller)
    {
        this.node_controller = node_controller;
    }

    // Populate this node's edges from a dictionary of all the edges
    // in a knowledge graph based on the node's imported data.
    public void PopulateEdges(Dictionary<int, Edge> all_edges)
    {
        foreach (int edge_id in this.imported_data.edge_ids)
        {
            this.edges.Add(edge_id, all_edges[edge_id]);
        }
    }

    public override string ToString()
    {
        string return_string = "";

        return_string = this.name;

        return return_string;
    }

    // Properties
    public NodeController NodeController
    {
        get { return this.node_controller; }
    }
    public NodeImport ImportedData
    {
        get { return this.imported_data; }
    }
}

public class ConceptNode : Node
{
    public string concept_type;
    public Synset synset;
    public Dictionary<int, CommonSenseNode> commonsense_nodes;
    public PolarityScoresImport polarity_scores;
    public float sentiment;

    public ConceptNode(ConceptImport imported_data) : base(imported_data)
    {
        this.concept_type = imported_data.concept_type;
        this.synset = new Synset(imported_data.synset);
        this.commonsense_nodes = new Dictionary<int, CommonSenseNode>();
        this.polarity_scores = imported_data.polarity_scores;
        this.sentiment = imported_data.sentiment;
    }

    public void PopulateCommonSenseNodes(Dictionary<int, CommonSenseNode> all_commonsense_nodes)
    {
        foreach (int commonsense_node_id in this.ImportedData.commonsense_node_ids)
        {
            this.commonsense_nodes.Add(commonsense_node_id, all_commonsense_nodes[commonsense_node_id]);
        }
    }

    // Properties
    public new ConceptImport ImportedData
    {
        get { return (ConceptImport)base.ImportedData; }
    }
}

public class InstanceNode : Node
{
    public Dictionary<int, ConceptNode> concept_nodes;
    public Dictionary<int, ImageData> images;
    public float focal_score;

    public InstanceNode(InstanceImport imported_data) : base(imported_data)
    {
        this.concept_nodes = new Dictionary<int, ConceptNode>();
        this.images = new Dictionary<int, ImageData>();
        this.focal_score = imported_data.focal_score;
    }

    public void PopulateNodes(Dictionary<int, Node> all_nodes)
    {
        foreach (int node_id in this.ImportedData.concept_ids)
        {
            this.concept_nodes[node_id] = (ConceptNode)all_nodes[node_id];
        }
    }

    public void PopulateImages(Dictionary<int, ImageData> all_images)
    {
        foreach (int image_id in this.ImportedData.image_ids)
        {
            this.images.Add(image_id, all_images[image_id]);
        }
    }

    public bool HasConcept(ConceptNode concept_node)
    {
        if (this.concept_nodes.ContainsKey(concept_node.id))
            return true;
        else
            return false;
    }

    // Properties
    public new InstanceImport ImportedData
    {
        get { return (InstanceImport)base.ImportedData; }
    }
}

public class ObjectNode : InstanceNode
{
    public List<SceneGraphObject> scene_graph_objects;
    public List<string> attributes;
    
    public ObjectNode(ObjectImport imported_data) : base(imported_data)
    {
        this.scene_graph_objects = new List<SceneGraphObject>();
        foreach (SceneGraphObjectImport data in imported_data.scene_graph_objects)
        {
            this.scene_graph_objects.Add(new SceneGraphObject(data));
        }
        this.attributes = new List<string>(imported_data.attributes);
    }

    // Populate images in all of this object node's scene graph objects.
    public new void PopulateImages(Dictionary<int, ImageData> all_images)
    {
        base.PopulateImages(all_images);
        foreach (SceneGraphObject scene_graph_object in this.scene_graph_objects)
        {
            scene_graph_object.PopulateImage(all_images);
        }
    }

    // Properties
    // Get a bounding box representing this node.
    public BoundingBox BoundingBox
    {
        get{ return this.scene_graph_objects[0].bounding_box; }
    }
    public new ObjectImport ImportedData
    {
        get { return (ObjectImport)base.ImportedData; }
    }
}

public class ActionNode : InstanceNode
{
    public ObjectNode subject;
    // Object can be null.
    public ObjectNode object_;
    // Scene graph relationship can be null.
    public SceneGraphRelationship scene_graph_rel;

    public ActionNode(ActionImport imported_data) : base(imported_data)
    {
        this.object_ = null;
        // If the predicate is null, the scene graph rel is null.
        if (imported_data.scene_graph_rel.predicate is not null)
            this.scene_graph_rel = new SceneGraphRelationship(imported_data.scene_graph_rel);
        else
            this.scene_graph_rel = null;
    }

    // Populate the subject and object_ from the dictionary of all
    // nodes from the knowledge graph.
    public new void PopulateNodes(Dictionary<int, Node> all_nodes)
    {
        base.PopulateNodes(all_nodes);
        this.subject = (ObjectNode)all_nodes[this.ImportedData.subject_id];
        if (this.ImportedData.obj_id != -1)
        {
            this.object_ = (ObjectNode)all_nodes[this.ImportedData.obj_id];
        }
    }

    // Populate Images in this action's scene graph relationship, if it exists.
    public new void PopulateImages(Dictionary<int, ImageData> all_images)
    {
        base.PopulateImages(all_images);
        if (this.scene_graph_rel is not null)
        {
            this.scene_graph_rel.PopulateImage(all_images);
        }
    }

    // Properties
    public new ActionImport ImportedData
    {
        get { return (ActionImport)base.ImportedData; }
    }
}

public class Step
{
    public StepImport imported_data;

    public int id;
    public Node node;
    public Step next_step;
    public Edge next_edge;
    public Step previous_step;
    public Edge previous_edge;

    public Step(StepImport imported_data)
    {
        this.imported_data = imported_data;
        this.id = imported_data.id;
    }

    public void PopulateNodes(Dictionary<int, Node> all_nodes)
    {
        this.node = all_nodes[this.imported_data.node_id];
    }

    public void PopulateEdges(Dictionary<int, Edge> all_edges)
    {
        // If there is no next or previous edge, their edge id in the imported data
        // will be -1. 
        if (this.imported_data.next_edge_id != -1)
            this.next_edge = all_edges[this.imported_data.next_edge_id];
        if (this.imported_data.previous_edge_id != -1)
            this.previous_edge = all_edges[this.imported_data.previous_edge_id];
    }

    public void PopulateSteps(List<Step> all_steps)
    {
        foreach (Step step in all_steps)
        {
            if (step.id == this.imported_data.next_step_id)
                this.next_step = step;
            else if (step.id == this.imported_data.previous_step_id)
                this.previous_step = step;
        }
    }
}

public class MultiStep
{
    public MultiStepImport imported_data;

    public int id;
    public List<Node> nodes;
    public MultiStep next_step;
    public List<Edge> next_edges;
    public MultiStep previous_step;
    public List<Edge> previous_edges;

    public MultiStep(MultiStepImport imported_data)
    {
        this.imported_data = imported_data;
        this.id = imported_data.id;
        this.nodes = new List<Node>();
        this.next_edges = new List<Edge>();
        this.previous_edges = new List<Edge>();
    }

    public void PopulateNodes(Dictionary<int, Node> all_nodes)
    {
        foreach (int node_id in this.imported_data.node_ids)
        {
            this.nodes.Add(all_nodes[node_id]);
        }
    }

    public void PopulateEdges(Dictionary<int, Edge> all_edges)
    {
        foreach (int edge_id in this.imported_data.next_edge_ids)
        {
            this.next_edges.Add(all_edges[edge_id]);
        }
        foreach (int edge_id in this.imported_data.previous_edge_ids)
        {
            this.previous_edges.Add(all_edges[edge_id]);
        }
    }

    public void PopulateMultiSteps(List<MultiStep> all_multi_steps)
    {
        foreach (MultiStep multi_step in all_multi_steps)
        {
            if (multi_step.id == this.imported_data.next_step_id)
                this.next_step = multi_step;
            else if (multi_step.id == this.imported_data.previous_step_id)
                this.previous_step = multi_step;
        }
    }

    public string NodesToString()
    {
        string return_string = "";

        foreach (Node node in this.nodes)
        {
            return_string += $"{node}, ";
        }
        // Remove trailing whitespace and comma.
        return_string = return_string.TrimEnd();
        return_string = return_string.TrimEnd(',');

        return return_string;
    }

    public string NextEdgesToString()
    {
        string return_string = "";

        foreach (Edge edge in this.next_edges)
        {
            return_string += edge.ToString() + '\n';
        }
        return_string = return_string.TrimEnd('\n');

        return return_string;
    }
}

public class GraphPath
{
    public PathImport imported_data;

    public int id;
    public List<Step> steps;

    public GraphPath(PathImport imported_data)
    {
        this.imported_data = imported_data;
        this.id = imported_data.id;
        this.steps = new List<Step>();

        foreach (StepImport data in imported_data.steps)
        {
            this.steps.Add(new Step(data));
        }
        foreach (Step step in this.steps)
        {
            step.PopulateSteps(this.steps);
        }
    }

    public void PopulateNodes(Dictionary<int, Node> all_nodes)
    {
        foreach (Step step in this.steps)
        {
            step.PopulateNodes(all_nodes);
        }
    }

    public void PopulateEdges(Dictionary<int, Edge> all_edges)
    {
        foreach (Step step in this.steps)
        {
            step.PopulateEdges(all_edges);
        }
    }
}

public class MultiGraphPath
{
    public MultiPathImport imported_data;

    public int id;
    public List<MultiStep> steps;

    public MultiGraphPath(MultiPathImport imported_data)
    {
        this.imported_data = imported_data;
        this.id = imported_data.id;
        this.steps = new List<MultiStep>();

        foreach (MultiStepImport data in imported_data.steps)
        {
            this.steps.Add(new MultiStep(data));
        }
        foreach (MultiStep step in this.steps)
        {
            step.PopulateMultiSteps(this.steps);
        }
    }

    public void PopulateNodes(Dictionary<int, Node> all_nodes)
    {
        foreach (MultiStep step in this.steps)
        {
            step.PopulateNodes(all_nodes);
        }
    }

    public void PopulateEdges(Dictionary<int, Edge> all_edges)
    {
        foreach (MultiStep step in this.steps)
        {
            step.PopulateEdges(all_edges);
        }
    }

    public override string ToString()
    {
        string return_string = "";
        // Print all the nodes for each step,
        // then all the edges for the next step.
        int step_counter = 0;
        foreach (MultiStep step in this.steps)
        {
            return_string += $"Step {step_counter}: {step.NodesToString()}";
            if (step.next_edges.Count > 0)
            {
                return_string += $"\n{step.NextEdgesToString()}";
            }//end if
            return_string += "\n";
            step_counter += 1;
        }// end foreach
        return_string = return_string.TrimEnd('\n');

        return return_string;
    }
}

