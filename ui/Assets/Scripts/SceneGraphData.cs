using Newtonsoft.Json.Linq;

using System.Collections;
using System.Collections.Generic;

public struct ImageData
{
    public int id;
    public int index;
    public string file_path;

    public ImageData(JToken token)
    {
        this.id = (int)token["id"];
        this.index = (int)token["index"];
        this.file_path = (string)token["file_path"];
    }
}

public struct BoundingBox
{
    public int h;
    public int w;
    public int x;
    public int y;

    public BoundingBox(JToken token)
    {
        this.h = (int)token["h"];
        this.w = (int)token["w"];
        this.x = (int)token["x"];
        this.y = (int)token["y"];
    }
}

public class SceneGraphObject
{
    public List<string> names;
    public List<Synset> synsets;
    public int object_id;
    public BoundingBox bounding_box;
    public int image_id;
    public ImageData image;
    public List<string> attributes;

    public SceneGraphObject(JToken token)
    {
        this.names = new List<string>();
        foreach (JToken name in token["names"])
        {
            this.names.Add((string)name);
        }
        this.synsets = new List<Synset>();
        foreach (JToken synset_token in token["synsets"])
        {
            this.synsets.Add(new Synset(synset_token));
        }
        this.object_id = (int)token["object_id"];
        this.bounding_box = new BoundingBox(token["bounding_box"]);
        this.image_id = (int)token["image"];
        this.attributes = new List<string>();
        foreach (JToken attribute in token["attributes"])
        {
            this.attributes.Add((string)attribute);
        }
    }
}

public class SceneGraphRelationship
{
    public string predicate;
    public List<Synset> synsets;
    public int relationship_id;
    public int subject_id;
    public int object_id;
    public int image_id;

    public SceneGraphRelationship(JToken token)
    {
        this.predicate = (string)token["predicate"];
        this.synsets = new List<Synset>();
        foreach (JToken synset_token in token["synsets"])
        {
            this.synsets.Add(new Synset(synset_token));
        }
        this.relationship_id = (int)token["relationship_id"];
        this.subject_id = (int)token["subject_id"];
        this.object_id = (int)token["object_id"];
        this.image_id = (int)token["image"];
    }
}