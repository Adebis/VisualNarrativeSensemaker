using System.Collections;
using System.Collections.Generic;
using System.IO;

using TMPro;
using UnityEngine;
using UnityEngine.UI;
using SimpleFileBrowser;

using App = MainApplication;
using System;

public class SetupMenuController : MonoBehaviour
{
    // Prefabs
    public GameObject image_preview_prefab;

    // SetupMenu UI elements.
    private GameObject image_preview_panel;
    private GameObject run_button;
    private List<GameObject> image_previews;

    private List<List<int>> all_image_set_ids;
    private List<int> loaded_image_set_ids;
    private int current_image_set_index;

    private List<ParameterSet> loaded_parameter_sets;

    public bool force_generate_outputs;

    private bool can_run;

    // Start is called before the first frame update
    void Start()
    {
        this.image_preview_panel = this.gameObject.transform.Find("ImagePreviewPanel").gameObject;
        this.run_button = this.gameObject.transform.Find("RunButton").gameObject;
        this.image_previews = new List<GameObject>();
        this.all_image_set_ids = new List<List<int>>();

        this.can_run = false;
        this.loaded_image_set_ids = new List<int>();
        // Load an initial image set.
        string default_image_set_file_name = "test_13.csv";
        string top_directory = Path.GetDirectoryName(Path.GetDirectoryName(Application.dataPath));
        string image_sets_directory = Path.Join(top_directory, "\\data\\inputs\\image_sets");
        string default_image_set_path = Path.Join(image_sets_directory, default_image_set_file_name);
        this.current_image_set_index = 0;
        this.all_image_set_ids = this.ReadImageSetsFile(default_image_set_path);
        this.LoadImageSet(this.all_image_set_ids[this.current_image_set_index]);
        // Load initial parameter sets.
        this.loaded_parameter_sets = new List<ParameterSet>();
        string parameter_sets_directory = Path.Join(top_directory, "\\data\\inputs\\parameter_sets");
        string default_parameter_sets_file_name = "default_parameter_sets.json";
        string default_parameter_sets_path = Path.Join(parameter_sets_directory, default_parameter_sets_file_name);
        this.loaded_parameter_sets = this.ReadParameterSetsFile(default_parameter_sets_path);

        this.force_generate_outputs = true;

        print("Done starting SetupMenuController");
    }

    // Update is called once per frame
    void Update()
    {
        // Don't allow the run button to be interacted with until the network handler is connnected.
        if (!can_run)
        {
            if (App.Instance.network_handler.connected)
            {
                can_run = true;
                this.EnableRunButton();
            }
        }
        else
        {
            if (!App.Instance.network_handler.connected)
            {
                can_run = false;
                this.DisableRunButton();
            }
        }

        // Up and down on the arrow keys go up and down in the list of image set IDs.
        if (Input.GetKeyDown(KeyCode.UpArrow))
        {
            // Try to go up in the image set ids list.
            if (this.current_image_set_index > 0)
            {
                this.current_image_set_index -= 1;
                this.LoadImageSet(this.all_image_set_ids[this.current_image_set_index]);
            }
        }//end if
        else if (Input.GetKeyDown(KeyCode.DownArrow))
        {
            // Try to go down in the image set ids list.
            if (this.current_image_set_index < this.all_image_set_ids.Count - 1)
            {
                this.current_image_set_index += 1;
                this.LoadImageSet(this.all_image_set_ids[this.current_image_set_index]);
            }
        }//end else if
    }

    // Reads an image sets csv file.
    // Returns a list of lists of image set ids.
    private List<List<int>> ReadImageSetsFile(string file_path)
    {
        List<List<int>> all_image_set_ids = new List<List<int>>();
        string file_text = File.ReadAllText(file_path);
        // Parse the csv.
        string[] text_line_split = file_text.Split("\n");
        // Each new line is a new set of comma-separated image set ids.
        foreach (string text_line in text_line_split)
        {
            List<int> image_set_ids = new List<int>();
            string[] text_comma_split = text_line.Split(",");
            foreach (string id_string in text_comma_split)
            {
                image_set_ids.Add(int.Parse(id_string));
            }// end foreach
            all_image_set_ids.Add(image_set_ids);
        }//end foreach
        return all_image_set_ids;
    }

    // Load an image set.
    private void LoadImageSet(List<int> image_set_ids)
    {
        // First, unload the current image set.
        // Destroy all image preview objects.
        foreach (GameObject image_preview in this.image_previews)
        {
            Destroy(image_preview);
        }
        this.image_previews.Clear();

        // Place the image set ids in the image set name.
        string image_set_name = "";
        foreach (int image_set_id in image_set_ids)
        {
            image_set_name += image_set_id.ToString() + "_";
        }
        image_set_name.TrimEnd('_');

        this.gameObject.transform.Find("ImageSetName").GetComponent<TMP_Text>().text = image_set_name;
        // Find and display the image for each image set id.
        this.loaded_image_set_ids = image_set_ids;
        int x_offset = 0;
        int x_padding = 20;
        float max_height = 300;
        float max_width = 500;
        // Keep track of the maximum height of the images so we can adjust the entire
        // image preview label accordingly.
        int max_image_height = 0;
        foreach (int image_set_id in this.loaded_image_set_ids)
        {
            // Find the image file associated with this image set id.
            string image_file_name = image_set_id.ToString() + ".jpg";
            string top_directory = Path.GetDirectoryName(Path.GetDirectoryName(Application.dataPath));
            string images_directory = Path.Join(top_directory, "\\data\\inputs\\images");
            string image_file_path = Path.Join(images_directory, image_file_name);

            // Load the image, then make a 2D texture out of it.
            byte[] image_bytes = File.ReadAllBytes(image_file_path);
            Texture2D image_texture = new Texture2D(1, 1);
            image_texture.LoadImage(image_bytes);
            // Scale the RawImage UI element to the image texture.
            //this.raw_image.rectTransform.sizeDelta = new Vector2(image_texture.width, image_texture.height);

            // Offset the image so that they're lined up next to each other.
            //this.transform.position += new Vector3(x_offset, 0, 0);

            // Make an ImagePreview UI element and set its sprite to the image we just loaded.
            GameObject new_image_preview = Instantiate(this.image_preview_prefab, this.image_preview_panel.transform);
            // Offset the ImagePreview by the cumulative x offset.
            new_image_preview.transform.position = new Vector3(
                new_image_preview.transform.position.x + x_offset,
                new_image_preview.transform.position.y,
                new_image_preview.transform.position.z);
            Image image_preview_image = new_image_preview.GetComponent<Image>();
            // Cap the image's height and width. 
            float rect_height = image_texture.height;
            float rect_width = image_texture.width;
            float image_texture_ratio = (float)image_texture.height / (float)image_texture.width;
            if (rect_height > max_height)
            {
                rect_height = max_height;
                rect_width = rect_height / image_texture_ratio;
            }
            if (rect_width > max_width)
            {
                rect_width = max_width;
                rect_height = rect_width * image_texture_ratio;
            }
            new_image_preview.GetComponent<Image>().sprite = Sprite.Create(
                texture: image_texture,
                rect: new Rect(0, 0, image_texture.width, image_texture.height),
                pivot: new Vector2Int(0, 0));
            // Set the size of the image preview to the capped height and width sizes calculated above.
            new_image_preview.GetComponent<RectTransform>().sizeDelta = new Vector2(rect_width, rect_height);
            // Set its label's text to the image's file name.
            new_image_preview.transform.Find("Label").GetComponent<TMP_Text>().text = image_file_name;

            this.image_previews.Add(new_image_preview);

            if (image_texture.height > max_image_height)
                max_image_height = (int)rect_height;
            // Update the cumulative x offset.
            x_offset += (int)rect_width + x_padding;
        }// end foreach

        // Set the height of the image previews panel to fit the images within it.
        // -20 in width puts 20 pixels of padding on the right side, since the ImagePreviewPanel's width stretches to fit
        // the SetupMenu.
        this.image_preview_panel.GetComponent<RectTransform>().sizeDelta = new Vector2(-20, max_image_height + 60);
    }

    // Read a parameter sets file.
    // Returns a list of ParameterSets.
    private List<ParameterSet> ReadParameterSetsFile(string file_path)
    {
        // The parameter sets file should be in the same JSON format as 
        // the parameter sets in the sensemaker's output JSON files.
        //SensemakerDatasImport sensemaker_datas_import = JsonUtility.FromJson<SensemakerDatasImport>(json_text);
        string json_text = File.ReadAllText(file_path);
        ParameterSetsImport parameter_sets_data_import = JsonUtility.FromJson<ParameterSetsImport>(json_text);

        List<ParameterSet> parameter_sets = new List<ParameterSet>();
        foreach (ParameterSetImport data in parameter_sets_data_import.parameter_sets)
        {
            parameter_sets.Add(new ParameterSet(data));
        }

        return parameter_sets;
    }

    private void DisableRunButton()
    {
        run_button.GetComponent<Button>().interactable = false;
        //run_button.transform.Find("Text").GetComponent<TextMeshPro>().text = "Run";
    }
    private void EnableRunButton()
    {
        run_button.GetComponent<Button>().interactable = true;
        //run_button.transform.Find("Text").GetComponent<TextMeshPro>().text = "Run";
    }

    // Called when the ImageSetLoadButton is clicked.
    // Event subscribed in editor from the SetupMenu->ImageSetLoadButton object.
    public void OnClickImageSetLoadButton()
    {
        StartCoroutine(this.HandleLoadDialog());
    }

    private IEnumerator HandleLoadDialog()
    {
        string top_directory = Path.GetDirectoryName(Path.GetDirectoryName(Application.dataPath));
        string image_sets_directory = Path.Join(top_directory, "\\data\\inputs\\image_sets");

        FileBrowser.SetFilters(true, new FileBrowser.Filter("CSVs", ".csv"));
        FileBrowser.SetDefaultFilter(".csv");
        yield return FileBrowser.WaitForLoadDialog(pickMode: FileBrowser.PickMode.Files,
            initialPath: image_sets_directory);

        /*
        FileBrowser.ShowLoadDialog(onSuccess: (paths) => { print("Path chosen from load dialog: " + paths[0]); path_chosen = paths[0]; },
            onCancel: () => { print("Load dialog canceled."); },
            pickMode: FileBrowser.PickMode.Files,
            allowMultiSelection: false,
            initialPath: image_sets_directory,
            initialFilename: null,
            title: "Load",
            loadButtonText: "Select");
        */

        print($"File dialog success: {FileBrowser.Success}");

        if (FileBrowser.Success)
        {
            string[] file_dialog_results = FileBrowser.Result;
            print($"File dialog result 0: {file_dialog_results[0]}");
            this.all_image_set_ids = this.ReadImageSetsFile(file_path: file_dialog_results[0]);
            this.current_image_set_index = 0;
            this.LoadImageSet(this.all_image_set_ids[this.current_image_set_index]);
        }
    }

    // Called when the RunButton is clciked.
    // Event subscribed in editor from the SetupMenu->RunButton object.
    public void OnClickRunButton()
    {
        // Run the main application using the image set and parameters set in
        // the setup menu.

        // First, Deinitialize the main program if it's already initialized.
        if (App.Instance.initialized)
        {
            App.Instance.Deinitialize();
        }

        // Set 13 - kitchen, bike ride, picnic
        //image_set_ids = new List<int> { 2402873, 2391830, 2406899 };
        // Set 14 - bikes with dogs
        //image_set_ids = new List<int> { 2384081, 2361867, 2329428 };
        //List<int> image_set_ids = new List<int> { 2402873, 2391830, 2406899 };

        bool run_started = App.Instance.Run(image_set_ids: this.loaded_image_set_ids,
            parameter_sets: this.loaded_parameter_sets,
            force_generate_output: this.force_generate_outputs);
        // If the run successfully started, disable the setup menu.
        if (run_started)
        {
            this.gameObject.SetActive(false);
        }
    }


}
