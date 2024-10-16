using Newtonsoft.Json.Linq;

using System.Collections;
using System.Collections.Generic;
using System.Diagnostics.Tracing;

public class ImageData
{
    // Imported data
    private ImageImport imported_data;

    public int id;
    public int index;
    public string file_path;

    public ImageData(ImageImport imported_data)
    {
        this.imported_data = imported_data;

        this.id = imported_data.id;
        this.index = imported_data.index;
        this.file_path = imported_data.file_path;
    }
}

public class BoundingBox
{
    private BoundingBoxImport imported_data;

    public int h;
    public int w;
    public int x;
    public int y;

    public BoundingBox(BoundingBoxImport imported_data)
    {
        this.imported_data = imported_data;

        this.h = imported_data.h;
        this.w = imported_data.w;
        this.x = imported_data.x;
        this.y = imported_data.y;
    }
}

public class SceneGraphObject
{
    private SceneGraphObjectImport imported_data;

    public List<string> names;
    public List<Synset> synsets;
    public int object_id;
    public BoundingBox bounding_box;
    public ImageData image;
    public List<string> attributes;

    public SceneGraphObject(SceneGraphObjectImport imported_data)
    {
        this.imported_data = imported_data;
        this.names = new List<string>(imported_data.names);
        this.synsets = new List<Synset>();
        foreach (SynsetImport data in imported_data.synsets)
        {
            synsets.Add(new Synset(data));
        }
        this.object_id = imported_data.object_id;
        this.bounding_box = new BoundingBox(imported_data.bounding_box);
        this.image = null;
        this.attributes = new List<string>(imported_data.attributes);
    }

    public void PopulateImage(Dictionary<int, ImageData> all_images)
    {
        this.image = all_images[this.imported_data.image_id];
    }
}

public class SceneGraphRelationship
{
    private SceneGraphRelImport imported_data; 

    public string predicate;
    public List<Synset> synsets;
    public int relationship_id;
    public int subject_id;
    public int object_id;
    public ImageData image;

    public SceneGraphRelationship(SceneGraphRelImport imported_data)
    {
        this.imported_data = imported_data;

        this.predicate = imported_data.predicate;
        this.synsets = new List<Synset>();
        foreach (SynsetImport data in imported_data.synsets)
        {
            this.synsets.Add(new Synset(data));
        }
        this.relationship_id = imported_data.relationship_id;
        this.subject_id = imported_data.subject_id;
        this.object_id = imported_data.object_id;
        this.image = null;
    }

    public void PopulateImage(Dictionary<int, ImageData> all_images)
    {
        this.image = all_images[this.imported_data.image_id];
    }
}