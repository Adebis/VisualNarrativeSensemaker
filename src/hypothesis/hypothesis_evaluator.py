from dataclasses import dataclass, field

import dwave_networkx as dnx
from neal.sampler import SimulatedAnnealingSampler

import constants as const
from parameters import ParameterSet
from knowledge_graph.graph import KnowledgeGraph
from knowledge_graph.items import (Instance, Edge)
from hypothesis.hypothesis import (Hypothesis, ConceptEdgeHypothesis, 
                                   ObjectDuplicateHypothesis, 
                                   OffscreenObjectHypothesis)

@dataclass
class Solution():
    """
    A single solution to the sensemaking MOP problem.

    Attributes:
    -----------
    id : int
        A unique integer identifier. 
    parameters : ParameterSet
        The parameter set used to create this solution.
    accepted_hypotheses : dict[int, Hypothesis]
        The hypotheses accepted in this solution.
    energy : float
        The energy value for this solution's accepted hypothesis set.
        Result of solving the MWIS problem. Lower energy means the hypothesis
        set is better.
    """

    id: int = field(init=False)
    parameters: ParameterSet
    accepted_hypotheses: dict[int, Hypothesis]
    energy: float

    _next_id = 0
    def __post_init__(self):
        # Assign the id, then increment the class ID counter so the next
        # Solution gets a unique id. 
        self.id = Solution._next_id
        Solution._next_id += 1
    # end __post_init__
# end class Solution

class HypothesisEvaluator():
    """
    Handles evaluating a knowledge graph and a set of hypotheses.

    Scores the hypotheses and applies constraints.

    Attributes:
    -----------
    parameters : ParameterSet
        A set of sensemaking parameters to use for hypothesis evaluations.
    """

    def __init__(self, parameters: ParameterSet):
        """
        Initializes with a set of sensemaking parameters.
        """
        print('Initializing hypothesis evaluator')
        self.parameters = parameters
    # end __init__

    def evaluate_hypotheses(self, knowledge_graph: KnowledgeGraph,
                 hypotheses: dict[int, Hypothesis]) -> list[Solution]:
        """
        Evaluate a knowledge graph and a set of hypotheses.

        Parameters
        ----------
        knowledge_graph : KnowledgeGraph
            The knowledge graph to be evaluated.
        hypotheses : dict[int, Hypothesis]
            The set of hypotheses to be evaluated with the knowledge graph. A
            dictionary of Hypothesis objects, keyed by their ids.

        Returns
        -------
        solutions : list[Solution]
            The solutions to the problem of which hypotheses to accept
            and which to reject.
        """
        # Predict the change in score from accepting each hypothesis.
        # For MWIS solving, need to get a predicted score for each hypothesis
        # itself and a predicted score for accepting that hypothesis with 
        # certain other hypotheses.
        # Key: hypothesis id. Value: predicted score for accepting that 
        # hypothesis.
        individual_scores = dict()
        # Key: tuple of hypothesis IDs. Value: predicted score for accepting
        # both of those hypotheses together.
        paired_scores = dict()

        # Score all ConceptEdgeHypotheses
        i_scores, p_scores = self._predict_concept_edge_scores(
            hypotheses=hypotheses)
        individual_scores.update(i_scores)
        paired_scores.update(p_scores)

        # Score all ObjectDuplicateHypotheses
        i_scores, p_scores, id_triplets = self._predict_object_duplicate_scores(
            hypotheses=hypotheses,
            paired_scores=paired_scores)
        individual_scores.update(i_scores)
        paired_scores.update(p_scores)

        # Score all ObjectHypotheses
        i_scores, p_scores = self._predict_object_scores(
            knowledge_graph=knowledge_graph, hypotheses=hypotheses)
        individual_scores.update(i_scores)
        paired_scores.update(p_scores)
        print("Done scoring.")

        # Solve the maximum weight independent set problem consisting of these
        # hypotheses' ids and their predicted scores.
        solution_set_ids, energies_list = self._solve_mwis(
            individual_scores=individual_scores, paired_scores=paired_scores)
        
        print("Done solving MWIS")

        # Put together the solutions.
        solutions = list()
        for i in range(len(solution_set_ids)):
            set_ids = solution_set_ids[i]
            set_hypotheses = dict()
            for set_id in set_ids:
                if set_id in hypotheses:
                    set_hypotheses[set_id] = hypotheses[set_id]
                # If this id is for a triplet representing three hypotheses, 
                # find out what those three hypotheses are and add them.
                elif set_id in id_triplets:
                    id_triplet = id_triplets[set_id]
                    for h_id in id_triplet:
                        set_hypotheses[h_id] = hypotheses[h_id]
                    # end for
                else:
                    print(f'HypothesisEvaluator.evaluate_hypotheses : id ' +
                          f'{set_id} not in hypotheses or triplets.')
                # end else
            # end for
            solution = Solution(parameters=self.parameters,
                                accepted_hypotheses=set_hypotheses,
                                energy=energies_list[i])
            solutions.append(solution)
        # end for

        return solutions
    # end evaluate_hypotheses

    def _predict_concept_edge_scores(self, hypotheses: dict[int, Hypothesis]):
        """
        Predicts scores for all of the ConceptEdgeHypotheses.

        Parameters
        ----------
        hypotheses : dict[int, Hypothesis]
            All of the Hypotheses, keyed by id.
        
        Returns
        -------
        individual_scores : dict[int, float]
            The individual scores for each ConceptEdgeHypothesis, keyed by
            hypothesis id.
        paired_scores : dict[tuple[int, int], float]
            The paired scores for accepting hypotheses together, keyed by
            pairs of hypothesis ids.
        """
        individual_scores = dict()
        paired_scores = dict()
        # Gather all the concept edge hypotheses.
        ce_hypotheses = [h for h in hypotheses.values() 
                         if type(h) == ConceptEdgeHypothesis]
        for hypothesis in ce_hypotheses:
            # The hypothesis' individual score is its evidence score, modified
            # by any parameters.
            score = hypothesis.score
            score -= self.parameters.relationship_score_minimum
            score *= self.parameters.relationship_score_weight
            # Accepting this hypothesis also avoids one no_relationship_penalty,
            # so subtract that here. 
            score -= self.parameters.no_relationship_penalty
            # Finally, take the average centrality between the two Instances the
            # hypothesis is between and multiply the score by it.
            score *= (hypothesis.source_instance.get_centrality() + 
                      hypothesis.target_instance.get_centrality()) / 2
            individual_scores[hypothesis.id] = score
            # If it's premised on any other Hypotheses, give its score a
            # large negative number and its paired score with an equally large
            # positive number to enforce the fact that the premise has to be
            # accepted to accept this Hypothesis.
            for premise in hypothesis.premises.values():
                individual_scores[hypothesis.id] -= const.H_SCORE_OFFSET
                id_tuple_1 = (hypothesis.id, premise.id)
                id_tuple_2 = (premise.id, hypothesis.id)
                paired_scores[id_tuple_1] = const.H_SCORE_OFFSET
                paired_scores[id_tuple_2] = const.H_SCORE_OFFSET
            # end for
        # end for
        return (individual_scores, paired_scores)
    # end _predict_concept_edge_scores

    def _predict_object_duplicate_scores(self, 
        hypotheses: dict[int, Hypothesis], 
        paired_scores: dict[tuple[int, int], float]):
        """
        Predict scores for all of the ObjectDuplicateHypotheses.
        
        Parameters
        ----------
        hypotheses : dict[int, Hypothesis]
            All of the Hypotheses, keyed by id.
        paired_scores : dict[tuple[int, int], float]
            Existing paired scores between hypotheses. Key is a pair of
            hypothesis ids. Value is the score between them.

        Returns
        -------
        individual_scores : dict[int, float]
            The individual scores for each ObjectDuplicateHypothesis, keyed by
            hypothesis id.
        new_paired_scores : dict[tuple[int, int], float]
            The paired scores for accepting hypotheses together, keyed by
            pairs of hypothesis ids.
        id_triplets : dict[int, tuple[int, int, int]]
            All of the triplets of ids for the transitive property triplets 
            found between ObjectDuplicateHypotheses, keyed by the ID they were 
            assigned.

            Their key ids match their id in the new_paired_scores dictionary,
            and are always negative.
        """
        individual_scores = dict()
        new_paired_scores = dict()
        # Get all the ObjectDuplicateHypotheses
        od_hypotheses = [h for h in hypotheses.values()
                         if type(h) == ObjectDuplicateHypothesis]
        for hypothesis in od_hypotheses:
            # Individual score is based on its similarity score, so its
            # evidence score should be fine.
            score = hypothesis.score
            # Accepting this hypothesis also gets rid of one no_continuity
            # penalty, so subtract that here.
            score -= self.parameters.continuity_penalty
            # Multiply the score by the average centrality between the two
            # Instances this hypothesis is between.
            score *= (hypothesis.object_1.get_centrality() + 
                      hypothesis.object_2.get_centrality()) / 2
            individual_scores[hypothesis.id] = score
            # If it's premised on any other Hypotheses, give its score a
            # large negative number and its paired score with the other 
            # Hypothesis an equally large positive number to enforce the fact 
            # that the premise has to be accepted to accept this Hypothesis.
            for premise in hypothesis.premises.values():
                individual_scores[hypothesis.id] -= const.H_SCORE_OFFSET
                id_pair_1 = (hypothesis.id, premise.id)
                id_pair_2 = (premise.id, hypothesis.id)
                new_paired_scores[id_pair_1] = const.H_SCORE_OFFSET
                new_paired_scores[id_pair_2] = const.H_SCORE_OFFSET
            # end for
        # end for
        # All ObjectDuplicateHypotheses should now have an individual score and
        # its paired scores with any of its premise hypotheses.
        # Find all of the ObjectDuplicateHypothesis pairs that contradict one
        # another.
        id_pairs = self._find_contradicting_duplicate_pairs(
            hypotheses=hypotheses)
        # For each pair, set their paired score to a large negative number to
        # enforce the fact that they should never be accepted together.
        for id_pair in id_pairs:
            new_paired_scores[id_pair] = -const.H_SCORE_OFFSET
            # Get the inverse too.
            new_paired_scores[(id_pair[0], id_pair[1])] = -const.H_SCORE_OFFSET
        # Find all of the transitive property triplets.
        id_triplets_list = self._find_transitive_property_triplets(
            hypotheses=hypotheses)
        # Store the triplets in a dictionary and key them. 
        id_triplets = dict()
        triplet_counter = 1
        for id_triplet in id_triplets_list:
            # Make sure their ids are all negative.
            id_triplets[-triplet_counter] = id_triplet
            triplet_counter += 1
        # end for
        paired_scores_to_add = dict()
        for triplet_id, triplet in id_triplets.items():
            # Have the triplet itself adopt all of the paired scores of its
            # member hypotheses.
            # Between each hypothesis if a triplet, give their paired scores a
            # large negative number.
            # Between the id of the triplet itself and each hypothesis, give 
            # their paired scores a large negative number. 
            # This way, either all of them are accepted or exactly one of them 
            # are accepted.
            for h_id in triplet:
                # Have the triplet adopt the paired scores of its members.
                for id_pair, paired_score in new_paired_scores.items():
                    other_id = -1
                    if h_id == id_pair[0]:
                        other_id = id_pair[1]
                    elif h_id == id_pair[1]:
                        other_id = id_pair[0]
                    else:
                        continue
                    new_id_pair_1 = (triplet_id, other_id)
                    new_id_pair_2 = (other_id, triplet_id)
                    paired_scores_to_add[new_id_pair_1] = paired_score
                    paired_scores_to_add[new_id_pair_2] = paired_score
                # end for
                # Place a large negative score between the triplet and its
                # members.
                new_id_pair_1 = (triplet_id, h_id)
                new_id_pair_2 = (h_id, triplet_id)
                paired_scores_to_add[new_id_pair_1] = -const.H_SCORE_OFFSET
                paired_scores_to_add[new_id_pair_2] = -const.H_SCORE_OFFSET
                # Place a large negative score between each member.
                for other_h_id in triplet:
                    if h_id == other_h_id:
                        continue
                    new_id_pair_1 = (other_h_id, h_id)
                    new_id_pair_2 = (h_id, other_h_id)
                    paired_scores_to_add[new_id_pair_1] = -const.H_SCORE_OFFSET
                    paired_scores_to_add[new_id_pair_2] = -const.H_SCORE_OFFSET
                # end for
            # end for
        # end for
        new_paired_scores.update(paired_scores_to_add)

        return (individual_scores, new_paired_scores, id_triplets)
    # end _predict_object_duplicate_scores

    def _find_contradicting_duplicate_pairs(self, 
                                            hypotheses: dict[int, Hypothesis]):
        """
        Finds all the pairs of ObjectDuplicateHypotheses that contradict with
        one another.

        Two ObjectDuplicateHypotheses contradict if they both assert that one
        Object is equal to two other Objects that are both in the same scene.

        Returns a list of hypothesis id pairs (without duplicates).
        """
        # Store the ids of all contradicting hypothesis pairs.
        id_pairs = list()
        # Get all the ObjectDuplicateHypotheses.
        od_hypotheses = [h for h in hypotheses.values()
                         if type(h) == ObjectDuplicateHypothesis]
        # Two ObjectDuplicateHypotheses contradict if they:
        #   1. Share an Object.
        #   2. Both have non-shared Objects that are in the same scene. 
        for hypothesis_1 in od_hypotheses:
            for hypothesis_2 in od_hypotheses:
                if hypothesis_1 == hypothesis_2:
                    continue
                # See if one of the Objects matches between hypothesis 1 and 2.
                # Then, hypothesis 1 has one non-matching Object and
                # hypothesis 2 has one non-matching Object.
                # Find the matching Object, hypothesis 1's non-matching Object,
                # and hypothesis 2's non-matching Object.
                matching_object = None
                non_matching_object_1 = None
                non_matching_object_2 = None
                if hypothesis_2.has_object(hypothesis_1.object_1):
                    matching_object = hypothesis_1.object_1
                    non_matching_object_1 = hypothesis_1.object_2
                    non_matching_object_2 = hypothesis_2.get_other_object(
                        matching_object)
                elif hypothesis_2.has_object(hypothesis_1.object_2):
                    matching_object = hypothesis_1.object_2
                    non_matching_object_1 = hypothesis_1.object_1
                    non_matching_object_2 = hypothesis_2.get_other_object(
                        matching_object)
                # end elif
                if matching_object is None:
                    continue
                # If the two non-matching Objects are both in the same scene,
                # this is a contradiction!
                if (non_matching_object_1.get_image() == 
                    non_matching_object_2.get_image()):
                    id_pair = (hypothesis_1.id, hypothesis_2.id)
                    # Add this pair if it doesn't already exist.
                    pair_exists = False
                    for existing_pair in id_pairs:
                        if self._equal_id_pairs(id_pair, existing_pair):
                            pair_exists = True
                            break
                        # end if
                    # end for
                    if not pair_exists:
                        id_pairs.append(id_pair)
                    # end if
                # end if
            # end for hypothesis_2
        # end for hypothesis_1
        return id_pairs
    # end _find_contradicting_duplicate_pairs

    def _find_transitive_property_triplets(self, 
                                           hypotheses: dict[int, Hypothesis]):
        """
        Finds all the transitive property triplets amongst the
        ObjectDuplicateHypotheses in the hypotheses passed in.

        Three ObjectDuplicateHypotheses form a triplet if the transitive
        property requires that they all be accepted if at least two of the are
        accepted.
        
        e.g. hypothesis_1: object_1->is->object_2, 
        hypothesis_2: object_1->is->object_3, 
        hypothesis_3: object_2->is->object_3.

        Returns a list of hypothesis id triplets (without duplicates).
        """
        # Store the transitive property triplets as triplets of hypothesis ids.
        id_triplets = list()
        # Get all the ObjectDuplicateHypotheses.
        od_hypotheses = [h for h in hypotheses.values()
                         if type(h) == ObjectDuplicateHypothesis]
        for hypothesis_1 in od_hypotheses:
            # Look for another hypothesis that leads to or from one of this
            # hypothesis' objects.
            for hypothesis_2 in od_hypotheses:
                if hypothesis_1 == hypothesis_2:
                    continue
                # See if one of the Objects matches between hypothesis 1 and 2.
                # Then, hypothesis 1 has one non-matching Object and
                # hypothesis 2 has one non-matching Object.
                # Find the matching Object, hypothesis 1's non-matching Object,
                # and hypothesis 2's non-matching Object.
                matching_object = None
                non_matching_object_1 = None
                non_matching_object_2 = None
                if hypothesis_2.has_object(hypothesis_1.object_1):
                    matching_object = hypothesis_1.object_1
                    non_matching_object_1 = hypothesis_1.object_2
                    non_matching_object_2 = hypothesis_2.get_other_object(
                        matching_object)
                elif hypothesis_2.has_object(hypothesis_1.object_2):
                    matching_object = hypothesis_1.object_2
                    non_matching_object_1 = hypothesis_1.object_1
                    non_matching_object_2 = hypothesis_2.get_other_object(
                        matching_object)
                # end elif
                if matching_object is None:
                    continue
                # end if
                # Look for a third hypothesis between the other two hypotheses'
                # non-matching objects.
                for hypothesis_3 in od_hypotheses:
                    if hypothesis_1 == hypothesis_3:
                        continue
                    elif hypothesis_2 == hypothesis_3:
                        continue
                    # end elif
                    if (hypothesis_3.has_object(non_matching_object_1) and
                        hypothesis_3.has_object(non_matching_object_2)):
                        # This is a transitive property triplet.
                        id_triplet = (hypothesis_1.id, hypothesis_2.id, 
                                      hypothesis_3.id)
                        # Don't add the triplet if it's already been founud.
                        triplet_exists = False
                        for existing_triplet in id_triplets:
                            if self._equal_id_triplets(id_triplet, 
                                                       existing_triplet):
                                triplet_exists = True
                                break
                            # end if
                        # end for
                        if not triplet_exists:
                            id_triplets.append(id_triplet)
                        # end if
                    # end if
                # end for hypothesis_3
            # end for hypothesis_2
        # end for hypothesis_1
        return id_triplets
    # end _find_transitive_property_triplets

    def _predict_object_scores(self, knowledge_graph: KnowledgeGraph, 
                                 hypotheses: dict[int, Hypothesis]):
        """
        Predicts scores for all of the ObjectHypotheses.

        Parameters
        ----------
        knowledge_graph : KnowledgeGraph
            The knowledge graph, to look at observed Instances.
        hypotheses : dict[int, Hypothesis]
            All of the Hypotheses, keyed by id.
        
        Returns
        -------
        individual_scores : dict[int, float]
            The individual scores for each OffscreenObjectHypothesis, keyed by
            hypothesis id.
        paired_scores : dict[tuple[int, int], float]
            The paired scores for accepting hypotheses together, keyed by
            pairs of hypothesis ids.
        """
        individual_scores = dict()
        paired_scores = dict()
        # Get all the ObjectHypotheses.
        obj_hypotheses = [h for h in hypotheses.values()
                        if type(h) == OffscreenObjectHypothesis]
        for hypothesis in obj_hypotheses:
            # Get the image for the scene this hypothesized Instance is in.
            image = hypothesis.obj.get_image()
            # Get all the observed Instances in the same scene.
            observed_instances = knowledge_graph.get_scene_instances(image)
            # Get all the ObjectHypotheses in the same scene that are
            # not this hypothesis.
            scene_obj_hypotheses = [h for h in obj_hypotheses
                                    if h.obj.get_image() == image and
                                    not h == hypothesis]
            # The base assumption is that the hypothesized Object has no
            # relationships with any other Instance in the scene. 
            # Add one no_relationship_penalty score to the hypothesis for every
            # Observed Instance in the scene.
            score = (len(observed_instances) * 
                     self.parameters.no_relationship_penalty)
            # Multiply the score by the hypothesized Object's centrality.
            centrality_factor = hypothesis.obj.get_centrality()
            score *= centrality_factor
            individual_scores[hypothesis.id] = score
            # Add a paired score for each hypothesized Obect in the same
            # scene equal to one no_relationship_penalty.
            for scene_obj_hypothesis in scene_obj_hypotheses:
                score = self.parameters.no_relationship_penalty
                score *= centrality_factor
                id_pair_1 = (hypothesis.id, scene_obj_hypothesis.id)
                id_pair_2 = (scene_obj_hypothesis.id, hypothesis.id)
                paired_scores[id_pair_1] = score
                paired_scores[id_pair_2] = score
            # end for scene_obj_hypothesis
            # Go through all of this hypothesis' ConceptEdgeHypotheses.
            for ce_hypothesis in hypothesis.concept_edge_hypotheses:
                # The paired score for accepting this edge is equal to the score 
                # of removing one no_relationship_penalty. 
                score = -self.parameters.no_relationship_penalty
                score *= centrality_factor
                id_pair_1 = (hypothesis.id, ce_hypothesis.id)
                id_pair_2 = (ce_hypothesis.id, hypothesis.id)
                paired_scores[id_pair_1] = score
                paired_scores[id_pair_2] = score
            # end for ce_hypothesis
        # end for hypothesis in obj_hypotheses
        return (individual_scores, paired_scores)
    # end _predict_object_scores

    def _equal_id_pairs(self, pair_1: tuple[int, int], pair_2: tuple[int, int]):
        """
        Determines whether or not two pairs of hypothesis ids have the same
        two ids.
        """
        return (True if (pair_1[0] in pair_2 and pair_1[1] in pair_2) 
                else False)
    # end _equal_id_pairs

    def _equal_id_triplets(self, triplet_1: tuple[int, int, int], 
                            triplet_2: tuple[int, int, int]):
        """
        Determines whether or not two triplets of hypothesis ids have the same
        three ids.
        """
        return (True if (triplet_1[0] in triplet_2 
                         and triplet_1[1] in triplet_2
                         and triplet_1[2] in triplet_2)
                         else False)
    # end _equal_id_triplets

    def _solve_mwis(self, individual_scores: dict[int, float],
                    paired_scores: dict[tuple[int, int], float]):
        """
        Solve max weight independent set on the hypothesis IDs and their scores.
        
        Returns
        -------
        solution_sets : list[list[int]]
            A list of all of the solution sets as lists of hypothesis ids.
        energies : list[float]
            A list of all of the energy values for each solution set in the
            same order as the solution_sets list.
        """
        qubo_matrix = dict()
        # Scores should, ideally, be between -1 and 1, with negative being
        # MORE preferred to be picked and positive being LESS preferred.
        # Set a scaling factor here.
        # Make it negative, since predicted scores are calculated s.t. the
        # higher they are the better they are.
        scaling_factor = -1/const.H_SCORE_OFFSET
        # Scale and encode all the individual scores into the matrix.
        for id, score in individual_scores.items():
            id_pair = (id, id)
            qubo_matrix[id_pair] = score * scaling_factor
        # end for
        # Scale and encode all the paired scores into the matrix.
        for id_pair, score in paired_scores.items():
            qubo_matrix[id_pair] = score * scaling_factor
        # end for

        # Sample the sampler using the QUBO matrix above.
        # Uses the Simulated Annealing Sampler from:
        #   https://docs.ocean.dwavesys.com/projects/neal/en/latest/reference/sampler.html
        sampler = SimulatedAnnealingSampler()

        # sample_qubo returns a SampleSet:
        #   https://docs.ocean.dwavesys.com/en/stable/docs_dimod/reference/sampleset.html#dimod.SampleSet
        number_of_solution_sets = 10
        sample_response = sampler.sample_qubo(qubo_matrix, 
                                              num_reads=number_of_solution_sets)
        #print(sample_response)
        sample_iterator = sample_response.samples()
        solution_sets = list()
        energies = sample_response.data_vectors['energy']
        # Each sample is a dictionary, with hypothesis ids as keys and either a
        # 1, if it's accepted, or a 0, if it's not, as values.
        for sample in sample_iterator:
            solution_set = [h_id for h_id, score in sample.items()
                            if score == 1]
            solution_sets.append(solution_set)
        # end for
        return (solution_sets, energies)
    # end _solve_mwis

    # DEBUG: CURRENTLY UNUSED
    def score_hypothesis_set(self, knowledge_graph: KnowledgeGraph, 
                             hypotheses: dict[int, Hypothesis]):
        """
        Scores a knowledge graph and a set of hypotheses.

        The assumption is that the hypotheses passed in are going to be accepted
        into the knowledge graph. 

        Returns a dictionary of hypothesis scores, keyed by hypothesis id.
        """
        # For ConceptEdgeHypotheses, take their scores.
        hypothesis_scores = dict()
        ce_hypotheses = [h for h in hypotheses.values() 
                         if type(h) == ConceptEdgeHypothesis]
        for hypothesis in ce_hypotheses:
            hypothesis_scores[hypothesis.id] = hypothesis.score
        # end for
        # For ObjectDuplicateHypotheses, take their scores.
        od_hypotheses = [h for h in hypotheses.values()
                         if type(h) == ObjectDuplicateHypothesis]
        for hypothesis in od_hypotheses:
            hypothesis_scores[hypothesis.id] = hypothesis.score
        # end for
        # For InstanceHypotheses, subtract one no_relationship_penalty for each
        # other Instance in the same image. Then, add one no_relationship_penalty
        # as well as the strength of the edge for each ConceptEdgeHypothesis
        # that was accepted for it. 
        i_hypotheses = [h for h in hypotheses.values()
                        if type(h) == OffscreenObjectHypothesis]
        for hypothesis in i_hypotheses:
            score = 0
            image = hypothesis.obj.get_image()
            scene_instances = knowledge_graph.get_scene_instances(image)
            scene_instances.extend(h.obj for h in i_hypotheses
                                   if h.obj.get_image() == image)
        # end for

        return hypothesis_scores
    # score_solution_set

# end class HypothesisEvaluator