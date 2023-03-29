import re

import nltk
import spacy

import sys

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

    #initialize_ui()

    # Make a sensemaker and run sensemaking.
    sensemaker = SenseMaker()
    # Set 10
    image_ids = [2402873, 2391830, 2406899]
    # Parameters
    parameter_sets = list()
    pset_normal = ParameterSet(name='normal',
                               no_relationship_penalty=-1.0,
                               relationship_score_minimum=0.5,
                               relationship_score_weight=1.0,
                               continuity_penalty=-10.0)
    pset_make_relationships = ParameterSet(name='make-relationships',
                                           no_relationship_penalty=-10.0,
                                           relationship_score_minimum=0,
                                           relationship_score_weight=1.0,
                                           continuity_penalty=-10.0)
    pset_choose_carefully = ParameterSet(name='choose-carefully',
                                         no_relationship_penalty=0.0,
                                         relationship_score_minimum=1.0,
                                         relationship_score_weight=10.0,
                                         continuity_penalty=-10.0)
    parameter_sets.append(pset_make_relationships)
    parameter_sets.append(pset_choose_carefully)
    knowledge_graph, hypotheses = sensemaker.perform_sensemaking(
        parameter_sets=parameter_sets, image_ids=image_ids)

    print("done!")
# end main

# __name__ will be __main__ if we're running the program
# from this script. If another module calls this script,
# then __name__ is the name of the calling module. 
if __name__ == "__main__":    
    main()
