from timeit import default_timer as timer
import json
import random
import sys
import os

import cv2

from nltk.corpus import wordnet as wn

import constants as const
from constants import ConceptType
from parameters import ParameterSet

from knowledge_graph.graph import KnowledgeGraph
from knowledge_graph.items import (Node, Concept, Instance, Object, Action)

from commonsense.cskg_querier import CommonSenseQuerier, CSKGQuerier
from commonsense.commonsense_data import Synset

from input_handling.scene_graph_reader import SceneGraphReader
from output_handling.sensemaking_data_encoder import SensemakingDataEncoder

from hypothesis.hypothesis_generation import HypothesisGenerator
from hypothesis.hypothesis_evaluator import HypothesisEvaluator, Solution
from hypothesis.hypothesis import (Hypothesis, ConceptEdgeHyp, 
                                   SameObjectHyp, 
                                   NewObjectHyp)

class SenseMaker:
    """
    A class to handle the program's overall sensemaking procedure.
    """


    def __init__(self):
        #print("Initializing SenseMaker")
        sys.setrecursionlimit(10000)

        # Seed the RNG to get the same results.
        random.seed(5)

        # Make the commonsense querier.
        self._commonsense_querier = CSKGQuerier()
    # end __init__

    def perform_sensemaking(self, parameter_sets: list[ParameterSet], 
                            image_ids: list[int]):
        """
        Performs the overall sensemaking procedure.

        Specific parts of the procedure are done in other classes and
        functions.

        Parameters
        ----------
        parameter_sets : list[ParameterSet]
            The sets of sensemaking parameters that will be used for this
            sensemaking procedure. Each ParameterSet in the list will result
            in a separate hypothesis evaluation run. 
        image_ids : int
            An ordered list of image ids to perform sensemaking over. Each id
            corresponds to the name of an image in the Visual Genome dataset. 

        Returns
        -------
        None
        """
        timers = dict()
        timers['start'] = timer()
        print("Performing sensemaking")
        # Get our observations from the environment.
        # Read in the scene graph files for the set and make a knowledge graph 
        # out of them.
        timers['sg_start'] = timer()
        print(f'Reading scene graphs...')
        scene_graph_reader = SceneGraphReader(self._commonsense_querier)
        knowledge_graph = scene_graph_reader.read_scene_graphs(image_ids)
        print(f'Done reading scene graphs.' +
              f' Time taken: {timer() - timers["sg_start"]}')
        
        timers['h_gen_start'] = timer()
        print(f'Generating hypotheses...')
        hypothesis_generator = HypothesisGenerator(self._commonsense_querier)
        hypotheses = hypothesis_generator.generate_hypotheses(knowledge_graph)
        print(f'Done generating hypotheses.' + 
              f' Time taken: {timer() - timers["h_gen_start"]}')

        timers['h_eval_start'] = timer()
        print(f'Evaluating hypotheses...')
        all_solutions = self._evaluate_hypotheses(
            knowledge_graph=knowledge_graph,
            hypotheses=hypotheses,
            parameter_sets={p_set.id: p_set for p_set in parameter_sets})
        print(f'Done evaluating hypotheses.' + 
              f' Time taken: {timer() - timers["h_eval_start"]}')
        
        print(f'Writing output to json...')
        self._write_output_json(knowledge_graph=knowledge_graph,
                                hypotheses=hypotheses,
                                parameter_sets={p_set.id: p_set 
                                                for p_set in parameter_sets},
                                solutions=all_solutions)

        print(f'Done performing sensemaking :) ' + 
              f'elapsed time: {timer() - timers["start"]}')

        return knowledge_graph, hypotheses
    # end perform_sensemaking

    def _evaluate_hypotheses(self, knowledge_graph: KnowledgeGraph,
                             hypotheses: dict[int, Hypothesis],
                             parameter_sets: dict[int, ParameterSet]):
        """
        Perform hypothesis evaluation on a set of Hypotheses using each of a
        set of different parameter sets.

        The hypotheses and parameter set inputs to this function should both be
        dictionaries keyed by their respective members' ids.

        Outputs a dictionary of lists of solutions, with each list keyed to
        the id of the parameter set used to make those solutions.
        """
        # Each solution should have
        #   'parameter_set'
        #   'hypothesis_sets'
        #   'energies'
        all_solutions = dict()
        for parameter_id, parameters in parameter_sets.items():
            hypothesis_evaluator = HypothesisEvaluator(parameters=parameters)
            solutions = hypothesis_evaluator.evaluate_hypotheses(
                knowledge_graph=knowledge_graph,
                hypotheses=hypotheses)
            all_solutions[parameter_id] = solutions
        # end for
        return all_solutions
    # end _evaluate_hypotheses

    def _write_output_json(self, knowledge_graph: KnowledgeGraph, 
                           hypotheses: dict[int, Hypothesis],
                           parameter_sets: dict[int, ParameterSet],
                           solutions: dict[int, list[Solution]]):
        """
        Write the solution sets for a series of sensemaking runs to an output
        json file.

        Parameters
        ----------
        knowledge_graph : KnowledgeGraph
            The sensemaker's knowledge graph.
        hypotheses : dict[int, Hypothesis]
            A dictionary of all of the sensemaker's hypotheses, keyed by
            hypothesis id.
        parameter_sets : dict[int, ParameterSet]
            A dictionary of the parameter sets used to evaluate hypotheses,
            keyed by parameter set id.
        solutions : dict[int, list[Solution]]
            A dictionary of all of the solutions from hypothesis evaluation,
            keyed by the id of the parameter set used to create them.
        """
        # Add hypothetical objects to the knowledge graph before encoding.
        objects_hs = [h for h in hypotheses.values() 
                       if type(h) == NewObjectHyp]
        for h in objects_hs:
            knowledge_graph.add_node(h.obj)
        # end for
        output_dict = {'sensemaker_data': {'knowledge_graph': knowledge_graph,
                       'hypotheses': list(hypotheses.values()),
                       'parameter_sets': list(parameter_sets.values()),
                       'solutions': list(solutions.values())}}
        json_data = json.dumps(output_dict, cls=SensemakingDataEncoder)
        json_obj = json.loads(json_data)
        # Make the output file name by concatenating the images' ids and
        # separating them by underscores.
        output_file_name = "output"
        for image in knowledge_graph.images.values():
            output_file_name += (f'_{image.id}')
        output_file_directory = (f'{const.OUTPUT_DIRECTORY}')
        output_file_path = (f'{output_file_directory}/{output_file_name}.json')
        # Write the json data to file.
        # Check if the directory we're making this file in exists.
        # If not, create it.
        if not os.path.exists(output_file_directory):
            os.makedirs(output_file_directory)
        # Creates or overwrite any existing file with this name.
        with open(output_file_path, 'w') as output_file:
            json.dump(json_obj, output_file, indent=2)
    # end _write_output_json

    def _compare_hypothesis_sets(self, hypotheses_1: dict[int, Hypothesis], 
                                 hypotheses_2: dict[int, Hypothesis]):
        """
        Compare two sets of hypotheses. 

        Retrns a dict of the hypotheses exclusive to the first set, a dict of 
        the hypotheses exclusive to the second set, and a dict of the ones 
        shared between both of them.
        """
        exclusives_1 = dict()
        exclusives_2 = dict()
        shared = dict()
        for id, hypothesis in hypotheses_1.items():
            if not id in hypotheses_2:
                exclusives_1[id] = hypothesis
            else:
                shared[id] = hypothesis
            # end else
        # end for
        for id, hypothesis in hypotheses_2.items():
            if not id in hypotheses_1:
                exclusives_2[id] = hypothesis
            else:
                shared[id] = hypothesis
            # end else
        # end for
        return exclusives_1, exclusives_2, shared
    # end _compare_hypothesis_sets

# end class Sensemaker