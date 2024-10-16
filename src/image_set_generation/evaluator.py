from timeit import default_timer as timer
import os
import pickle
import json

from parameters import ParameterSet
from sensemaker import SenseMaker
from hypothesis.hypothesis_evaluator import (SolutionSet, Solution)
from hypothesis.hypothesis import (CausalSequenceHyp, SameObjectHyp)

from image_set_generation.image_set_generator import ImageSetGenerator
from image_set_generation.data_handler import DataHandler

class TableData1():
    '''
    The data for table 1 for a single condition.
    Equal to the data for a single row of table 1. 
    '''
    # The parameter set associated with this condition.
    # Column 1
    parameter_set: ParameterSet
    # How many image sets have been processed total.
    image_set_counter: int
    # The average number of images in each plot generated under this condition.
    # If the plot connected none of the images, it counts as having 0 images
    # in the plot. 
    # Column 2
    average_images_in_plot: float
    # Divide the total number of images that have been connected into plots by
    # the total number of image sets that have been parsed to get the average.
    _total_images_in_plots: int

    # Count how many stories had all 3 images connected in the plot
    number_of_3_image_plots: int
    # Count how many stories only had 2 images connected in the plot.
    number_of_2_image_plots: int
    # Count how many stories had no images connected together in the plot
    number_of_0_image_plots: int

    # Count how many image sets did not have any plot connecting them.
    _total_plotless_count: int

    # For each pair of images connected through the plot, how many best-scoring
    # causal sequence hypotheses are there on average.
    # Column 3
    average_hyps_per_plot_segment: float
    # Count the total number of such hypotheses.
    _total_hyp_count: int
    # Count the total number of plot segments there are.
    _total_plot_segment_count: int

    # Keep track of the unique action labels in each plot.
    # Column 4 (once counted)
    unique_plot_actions: set[str]

    # Keep track of the unique object labels in each plot.
    # Column 5 (once counted)
    unique_recurring_objects: set[str]
    # Count the number of times each unique recurring object appeared in
    # a plot.
    # Keyed by the label of the object.
    objects_counts: dict[str, int]

    # Keep track of the number of unique action labels that have at least
    # one piece of causal path evidence in a plot.
    # This shows us the coverage of ConceptNet over actions in plots.
    # Column 6 (once counted)
    unique_plot_actions_with_causal_links: set[str]

    def __init__(self, parameter_set: ParameterSet):
        self.parameter_set = parameter_set
        self.image_set_counter = 0
        self.average_images_in_plot = 0
        self._total_images_in_plots = 0

        self.number_of_3_image_plots = 0
        self.number_of_2_image_plots = 0
        self.number_of_0_image_plots = 0

        self._total_plotless_count = 0
        self.average_hyps_per_plot_segment = 0
        self._total_hyp_count = 0
        self._total_plot_segment_count = 0
        self.unique_plot_actions = set()
        self.unique_recurring_objects = set()
        self.unique_plot_actions_with_causal_links = set()
        self.objects_counts = dict()
    # end __init__

    # Parse an image set's results.
    def parse_results(self, image_set: list[int],
                      plot: dict[int, list[CausalSequenceHyp]], 
                      recurring_objects: dict[int, list[SameObjectHyp]]):
        '''
        Parse a plot and set of recurring objects into the statistics for this
        table data's parameter set condition. 
        '''
        # Count this image set.
        self.image_set_counter += 1

        # 1. Count the number of images connected in the plot.
        # Count how many segment the plot has. If it has 1 or more, the
        # number of connected images is that plus 1. 
        plot_segment_count = 0
        plot_image_count = 0
        if (len(plot[0]) > 0):
            plot_segment_count += 1
        if (len(plot[1]) > 0):
            plot_segment_count += 1
        # Add to the total number of plot segments.
        self._total_plot_segment_count += plot_segment_count
        if plot_segment_count > 0:
            plot_image_count = plot_segment_count + 1
            if plot_image_count == 2:
                self.number_of_2_image_plots += 1
            elif plot_image_count == 3:
                self.number_of_3_image_plots += 1
        else:
            # If there were no plot segments, it's because this image set did not
            # have a plot.
            # Add it to the total count of image sets without plots.
            self._total_plotless_count += 1
            self.number_of_0_image_plots += 1
        # end else
        # Add the total number of images connected by the plot to the total.
        self._total_images_in_plots += plot_image_count
        # Calculate the average.
        self.average_images_in_plot = self._total_images_in_plots / self.image_set_counter

        # 2. Count the number of hypotheses for each plot segment. 
        # Only counts for those segments that have at least one hypothesis. 
        plot_hyp_count = 0
        if (len(plot[0]) > 0):
            plot_hyp_count += len(plot[0])
        if (len(plot[1]) > 0):
            plot_hyp_count += len(plot[1])
        # Add to the total number of hypotheses in this plot.
        self._total_hyp_count += plot_hyp_count
        # To get the average number of hypotheses per plot segment, divide by
        # the total number of segments.
        if self._total_plot_segment_count > 0:
            self.average_hyps_per_plot_segment = self._total_hyp_count / self._total_plot_segment_count

        # 3. Add to the set of unique actions (by label) in all plots.
        # 5. Add to the set of unique actions (by label) in all plots that have
        # causal link coverage in ConceptNet. 
        for index, cs_hyps in plot.items():
            for cs_hyp in cs_hyps:
                # Look at the label of the source and target actions.
                # If either is not in the set of unique actions, add it.
                if not cs_hyp.source_action.label in self.unique_plot_actions:
                    self.unique_plot_actions.add(cs_hyp.source_action.label)
                if not cs_hyp.target_action.label in self.unique_plot_actions:
                    self.unique_plot_actions.add(cs_hyp.target_action.label)
                # If this cs hyp has any causal path evidence, then concept net
                # had causal coverage for its source and target actions.
                # Add them to the set of unique actions with concept net coverage.
                if len(cs_hyp.causal_path_evs) > 0 or len(cs_hyp.multi_causal_path_evs) > 0:
                    if not cs_hyp.source_action.label in self.unique_plot_actions_with_causal_links:
                        self.unique_plot_actions_with_causal_links.add(cs_hyp.source_action.label)
                    if not cs_hyp.target_action.label in self.unique_plot_actions_with_causal_links:
                        self.unique_plot_actions_with_causal_links.add(cs_hyp.target_action.label)
            # end for
        # end for

        # 4. Add to the set of unique recurring objects (by label).
        for index, so_hyps in recurring_objects.items():
            for so_hyp in so_hyps:
                # Look at the label of object 1.
                # If it is not in the set of unique recurring objects, add it.
                if not so_hyp.object_1.label in self.unique_recurring_objects:
                    self.unique_recurring_objects.add(so_hyp.object_1.label)
                    # Start counting it as well.
                    self.objects_counts[so_hyp.object_1.label] = 0
                # end if
                self.objects_counts[so_hyp.object_1.label] += 1
            # end for
        # end for

    # end parse_results

    def get_results(self):
        '''
        Returns the results for this condition as a dictionary, with each result
        keyed by the name of its column in the table.
        '''
        result_dict = {}
        result_dict['Average Number of Images Included in Plot'] = self.average_images_in_plot
        result_dict['Number of 3 Image Plots'] = self.number_of_3_image_plots
        result_dict['Number of 2 Image Plots'] = self.number_of_2_image_plots
        result_dict['Number of 0 Image Plots'] = self.number_of_0_image_plots
        result_dict['Average Number of Highest-Scoring Action Sequences per Plot Segment'] = self.average_hyps_per_plot_segment
        result_dict['Number of Unique Actions in All Plots'] = len(self.unique_plot_actions)
        result_dict['Number of Unique Actions with ConceptNet Causal Link Coverage in All Plots'] = len(self.unique_plot_actions_with_causal_links)
        result_dict['Number of Unique Recurring Objects in All Plots'] = len(self.unique_recurring_objects)
        return result_dict
    # end get_results
# end TableData1

class Evaluator():
    '''
    Runs the sensemaker and performs larger scale evaluation. 
    '''

    def __init__(self):
        print('Initializing evaluator.')
    # end __init__

    def evaluate(self):
        '''
        Run the sensemaker on a set of image sets, then count all the things 
        that I want to check in my evaluation.
        '''
        image_sets = self.get_image_sets()

        # For each image set, run the sensemaker.
        # Make the sensemaker and load the parameters. 
        sensemaker = SenseMaker()
        # Parameters
        parameter_sets: list[ParameterSet] = list()
        # Read the parameter sets from data/inputs/parameter_sets/default_parameter_sets.json.
        pset_file_path = 'data/inputs/parameter_sets/default_parameter_sets.json'
        pset_dict = dict()
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
                pset_dict[pset_data['id']] = pset
            # end for
        # end with

        # What we're counting:
        # 1. Average # of images with a causal link to a sequential image. 
        # 2. Average # of highest-scoring causal links pair of sequential images with
        #   at least one causal link.
        # 3. Total number of unique actions involved in at least one plot.
        # 4. Total number of unique recurring objects.
        # 5. Total number of unique actions involved in at least one plot with
        #   causal path evidence in the plot. This checks the coverage of
        #   ConceptNet for the actions in the system's generated plots.
        # 6. For each emotional arc, how many plots had different actions from the
        #   baseline's plot. 

        # Keep table data for each condition, by parameter set id.
        table_data: dict[int, TableData1] = dict()
        # For each emotional arc, also compare their plots against the baseline
        # plot and see if they differ. Count how many times the plot differs
        # from the baseline.
        different_actions_counts: dict[int, int] = dict()
        for pset_id, pset in pset_dict.items():
            table_data[pset_id] = TableData1(pset)
            if pset_id > 4:
                different_actions_counts[pset_id] = 0
        # end for


        image_set_counter = 0
        image_set_limit = 501
        start_timer = timer()
        for image_ids in image_sets:
            image_set_counter += 1
            knowledge_graph, hypotheses, all_solutions = sensemaker.perform_sensemaking(
                parameter_sets=parameter_sets, image_ids=image_ids,
                write_json=False)
            # all_solutions is a dict of lists of SolutionSets, keyed by the
            # id of the parameter set that resulted in the solution. 
            image_id_1 = image_ids[0]
            image_id_2 = image_ids[1]
            image_id_3 = image_ids[2]

            # The emotional arcs baseline is id 4.
            # We want to compare each emotional arc's plot action against the
            # baseline's plot actions and see if they actually differ. 
            emotional_arc_baseline_plot = list()
            
            # Count things one parameter set at a time.
            # Look only at the first solution per parameter set.
            for pset_id, pset in pset_dict.items():
                solution_set = all_solutions[pset_id]
                solution = solution_set.solutions[0]
                # Get the plot.
                # Index 0 is the cs hyps between the first and second image.
                # Index 1 is the cs hyps between the second and third images.
                plot = self.get_plot(solution_set)
                
                # Check for outliers.
                # If a plot has 20 or more action sequences in a single segment,
                # the story may be an outlier. 
                
                if len(plot[0]) > 20 or len(plot[1]) > 20:
                    index_out = 0
                    num_sequences = 0
                    num_sequences_2 = 0
                    if len(plot[0]) > 20 and len(plot[1]) > 20:
                        index_out = 2
                        num_sequences = len(plot[0])
                        num_sequences_2 = len(plot[1])
                    elif len(plot[0]) > 20:
                        index_out = 0
                        num_sequences = len(plot[0])
                    elif len(plot[1]) > 20:
                        index_out = 1
                        num_sequences = len(plot[1])
                    
                    # Write the image sequence out to a file called
                    # 'outliers.txt' in the data directory.
                    text = (f'Sequence {image_set_counter} pset {pset_id} segment {index_out}. '
                            + f'Image ids {image_id_1} {image_id_2} {image_id_3}. '
                            + f' Number of action sequences: {num_sequences}.')
                    if num_sequences_2 > 0:
                        text += f' For second segment: {num_sequences_2}'
                    text += f'\n'
                    with open('data/outliers.txt', 'a+') as f:
                        f.write(text)
                    
                    # Get the outlier's equally high scoring actions.
                    if len(plot[1]) > 100:
                        outlier_text = 'Highest scoring action sequences for segment 1:'
                        for cs_hyp in plot[1]:
                            # Get its score.
                            hyp_score = 0
                            # Individual score.
                            individual_score = solution_set.individual_scores[cs_hyp.id]
                            # Paired scores with every same-object hypothesis to get
                            # all continuity evidence scores.
                            paired_scores = 0
                            # Check the hypothesis' continuity evidence for accepted
                            # same-object hyps, then get their paired scores.
                            for ev in cs_hyp.continuity_evs:
                                if ev.joining_hyp.id in solution.accepted_hypotheses:
                                    id_pair = frozenset([cs_hyp.id, ev.joining_hyp.id])
                                    if id_pair in solution_set.paired_scores:
                                        paired_scores += solution_set.paired_scores[id_pair]
                                # end if
                            # end for

                            hyp_score = individual_score + paired_scores
                            outlier_text += (f'\n{cs_hyp.source_action.label}->{cs_hyp.target_action.label} ({hyp_score})')
                        # end for
                        with open('data/200_action_outlier.txt', 'a+') as f:
                            f.write(outlier_text)
                    # end if
                # end if

                # Get the recurring objects.
                recurring_objects = self.get_recurring_objects(solution_set,
                                                               plot)
                # Parse them into the table data.
                table_data[pset_id].parse_results(image_ids,
                                                  plot,
                                                  recurring_objects)
                # Save the emotional arc baseline's plot.
                if pset_id == 4:
                    emotional_arc_baseline_plot = plot
                # For any emotional arc parameter set, compare its plot
                # against the baseline's plot and see if any actions differ.
                if pset_id > 4:
                    if self.plots_differ(emotional_arc_baseline_plot, plot):
                        different_actions_counts[pset_id] += 1
                # end if
            # end for

            if image_set_counter % 10 == 1:
                elapsed_time = timer() - start_timer
                print(f'Image set {image_set_counter}/{len(image_sets)}. '
                      + f'Elapsed time: {elapsed_time}s.')
                #break
            if image_set_counter >= image_set_limit:
                break
        # end for

        results_dicts_per_pset = dict()
        for pset_id, row_data in table_data.items():
            results_dict = row_data.get_results()
            if pset_id > 4:
                results_dict['Number of Plots with Different Actions From Baseline'] = different_actions_counts[pset_id]
            # For medium suspension of disbelief, look at the unique objects.
            if pset_id == 2:
                unique_objects_text = ''
                for obj_ in row_data.unique_recurring_objects:
                    unique_objects_text += (f'{obj_} ({row_data.objects_counts[obj_]}), ')
                unique_objects_text = unique_objects_text.rstrip()
                unique_objects_text = unique_objects_text.rstrip(',')
                results_dict['Unique Objects'] = unique_objects_text
            print(f'\n=====')
            print(f'Condition {pset_dict[pset_id].name}: ')
            for column_name, value in results_dict.items():
                print(f' {column_name}: {value}')
            # end for
            print(f'=====\n')
            results_dicts_per_pset[pset_id] = results_dict
        # end for

        print("done :)")
        return results_dicts_per_pset
    # end evaluate

    def get_plot(self, solution_set: SolutionSet) -> dict[int, list[CausalSequenceHyp]]:
        '''
        Gets the plot for a solution set by getting the highest scoring causal
        sequence hypotheses for each adjacent image.
        '''
        solution = solution_set.solutions[0]
        # Get the highest scoring accepted causal sequence hypotheses
        # between each pair of sequential images.
        highest_scores = dict()
        # Between the first and second images.
        highest_scores[0] = -1000000000000
        # Between the second and third images.
        highest_scores[1] = -1000000000000
        # Store the plot hyps as lists indexed by the first image in
        # the pair.
        plot_hyps: dict[int, list[CausalSequenceHyp]] = dict()
        # Between the first and second images
        plot_hyps[0] = list()
        # Between the second and third images
        plot_hyps[1] = list()

        # Go through each accepted causal sequence hypothesis.
        for hyp_id, hyp in solution.accepted_hypotheses.items():
            if not isinstance(hyp, CausalSequenceHyp):
                continue
            cs_hyp: CausalSequenceHyp = hyp
            # Get the indices of the two images this causal sequence hyp
            # is between.
            source_image = cs_hyp.source_action.get_image()
            target_image = cs_hyp.target_action.get_image()
            index_1 = source_image.index
            index_2 = target_image.index
            # If the images aren't adjacent, skip this hypothesis.
            if (not abs(index_2 - index_1) == 1):
                continue

            # Get its score.
            hyp_score = 0
            # Individual score.
            individual_score = solution_set.individual_scores[hyp_id]
            # Paired scores with every same-object hypothesis to get
            # all continuity evidence scores.
            paired_scores = 0
            # Check the hypothesis' continuity evidence for accepted
            # same-object hyps, then get their paired scores.
            for ev in cs_hyp.continuity_evs:
                if ev.joining_hyp.id in solution.accepted_hypotheses:
                    id_pair = frozenset([hyp_id, ev.joining_hyp.id])
                    if id_pair in solution_set.paired_scores:
                        paired_scores += solution_set.paired_scores[id_pair]
                # end if
            # end for

            hyp_score = individual_score + paired_scores

            # Compare it to the highest score.
            # If it's equal to the highest score, add it to the list.
            if hyp_score == highest_scores[index_1]:
                plot_hyps[index_1].append(hyp)
            # If it's greater than the highest score, make a new list with
            # this hypothesis in it.
            elif hyp_score > highest_scores[index_1]:
                plot_hyps[index_1] = list()
                plot_hyps[index_1].append(hyp)
                highest_scores[index_1] = hyp_score
            # end elif
        # end for
        return plot_hyps
    # end get_plot

    def get_recurring_objects(self, solution_set: SolutionSet,
                              plot: dict[int, list[CausalSequenceHyp]]) -> dict[int, list[SameObjectHyp]]:
        '''
        Gets the recurring objects between each pair of adjacent images in the form
        of lists of same object hypotheses. 

        Only counts those recurring objects that are also involved in the plot.
        '''
        solution = solution_set.solutions[0]

        recurring_objects: dict[int, list[CausalSequenceHyp]] = dict()
        # Between the first and second images
        recurring_objects[0] = list()
        # Between the second and third images
        recurring_objects[1] = list()

        # Go through each plot action.
        # See if they have any continuity evidence.
        # If the joining hyp for that continuity evidence was accepted, add it
        # to the list of recurring objects.
        for index, cs_hyps in plot.items():
            for cs_hyp in cs_hyps:
                for ev in cs_hyp.continuity_evs:
                    if ev.joining_hyp.id in solution.accepted_hypotheses:
                        if ev.joining_hyp not in recurring_objects[index]:
                            recurring_objects[index].append(ev.joining_hyp)
                        # end if
                    # end if
                # end for
            # end for
        # end for

        '''
        # Go through each accepted same object hypothesis.
        for hyp_id, hyp in solution.accepted_hypotheses.items():
            if not isinstance(hyp, SameObjectHyp):
                continue
            so_hyp: SameObjectHyp = hyp
            # Get the indices of the two images this same object hyp
            # is between.
            image_1 = so_hyp.object_1.get_image()
            image_2 = so_hyp.object_2.get_image()
            index_1 = min(image_1.index, image_2.index)
            index_2 = max(image_1.index, image_2.index)
            # If the images aren't adjacent, skip this hypothesis.
            if (not abs(index_2 - index_1) == 1):
                continue
            recurring_objects[index_1].append(so_hyp)
        # end for
        '''

        return recurring_objects
    # end get_recurring_objects

    def get_image_sets(self) -> list[list[int]]:
        '''
        Loads or makes the image sets for the evaluation.
        '''
        # First, try to load the evaluation image sets from pickle file.
        image_sets_file_name = 'eval_image_sets.pickle'
        data_directory = 'C:/Users/zevsm/Documents/GitHub/VisualNarrativeSensemaker/data/'
        image_sets_file_path = data_directory + image_sets_file_name
        image_sets = list()
        # Check if the file exists before trying to read it.
        if os.path.exists(image_sets_file_path):
            image_sets = pickle.load(open(image_sets_file_path, 'rb'))
            if len(image_sets) > 0:
                return image_sets
        # end if
        # If the file did not exist or is empty, the image sets have to be made.
        images_directory = 'C:/Users/zevsm/Documents/GitHub/VisualNarrativeSensemaker/data/inputs/images'
        annotations_directory = 'C:/Users/zevsm/Documents/GitHub/VisualNarrativeSensemaker/data/inputs/scene_graphs'
        image_set_generator = ImageSetGenerator(annotations_directory=annotations_directory,
                                                images_directory=images_directory,
                                                load_caches=True)
        image_set_gen_start = timer()
        image_sets = image_set_generator.generate_object_linked_image_sets(500)
        print(f'Image sets generated. Elapsed time: {timer() - image_set_gen_start}s.')
        # Cache the image sets.
        with open(image_sets_file_path, 'wb') as output_file:
            pickle.dump(image_sets, output_file)
        return image_sets
    # end get_image_sets

    def plots_differ(self, plot_1: dict[int, list[CausalSequenceHyp]], 
                     plot_2: dict[int, list[CausalSequenceHyp]]):
        '''
        Compares two plots and determines if their actions differ.
        Returns True if they do differ, False if they do not.
        '''
        for index, cs_hyps in plot_1.items():
            # If one plot links two images that the other doesn't, the plots
            # differ.
            if not index in plot_2:
                return True
            # Gather all unique source and target actions, by id, for plot 1.
            source_action_ids_1 = {cs_hyp.source_action.id 
                                   for cs_hyp in cs_hyps}
            target_action_ids_1 = {cs_hyp.target_action.id 
                                   for cs_hyp in cs_hyps}

            # Gather all unique source and target actions, by id, for plot 2.
            source_action_ids_2 = {cs_hyp.source_action.id 
                                   for cs_hyp in plot_2[index]}
            target_action_ids_2 = {cs_hyp.target_action.id 
                                   for cs_hyp in plot_2[index]}

            # If either of their symmetric differences are non-zero, that means
            # there is an action in one set that is not in the other set.
            if len(source_action_ids_1.symmetric_difference(source_action_ids_2)) > 0:
                return True
            if len(target_action_ids_1.symmetric_difference(target_action_ids_2)) > 0:
                return True
        # end for

        return False
    # end plots_differ
# end class Evaluator