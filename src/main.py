import re

import nltk
import spacy

import os
import sys
import argparse
import json

from flask import Flask

from PySide6.QtWidgets import QApplication

from nltk.corpus import wordnet as wn

from output_handling.ui import MainUI

from parameters import ParameterSet

from sensemaker import SenseMaker

from commonsense.cskg_querier import CSKGQuerier

def initialize_ui():
    # Initialize the Qt application and UI
    qt_app = QApplication(sys.argv)
    qt_app.setOrganizationName("Me :)")
    qt_app.setApplicationName("Narrative Image Sensemaker")
    # Creates the main window
    main_window = MainUI()
    main_window.show()
    # Shuts down the app when the 'x' button is pressed
    # on the window. 
    sys.exit(qt_app.exec_())
    print(":)")
# end initialize_ui

def main():
    print ("hey :)")
    # Download wordnet.
    # Only need to do once per machine.
    #nltk.download('wordnet')
    #nltk.download('omw-1.4')
    #nltk.download('vader_lexicon')

    #initialize_ui()
    # The input should be a list of 3 integers, each one the ID of an image.
    # e.g.  [123, 6524564, 12321]
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('image_set_ids', type=int, nargs='+', 
                        help='The ids of the images in the image set you wish to parse.')
    args = parser.parse_args()
    image_set_ids = args.image_set_ids
    '''

    # Study 1 group 1
    #image_set_ids = [1000000002,1000000007,1000000009]
    # Study 1 group 2
    #image_set_ids = [1000000003, 1000000002, 1000000007]
    # Study 1 group 3
    #image_set_ids = [1000000001, 1000000003, 1000000009]
    # Study 1 group 4
    #image_set_ids = [1000000005, 1000000003, 1000000009]
    # Study 1 group 5
    #image_set_ids = [1000000007, 1000000006, 1000000001]
    # Study 1 group 6
    #image_set_ids = [1000000005, 1000000004, 1000000007]
    # Study 1 group 7
    #image_set_ids = [1000000001, 1000000006, 1000000007]
    # Study 1 group 8
    #image_set_ids = [1000000005, 1000000003, 1000000009]
    # Study 1 group 9
    #image_set_ids = [1000000008, 1000000002, 1000000001]
    # Study 1 group 10
    image_set_ids = [1000000003, 1000000002, 1000000007]
    # Study 1 group 11
    #image_set_ids = [1000000009, 1000000003, 1000000001]
    #image_set_ids = [13]
    # Can enter a test set number instead of 3 image ids.
    if len(image_set_ids) == 1 and image_set_ids[0] == 13:
        # Set 13 - kitchen, bike ride, picnic
        image_set_ids = [2402873, 2391830, 2406899]
    elif len(image_set_ids) == 1 and image_set_ids[0] == 14:
        # Set 14 - Field bike ride, bike stop, road bike ride (all with dogs)
        image_set_ids = [2384081, 2361867, 2329428]
    elif len(image_set_ids) == 1 and image_set_ids[0] == -1:
        image_set_ids = [225, 1324, 621]
    print(f'Image set ids: {image_set_ids}')

    # Script has to be called while current working directory is wherever 
    # VisualNarrativeSensemaker, the folder that contains data and src, is.
    cwd = os.getcwd()
    print(f'Current working directory: {cwd}')

    # Make a sensemaker and run sensemaking.
    sensemaker = SenseMaker()
    # Parameters
    parameter_sets = list()
    # Read the parameter sets from data/inputs/parameter_sets/default_parameter_sets.json.
    pset_file_path = 'data/inputs/parameter_sets/default_parameter_sets.json'
    with open(pset_file_path) as f:
        pset_file_data = json.load(f)
        for pset_data in pset_file_data['parameter_sets']:
            pset = ParameterSet(name=pset_data['name'],
                                visual_sim_ev_weight=pset_data['visual_sim_ev_weight'],
                                visual_sim_ev_thresh=pset_data['visual_sim_ev_thresh'],
                                attribute_sim_ev_weight=pset_data['attribute_sim_ev_weight'],
                                attribute_sim_ev_thresh=pset_data['attribute_sim_ev_thresh'],
                                causal_path_ev_weight=pset_data['causal_path_ev_weight'],
                                causal_path_ev_thresh=pset_data['causal_path_ev_thresh'],
                                continuity_ev_weight=pset_data['continuity_ev_weight'],
                                continuity_ev_thresh=pset_data['continuity_ev_thresh'],
                                density_weight=pset_data['density_weight'],
                                affect_curve=pset_data['affect_curve'],
                                affect_curve_weight=pset_data['affect_curve_weight'],
                                affect_curve_thresh=pset_data['affect_curve_thresh'])
            pset.set_id(pset_data['id'])
            parameter_sets.append(pset)
        # end for
    # end with

    #parameter_sets.append(pset_make_relationships)
    #parameter_sets.append(pset_choose_carefully)
    #parameter_sets = [pset_default, pset_high_cont, pset_no_cont]
    knowledge_graph, hypotheses = sensemaker.perform_sensemaking(
        parameter_sets=parameter_sets, image_ids=image_set_ids)

    print("done!")
# end main

# __name__ will be __main__ if we're running the program
# from this script. If another module calls this script,
# then __name__ is the name of the calling module. 
if __name__ == "__main__":    
    main()
