using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

public class GUIController : MonoBehaviour
{
    // The main controller.
    private Main main;

    // UI Elements from the editor.
    public Canvas ui_canvas;

    // UI Elements fetched programmatically.
    // NOTE: The Panel UI element is actually a game object with a rect
    // transform and an Image component.
    private GameObject control_panel;
    private Toggle hypothesized_toggle;

    private string info_text = "";

    void Start()
    {
        this.info_text = "";
        this.main = this.gameObject.GetComponent<Main>();

        // Get the UI elements and assign listener functions.
        // The control panel.
        control_panel = ui_canvas.gameObject.transform.Find("ControlPanel").gameObject;
        // The control panel's toggles.
        hypothesized_toggle = control_panel.transform.Find("HypothesizedToggle").gameObject.GetComponent<Toggle>();
        hypothesized_toggle.onValueChanged.AddListener(delegate { HypothesizedToggleChanged(hypothesized_toggle); });
    }

    // Set the text shown in the info box.
    public void SetInfoText(string text)
    {
        this.info_text = text;
    }

    // Add text to the info box's text.
    public void AddInfoText(string text)
    {
        this.info_text += "/n" + text;
    }

    void OnGUI()
    {
        // Make a general info box on the bottom of the screen. 
        GUI.Box(new Rect(10, Screen.height - 250, Screen.width - 10, 250), this.info_text);
    }

    // Listeners for UI elements.
    void HypothesizedToggleChanged(Toggle toggle)
    {
        this.SetInfoText("Hypothesized toggle is currently " + toggle.isOn.ToString());
        // If the toggle is set to On, tell the main controller to enable all hypothesized elements.
        // Otherwise, tell the main controller to disable all hypothesized elements.
        if (toggle.isOn)
        {
            this.main.EnableHypothesized();
        }
        else if (!toggle.isOn)
        {
            this.main.DisableHypothesized();
        }
    }
}//end class GUIController