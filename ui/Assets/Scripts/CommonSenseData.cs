using Newtonsoft.Json.Linq;

using System.Collections;
using System.Collections.Generic;

public class CommonSenseNode
{
    // Imported data
    private CommonSenseNodeImport imported_data;

    public int id;
    public string uri;
    public List<string> labels;
    public List<int> edge_ids;

    public CommonSenseNode(CommonSenseNodeImport imported_data)
    {
        this.imported_data = imported_data;

        this.id = imported_data.id;
        this.uri = imported_data.uri;
        this.labels = new List<string>(imported_data.labels);
        this.edge_ids = new List<int>(imported_data.edge_ids);
    }
}

public class CommonSenseEdge
{
    // Imported data
    private CommonSenseEdgeImport imported_data;

    public int id;
    public string uri;
    public List<string> labels;
    public string relation;
    public int start_node_id;
    public int end_node_id;
    public string start_node_uri;
    public string end_node_uri;
    public float weight;
    public string dimension;
    public string source;
    public string sentence;

    public CommonSenseEdge(CommonSenseEdgeImport imported_data)
    {
        this.imported_data = imported_data;

        this.id = imported_data.id;
        this.uri = imported_data.uri;
        this.labels = new List<string>(imported_data.labels);
        this.relation = imported_data.relation;
        this.start_node_id = imported_data.start_node_id;
        this.end_node_id = imported_data.end_node_id;
        this.start_node_uri = imported_data.start_node_uri;
        this.end_node_uri = imported_data.end_node_uri;
        this.start_node_uri = imported_data.start_node_uri;
        this.end_node_uri = imported_data.end_node_uri;
        this.weight = imported_data.weight;
        this.dimension = imported_data.dimension;
        this.source = imported_data.source;
        this.sentence = imported_data.sentence;
    }
}

public class Synset
{
    private SynsetImport imported_data;

    public string name;
    public string word;
    public string pos;
    public string sense;

    public Synset(SynsetImport imported_data)
    {
        this.imported_data = imported_data;

        this.name = imported_data.name;
        this.word = imported_data.word;
        this.pos = imported_data.pos;
        this.sense = imported_data.sense;
    }
}