using Newtonsoft.Json.Linq;

using System.Collections;
using System.Collections.Generic;

public struct CommonSenseNode
{
    public int id;
    public string uri;
    public List<string> labels;
    public List<int> edge_ids;

    public CommonSenseNode(JToken token)
    {
        this.id = (int)token["id"];
        this.uri = (string)token["uri"];
        this.labels = new List<string>();
        foreach (JToken label_token in token["labels"])
        {
            this.labels.Add((string)label_token);
        }
        this.edge_ids = new List<int>();
        foreach (JToken edge_id in token["edge_ids"])
        {
            this.edge_ids.Add((int)edge_id);
        }
    }
}

public struct Synset
{
    public string name;
    public string word;
    public string pos;
    public string sense;

    public Synset(JToken token)
    {
        this.name = (string)token["name"];
        this.word = (string)token["word"];
        this.pos = (string)token["pos"];
        this.sense = (string)token["sense"];
    }
}