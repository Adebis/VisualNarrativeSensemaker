using Newtonsoft.Json.Linq;

using System.Collections;
using System.Collections.Generic;

public class KnowledgeGraph
{
    // These dictionaries are keyed by ids of their respective items.
    public Dictionary<int, CommonSenseNode> commonsense_nodes;
    public Dictionary<int, ImageData> images;
    public Dictionary<int, Node> nodes;
    public Dictionary<int, Edge> edges;

    public KnowledgeGraph(JToken token)
    {
        // Decode the commonsense nodes.
        this.commonsense_nodes = new Dictionary<int, CommonSenseNode>();
        foreach (JToken cs_node_token in token["commonsense_nodes"])
        {
            var new_cs_node = new CommonSenseNode(cs_node_token);
            commonsense_nodes[new_cs_node.id] = new_cs_node;
        }//end foreach

        // Decode the images.
        this.images = new Dictionary<int, ImageData>();
        foreach (JToken image_token in token["images"])
        {
            var new_image = new ImageData(image_token);
            images[new_image.id] = new_image;
        }

        // Decode the nodes.
        this.nodes = new Dictionary<int, Node>();
        // Check the node's type and make the matching Node subtype.
        foreach (JToken node_token in token["nodes"])
        {
            switch ((string)node_token["type"])
            {
                case "concept":
                {
                    var new_node = new ConceptNode(node_token);
                    nodes[new_node.id] = new_node;
                    break;
                }
                case "object":
                {
                    var new_node = new ObjectNode(node_token);
                    nodes[new_node.id] = new_node;
                    break;
                }
                case "action":
                {
                    var new_node = new ActionNode(node_token);
                    nodes[new_node.id] = new_node;
                    break;
                }
            }
        }

        // Decode the edges.
        this.edges = new Dictionary<int, Edge>();
        foreach (JToken edge_token in token["edges"])
        {
            var new_edge = new Edge(edge_token);
            edges[new_edge.id] = new_edge;
        }
        // Now that everything is decoded and owned by the knowledge graph, we
        // can resolve id references.
        // Give the nodes their edges.
        foreach (Node node in this.nodes.Values)
        {
            foreach (int edge_id in node.edge_ids)
            {
                node.edges[edge_id] = this.edges[edge_id];
            }
            // Give concept nodes their commonsense nodes.
            if (node is ConceptNode)
            {
                var concept_node = (ConceptNode)node;
                foreach (int cs_node_id in concept_node.commonsense_node_ids)
                {
                    concept_node.commonsense_nodes[cs_node_id] = this.commonsense_nodes[cs_node_id];
                }
            }
            // Give object nodes their concepts and images, and their
            // scene graph objects their images.
            else if (node is ObjectNode)
            {
                var object_node = (ObjectNode)node;
                foreach (int concept_id in object_node.concept_ids)
                {
                    object_node.concepts[concept_id] = (ConceptNode)this.nodes[concept_id];
                }
                foreach (int image_id in object_node.image_ids)
                {
                    object_node.images[image_id] = this.images[image_id];
                }
                foreach (var sg_obj in object_node.scene_graph_objects)
                {
                    sg_obj.image = this.images[sg_obj.image_id];
                }
            }
            // Give action nodes their concepts, images, subject, and object nodes.
            else if (node is ActionNode)
            {
                var action_node = (ActionNode)node;
                foreach (int concept_id in action_node.concept_ids)
                {
                    action_node.concepts[concept_id] = (ConceptNode)this.nodes[concept_id];
                }
                foreach (int image_id in action_node.image_ids)
                {
                    action_node.images[image_id] = this.images[image_id];
                }
                action_node.subject = (ObjectNode)this.nodes[action_node.subject_id];
                // Some actions don't have objects.
                if (action_node.object_id is not null)
                {
                    action_node.obj = (ObjectNode)this.nodes[(int)action_node.object_id];
                }
            }
        }
        // Give the edges their source and target nodes.
        foreach (Edge edge in this.edges.Values)
        {
            edge.source = this.nodes[edge.source_id];
            edge.target = this.nodes[edge.target_id];
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
    public int id;
    public int source_id;
    public Node source;
    public int target_id;
    public Node target;
    public string relationship;
    public float weight;
    public int? commonsense_edge_id;

    public Edge(JToken token)
    {
        this.id = (int)token["id"];
        this.source_id = (int)token["source"];
        this.target_id = (int)token["target"];
        this.relationship = (string)token["relationship"];
        this.weight = (float)token["weight"];
        // Can be null
        this.commonsense_edge_id = null;
        if (token["commonsense_edge"].Type != JTokenType.Null)
            this.commonsense_edge_id = (int?)token["commonsense_edge"];
    }
}

public class Node
{
    public int id;
    public string label;
    public string name;
    public List<int> edge_ids;
    public Dictionary<int, Edge> edges;
    public bool hypothesized;

    public Node(JToken token)
    {
        this.id = (int)token["id"];
        this.label = (string)token["label"];
        this.name = (string)token["name"];
        this.edge_ids = new List<int>();
        foreach (JToken edge_id in token["edges"])
        {
            this.edge_ids.Add((int)edge_id);
        }
        this.hypothesized = (bool)token["hypothesized"];

        this.edges = new Dictionary<int, Edge>();
    }
}

public class ConceptNode : Node
{
    public string concept_type;
    public Synset synset;
    public List<int> commonsense_node_ids;
    public Dictionary<int, CommonSenseNode> commonsense_nodes;

    public ConceptNode(JToken token) : base(token)
    {
        this.concept_type = (string)token["concept_type"];
        this.synset = new Synset(token["synset"]);
        this.commonsense_node_ids = new List<int>();
        foreach (JToken cs_node_id in token["commonsense_nodes"])
        {
            this.commonsense_node_ids.Add((int)cs_node_id);
        }
        this.commonsense_nodes = new Dictionary<int, CommonSenseNode>();
    }
}

public class ObjectNode : Node
{
    public List<int> concept_ids;
    public Dictionary<int, ConceptNode> concepts;
    public List<int> image_ids;
    public Dictionary<int, ImageData> images;
    public float focal_score;
    public List<SceneGraphObject> scene_graph_objects;
    public List<string> attributes;
    
    public ObjectNode(JToken token) : base(token)
    {
        this.concept_ids = new List<int>();
        foreach (JToken concept_id in token["concepts"])
        {
            this.concept_ids.Add((int)concept_id);
        }
        this.image_ids = new List<int>();
        foreach (JToken image_id in token["images"])
        {
            this.image_ids.Add((int)image_id);
        }
        this.focal_score = (float)token["focal_score"];
        this.scene_graph_objects = new List<SceneGraphObject>();
        foreach (JToken sg_object_token in token["scene_graph_objects"])
        {
            this.scene_graph_objects.Add(new SceneGraphObject(sg_object_token));
        }
        this.attributes = new List<string>();
        foreach (JToken attribute in token["attributes"])
        {
            this.attributes.Add((string)attribute);
        }
        this.concepts = new Dictionary<int, ConceptNode>();
        this.images = new Dictionary<int, ImageData>();
    }
}

public class ActionNode : Node
{
    public List<int> concept_ids;
    public Dictionary<int, ConceptNode> concepts;
    public List<int> image_ids;
    public Dictionary<int, ImageData> images;
    public float focal_score;
    public int subject_id;
    public ObjectNode subject;
    // Object id can be null.
    public int? object_id;
    public ObjectNode obj;
    // Scene graph relationship can be null.
    public SceneGraphRelationship scene_graph_rel;

    public ActionNode(JToken token) : base(token)
    {
        this.concept_ids = new List<int>();
        foreach (JToken concept_id in token["concepts"])
        {
            this.concept_ids.Add((int)concept_id);
        }
        this.image_ids = new List<int>();
        foreach (JToken image_id in token["images"])
        {
            this.image_ids.Add((int)image_id);
        }
        this.focal_score = (float)token["focal_score"];
        this.subject_id = (int)token["subject"];
        // Can be null
        this.object_id = null;
        if (token["obj"].Type != JTokenType.Null)
        {
            this.object_id = (int?)token["obj"];
        }
        // Can be null
        this.scene_graph_rel = null;
        if (token["scene_graph_rel"].Type != JTokenType.Null)
        {
            this.scene_graph_rel = new SceneGraphRelationship(token["scene_graph_rel"]);
        }
        this.concepts = new Dictionary<int, ConceptNode>();
        this.images = new Dictionary<int, ImageData>();
    }

}