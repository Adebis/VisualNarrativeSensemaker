using System.IO;

using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

public class SceneImageController : MonoBehaviour
{
    public ImageData image_data;
    // The raw image component connected to this script's game object.
    private RawImage raw_image;

    public void Initialize(ImageData image_data, float x_offset)
    {
        this.image_data = image_data;
        this.raw_image = this.GetComponent<RawImage>();
        // Read in the image as a byte array and load it onto a 2d texture.\
        string top_directory = Path.GetDirectoryName(Path.GetDirectoryName(Application.dataPath));
        string image_file_path = Path.Join(top_directory, image_data.file_path.Replace("/", "\\"));
        print("Loading image at " + image_file_path);
        byte[] image_bytes = File.ReadAllBytes(image_file_path);
        // Turn it into a 2D texture.
        var image_texture = new Texture2D(1, 1);
        image_texture.LoadImage(image_bytes);
        // Scale the RawImage UI element to the image texture.
        this.raw_image.rectTransform.sizeDelta = new Vector2(image_texture.width, image_texture.height);
        // Set the texture to the image texture we just made.
        this.raw_image.texture = image_texture;
        // Offset the image so that they're lined up next to each other.
        this.transform.position += new Vector3(x_offset, 0, 0);
    }

    // Start is called before the first frame update
    void Start()
    {
        
    }

    // Update is called once per frame
    void Update()
    {
        
    }

    // Dimensions, for ease of access.
    public float Width
    {
        get
        {
            return this.raw_image.rectTransform.sizeDelta.x;
        }
    }
    public float Height
    {
        get
        {
            return this.raw_image.rectTransform.sizeDelta.y;
        }   
    }
    public float x
    {
        get
        {
            return this.transform.position.x;
        }
    }
    public float y
    {
        get
        {
            return this.transform.position.y;
        }
    }
}
