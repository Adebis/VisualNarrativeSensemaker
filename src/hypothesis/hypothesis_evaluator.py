from timeit import default_timer as timer

from dataclasses import dataclass, field

import dwave_networkx as dnx
from neal.sampler import SimulatedAnnealingSampler

import constants as const
from parameters import ParameterSet
from knowledge_graph.graph import KnowledgeGraph
from knowledge_graph.items import (Instance, Edge)
from hypothesis.hypothesis import (Hypothesis, ConceptEdgeHyp, 
                                   SameObjectHyp,
                                   CausalSequenceHyp, 
                                   NewObjectHyp,
                                   PersistObjectHyp)

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
        # DEBUG:
        timers = dict()
        timers["start"] = timer()
        # Predict the change in score from accepting each hypothesis.
        # For MWIS solving, need to get a predicted score for each hypothesis
        # itself and a predicted score for accepting that hypothesis with 
        # certain other hypotheses.
        # Key: hypothesis id. Value: predicted score for accepting that 
        # hypothesis.
        individual_scores = dict()
        # Key: frozenset pair of hypothesis IDs. Value: predicted score for 
        # accepting both of those hypotheses together.
        paired_scores = dict()

        # Get scores making sure all hypotheses are only accepted when their
        # premises are accepted.
        individual_scores, paired_scores = self._predict_premise_scores(
            hypotheses=hypotheses)
        timers["end_predict_premise"] = timer()

        # Score all ConceptEdgeHypotheses
        #i_scores, p_scores = self._predict_concept_edge_scores(
        #    hypotheses=hypotheses)
        #self._integrate_scores(individual_scores, i_scores)
        #self._integrate_scores(paired_scores, p_scores)
        #timers["end_concept_edge"] = timer()

        # Score all NewObjectHyps
        #i_scores, p_scores = self._predict_new_object_scores(
        #    knowledge_graph=knowledge_graph, hypotheses=hypotheses)
        #self._integrate_scores(individual_scores, i_scores)
        #self._integrate_scores(paired_scores, p_scores)
        #timers["end_new_object"] = timer()

        # Score all PersistObjectHyps
        #i_scores, p_scores = self._predict_persist_object_scores(
        #    hypotheses=hypotheses)
        #self._integrate_scores(individual_scores, i_scores)
        #self._integrate_scores(paired_scores, p_scores)
        #timers["end_persist_object"] = timer()

        # Score all SameObjectHyps
        i_scores, p_scores, id_triplets = self._predict_same_object_scores(
            hypotheses=hypotheses,
            paired_scores=paired_scores)
        self._integrate_scores(individual_scores, i_scores)
        timers["end_same_object"] = timer()

        # Score all CausalSequenceHyps
        i_scores = self._predict_causal_sequence_scores(
            hypotheses=hypotheses,
            paired_scores=paired_scores
        )
        self._integrate_scores(individual_scores, i_scores)
        timers["end_causal_sequence"] = timer()

        print("Done scoring.")

        # Solve the maximum weight independent set problem consisting of these
        # hypotheses' ids and their predicted scores.
        solution_set_ids, energies_list = self._solve_mwis(
            individual_scores=individual_scores, paired_scores=paired_scores)
        timers["end_solve_mwis"] = timer()
        
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

        #print("Times taken:")
        #print(f'Total time spent predicting scores: {timers["end_same_object"] - timers["start"]}')
        #print(f'Predict premise scores: {timers["end_predict_premise"] - timers["start"]}')
        #print(f'Predict ConceptEdgeHyp scores: {timers["end_concept_edge"] - timers["end_predict_premise"]}')
        #print(f'Predict NewObjectHyp scores: {timers["end_new_object"] - timers["end_concept_edge"]}')
        #print(f'Predict PersistObjectHyp scores: {timers["end_persist_object"] - timers["end_new_object"]}')
        #print(f'Predict SameObjectHyp scores: {timers["end_same_object"] - timers["end_persist_object"]}')
        #print(f'Total time spent solving MWIS: {timers["end_solve_mwis"] - timers["end_same_object"]}')

        return solutions
    # end evaluate_hypotheses

    def _integrate_scores(self, base_scores: dict, additional_scores: dict):
        """
        Integrates the dictionary of scores in additional_scores into the
        dictionary of scores in base_scores in-place.
        """
        for score_key, score in additional_scores.items():
            self._integrate_score(base_scores=base_scores, score_key=score_key,
                                  score=score)
        # end for
    # end _integrate_scores
    def _integrate_score(self, base_scores: dict, score_key, score: float):
        """
        Integrates a single score into a dictionary of scores in-place.
        """
        if not score_key in base_scores:
            base_scores[score_key] = 0
        base_scores[score_key] += score
    # end _integrate_score

    def _predict_premise_scores(self, hypotheses: dict[int, Hypothesis]):
        """
        Gets individual and paired score dictionaries with values set such that 
        hypotheses won't be accepted without their premise hypotheses also being 
        accepted.

        Returns
        -------
        individual_scores : dict[int, float]
            The individual scores for each hypothesis, keyed by hypothesis id.
        paired_scores : dict[frozenset[int, int], float]
            The paired scores for accepting two hypotheses together, keyed by
            the ids of both hypotheses.
        """
        individual_scores = dict()
        paired_scores = dict()
        for h_id, h in hypotheses.items():
            # Give each hypothesis a large negative value to its individual
            # score based on the number of premises it has.
            individual_scores[h_id] = -len(h.premises) * const.H_SCORE_OFFSET
            for p_id, p in h.premises.items():
                # Give a large positive score to each hypothesis paired with its 
                # premises. This way, when both are accepted together, the large
                # negative value to its individual score will be removed. 
                paired_scores[frozenset([h_id, p_id])] = const.H_SCORE_OFFSET
        # end for
        return individual_scores, paired_scores
    # end _predict_premise_scores

    def _predict_same_object_scores(self, 
        hypotheses: dict[int, Hypothesis], 
        paired_scores: dict[frozenset[int, int], float]):
        """
        Predict scores for all of the SameObjectHyps.
        
        Parameters
        ----------
        hypotheses : dict[int, Hypothesis]
            All of the Hypotheses, keyed by id.
        paired_scores : dict[frozenset[int, int], float]
            Existing paired scores between hypotheses. Key is a pair of
            hypothesis ids. Value is the score between them. Adds to paired
            scores in-place.

        Returns
        -------
        individual_scores : dict[int, float]
            The individual scores for each SameObjectHyp, keyed by
            hypothesis id.
        new_paired_scores : dict[frozenset[int, int], float]
            The paired scores for accepting two hypotheses together, keyed by
            the ids of both hypotheses.
        id_triplets : dict[int, frozenset[int, int, int]]
            All of the triplets of ids for the transitive property triplets 
            found between SameObjectHyps, keyed by the negative integer ID the
            triplet was assigned.

            Their key ids match their id in the new_paired_scores dictionary,
            and are always negative.
        """
        # DEBUG:
        timers = dict()
        times = dict()
        timers["start"] = timer()
        individual_scores = dict()
        # Get all the SameObjectHyps
        same_object_hyps = [h for h in hypotheses.values()
                         if type(h) == SameObjectHyp]
        for hypothesis in same_object_hyps:
            # Individual score is based on its similarity score.
            score = hypothesis.get_individual_score()
            # Accepting this hypothesis also gets rid of one no_continuity
            # penalty, so subtract that here.
            #score -= self.parameters.continuity_penalty
            # Multiply the score by the average centrality between the two
            # Instances this hypothesis is between.
            #score *= (hypothesis.object_1.get_centrality() + 
            #          hypothesis.object_2.get_centrality()) / 2
            individual_scores[hypothesis.id] = score
        # end for

        # All SameObjectHyps should now have an individual score and
        # its paired scores with any of its premise hypotheses.
        # Find all of the SameObjectHyp pairs that contradict one
        # another.
        timers["start_dupe"] = timer()
        id_pairs = self._find_contradicting_duplicate_pairs(
            hypotheses=hypotheses)
        times["dupes"] = timer() - timers["start_dupe"]

        # For each pair, set their paired score to a large negative number to
        # enforce the fact that they should never be accepted together.
        for id_pair in id_pairs:
            self._integrate_score(paired_scores, id_pair, -const.H_SCORE_OFFSET)
        # Find all of the transitive property triplets.
        timers["start_prop"] = timer()
        id_triplets_set = self._find_transitive_property_triplets(
            hypotheses=hypotheses)
        times["props"] = timer() - timers["start_prop"]
        # Store the triplets in a dictionary and key them. 
        id_triplets = dict()
        triplet_counter = 1
        for id_triplet in id_triplets_set:
            # Make sure their ids are all negative.
            id_triplets[-triplet_counter] = id_triplet
            triplet_counter += 1
        # end for

        timers["start_triplets"] = timer()
        paired_scores_to_add = dict()
        for triplet_id, triplet in id_triplets.items():
            # Have the triplet itself adopt all of the paired scores of its
            # member hypotheses.
            # Between each hypothesis in a triplet, give their paired scores a
            # large negative number.
            # Between the id of the triplet itself and each hypothesis, give 
            # their paired scores a large negative number. 
            # This way, either all of them are accepted or exactly one of them 
            # are accepted.
            for h_id in triplet:
                # Have the triplet adopt the paired scores of its members. 
                incident_pairs = [id_pair for id_pair in paired_scores.keys()
                                  if h_id in id_pair]
                for id_pair in incident_pairs:
                    id_pair_list = list(id_pair)
                    other_id = -1
                    # If this pair contains the id of the triplet member h_id, 
                    # get the other id in the pair.
                    if h_id == id_pair_list[0]:
                        other_id = id_pair_list[1]
                    elif h_id == id_pair_list[1]:
                        other_id = id_pair_list[0]
                    else:
                        continue
                    # Have the triplet adopt its member's paired score.
                    pair_key = frozenset([triplet_id, other_id])
                    paired_scores_to_add[pair_key] = paired_scores[id_pair]
                # end for
                # Place a large negative score between the triplet and this
                # member.
                pair_key = frozenset([triplet_id, h_id])
                paired_scores_to_add[pair_key] = -const.H_SCORE_OFFSET

                # Place a large negative score between each member.
                for other_h_id in triplet:
                    if h_id == other_h_id:
                        continue
                    pair_key = frozenset([h_id, other_h_id])
                    paired_scores_to_add[pair_key] = -const.H_SCORE_OFFSET
                # end for
            # end for
        # end for
        times["triplets"] = timer() - timers["start_triplets"]
        self._integrate_scores(paired_scores, paired_scores_to_add)

        times["total"] = timer() - timers["start"]
        #print("Times taken predicting SameObjectHyp scores")
        #print(f'Total: {times["total"]}')
        #print(f'Finding contradicting duplicate pairs: {times["dupes"]}')
        #print(f'Finding transitive property triplets: {times["props"]}')
        #print(f'Resolving triplet score adoption: {times["triplets"]}')

        return individual_scores, paired_scores, id_triplets
    # end _predict_same_object_scores

    def _find_contradicting_duplicate_pairs(self, 
                hypotheses: dict[int, Hypothesis]) -> set[frozenset[int, int]]:
        """
        Finds all the pairs of SameObjectHyps that contradict with
        one another.

        Two SameObjectHyps contradict if they both assert that one
        Object is equal to two other Objects that are both in the same scene.

        Returns a set of hypothesis id pairs (without duplicates).
        """
        # Store the ids of all contradicting hypothesis pairs as frozensets.
        id_pairs = set()
        # Get all the SameObjectHyps.
        same_object_hyps = [h for h in hypotheses.values()
                            if type(h) == SameObjectHyp]
        # Two SameObjectHyps contradict if they:
        #   1. Share an Object.
        #   2. Both have non-shared Objects that are in the same scene. 
        for hypothesis_1 in same_object_hyps:
            for hypothesis_2 in same_object_hyps:
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
                    id_pair = frozenset([hypothesis_1.id, hypothesis_2.id])
                    id_pairs.add(id_pair)
                # end if
            # end for hypothesis_2
        # end for hypothesis_1
        return id_pairs
    # end _find_contradicting_duplicate_pairs

    def _find_transitive_property_triplets(self, 
            hypotheses: dict[int, Hypothesis]) -> set[frozenset[int, int, int]]:
        """
        Finds all the transitive property triplets amongst the
        SameObjectHyps in the hypotheses passed in.

        Three SameObjectHyps form a triplet if the transitive
        property requires that they all be accepted if at least two of the are
        accepted.
        
        e.g. hypothesis_1: object_1->is->object_2, 
        hypothesis_2: object_1->is->object_3, 
        hypothesis_3: object_2->is->object_3.

        Returns a set of hypothesis id triplets as frozensets.
        """
        # Store the transitive property triplets as triplets of hypothesis ids.
        id_triplets = set()
        # Get all the SameObjectHyps.
        same_object_hyps = [h for h in hypotheses.values()
                         if type(h) == SameObjectHyp]
        for hypothesis_1 in same_object_hyps:
            # Look for another hypothesis that leads to or from one of this
            # hypothesis' objects.
            for hypothesis_2 in same_object_hyps:
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
                for hypothesis_3 in same_object_hyps:
                    if hypothesis_1 == hypothesis_3:
                        continue
                    elif hypothesis_2 == hypothesis_3:
                        continue
                    # end elif
                    if (hypothesis_3.has_object(non_matching_object_1) and
                        hypothesis_3.has_object(non_matching_object_2)):
                        # This is a transitive property triplet.
                        id_triplet = frozenset([hypothesis_1.id, 
                                                hypothesis_2.id, 
                                                hypothesis_3.id])
                        id_triplets.add(id_triplet)
                    # end if
                # end for hypothesis_3
            # end for hypothesis_2
        # end for hypothesis_1
        return id_triplets
    # end _find_transitive_property_triplets

    def _predict_causal_sequence_scores(self, 
        hypotheses: dict[int, Hypothesis], 
        paired_scores: dict[frozenset[int, int], float]) -> dict[int, float]:
        """
        Predict scores for all of the CausalSequenceHyps.
        
        Parameters
        ----------
        hypotheses : dict[int, Hypothesis]
            All of the Hypotheses, keyed by id.
        paired_scores : dict[frozenset[int, int], float]
            Existing paired scores between hypotheses. Key is a pair of
            hypothesis ids. Value is the score between them. Adds to paired
            scores in-place.

        Returns
        -------
        individual_scores : dict[int, float]
            The individual scores for each SameObjectHyp, keyed by
            hypothesis id.

        new_paired_scores : dict[frozenset[int, int], float]
            The paired scores for accepting two hypotheses together, keyed by
            the ids of both hypotheses.
        """
        individual_scores = dict()

        # Get all CausalSequenceHyps
        causal_sequence_hyps = [h for h in hypotheses.values()
                                if type(h) == CausalSequenceHyp]
        # Go through each one and predict its score.
        for hyp in causal_sequence_hyps:
            score = hyp.get_individual_score()
            individual_scores[hyp.id] = score
        # end for hyp

        return individual_scores
    # end _predict_causal_sequence_scores

    def _solve_mwis(self, individual_scores: dict[int, float],
                    paired_scores: dict[frozenset[int, int], float]):
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
        for ids, score in paired_scores.items():
            ids_list = list(ids)
            id_pair_1 = (ids_list[0], ids_list[1])
            id_pair_2 = (ids_list[1], ids_list[0])
            # Divide each half by two so the scores don't double.
            qubo_matrix[id_pair_1] = score * scaling_factor / 2
            qubo_matrix[id_pair_2] = score * scaling_factor / 2
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



    # UNUSED
    # ====================================


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
        paired_scores : dict[frozenset[int, int], float]
            The paired scores for accepting two hypotheses together, keyed by
            the ids of both hypotheses.
        """
        individual_scores = dict()
        paired_scores = dict()
        # Gather all the concept edge hypotheses.
        concept_edge_hyps = [h for h in hypotheses.values() 
                             if type(h) == ConceptEdgeHyp]
        for hypothesis in concept_edge_hyps:
            # The hypothesis' individual score is its evidence score, modified
            # by any parameters.
            score = hypothesis.get_individual_score()
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
        # end for
        return individual_scores, paired_scores
    # end _predict_concept_edge_scores

    def _predict_new_object_scores(self, knowledge_graph: KnowledgeGraph, 
                                   hypotheses: dict[int, Hypothesis]):
        """
        Predicts scores for all of the NewObjectHyps.

        Parameters
        ----------
        knowledge_graph : KnowledgeGraph
            The knowledge graph, to look at observed Instances.
        hypotheses : dict[int, Hypothesis]
            All of the Hypotheses, keyed by id.
        
        Returns
        -------
        individual_scores : dict[int, float]
            The individual scores for each NewObjectHyp, keyed by
            hypothesis id.
        paired_scores : dict[frozenset[int, int], float]
            The paired scores for accepting two hypotheses together, keyed by
            the ids of both hypotheses.
        """
        individual_scores = dict()
        paired_scores = dict()
        # Get all the NewObjectHypotheses.
        new_object_hyps = [h for h in hypotheses.values() 
                           if type(h) == NewObjectHyp]
        for hypothesis in new_object_hyps:
            # Get the image for the scene this hypothesized Instance is in.
            image = hypothesis.obj.get_image()
            # Get all the observed Instances in the same scene.
            observed_instances = knowledge_graph.get_scene_instances(image)
            # Get all the ObjectHypotheses in the same scene that are
            # not this hypothesis.
            scene_obj_hypotheses = [h for h in new_object_hyps
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

            # Add a paired score for each hypothesized Object in the same
            # scene equal to one no_relationship_penalty.
            for other_new_obj_hyp in scene_obj_hypotheses:
                score = self.parameters.no_relationship_penalty
                score *= centrality_factor
                self._integrate_score(base_scores=paired_scores,
                    score_key=frozenset([hypothesis.id, other_new_obj_hyp.id]),
                    score=score)
            # end for scene_obj_hypothesis

            # Go through all of this hypothesis' ConceptEdgeHypotheses.
            for concept_edge_hyp in hypothesis.concept_edge_hyps:
                # Accepting this concept edge hypothesis means negating one 
                # no_relationship_penalty.
                # Add a paired score.
                score = -self.parameters.no_relationship_penalty
                score *= centrality_factor
                self._integrate_score(base_scores=paired_scores,
                    score_key=frozenset([hypothesis.id, concept_edge_hyp.id]),
                    score=score)
            # end for concept_edge_hyp

        # end for hypothesis in obj_hypotheses
        return (individual_scores, paired_scores)
    # end _predict_new_object_scores

    def _predict_persist_object_scores(self, hypotheses: dict[int, Hypothesis]):
        """
        Predicts scores for all the PersistObjectHyps.

        Returns
        -------
        individual_scores : dict[int, float]
            The individual scores for each PersistObjectHyp, keyed by
            hypothesis id.
        paired_scores : dict[frozenset[int, int], float]
            The paired scores for accepting two hypotheses together, keyed by
            the ids of both hypotheses.
        """
        individual_scores = dict()
        paired_scores = dict()
        persist_object_hyps = [h for h in hypotheses.values()
                               if type(h) == PersistObjectHyp]
        # PersistObjectHypotheses really only relies on the new object 
        # hypothesis and same object hypothesis it generates alongside itself. 
        # Both of those are already accounted for as premises in 
        # predict_premise_scores.
        for hypothesis in persist_object_hyps:
            individual_scores[hypothesis.id] = 0
        # end for
        return individual_scores, paired_scores
    # end _predict_persist_object_scores



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
        concept_edge_hyps = [h for h in hypotheses.values() 
                         if type(h) == ConceptEdgeHyp]
        for hypothesis in concept_edge_hyps:
            hypothesis_scores[hypothesis.id] = hypothesis.score
        # end for
        # For SameObjectHyps, take their scores.
        same_object_hyps = [h for h in hypotheses.values()
                         if type(h) == SameObjectHyp]
        for hypothesis in same_object_hyps:
            hypothesis_scores[hypothesis.id] = hypothesis.score
        # end for
        # For InstanceHypotheses, subtract one no_relationship_penalty for each
        # other Instance in the same image. Then, add one no_relationship_penalty
        # as well as the strength of the edge for each ConceptEdgeHypothesis
        # that was accepted for it. 
        i_hypotheses = [h for h in hypotheses.values()
                        if type(h) == NewObjectHyp]
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