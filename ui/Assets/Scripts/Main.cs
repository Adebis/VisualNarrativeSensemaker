using System.IO;
using Newtonsoft.Json;

using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class Main : MonoBehaviour
{
    // The name of the output json file that should be loaded.
    public string output_file_name;

    // Start is called before the first frame update
    void Start()
    {
        // Find the output directory, which should be under ../../data/outputs/
        // Go two directories up from Assets to get to VisualNarrativeSensemaker/
        string output_file_directory = Path.Join(Path.GetDirectoryName(
            Path.GetDirectoryName(Application.dataPath)), "\\data\\outputs\\");
        string output_file_path = output_file_directory + output_file_name;
        print("Loading output file at " + output_file_path);
        string json_text = File.ReadAllText(output_file_path);
        SensemakerData sensemaker_data = JsonConvert.DeserializeObject<SensemakerData>(
            json_text, new SensemakerDataConverter());
    }

    // Update is called once per frame
    void Update()
    {
        
    }
}