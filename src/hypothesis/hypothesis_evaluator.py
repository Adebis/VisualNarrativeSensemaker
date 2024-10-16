from timeit import default_timer as timer

from dataclasses import dataclass, field

import dwave_networkx as dnx
from neal.sampler import SimulatedAnnealingSampler

import constants as const

from parameters import ParameterSet
from knowledge_graph.graph import KnowledgeGraph
from knowledge_graph.items import (Instance, Edge)
from hypothesis.hypothesis import (Hypothesis, 
                                   SameObjectHyp,
                                   CausalSequenceHyp,
                                   HypothesisSet,
                                   CausalHypChain)
from hypothesis.contradiction import (Contradiction, 
                                      HypothesisCon,
                                      HypothesisSetCon,
                                      InImageTransCon, 
                                      TweenImageTransCon,
                                      CausalCycleCon,
                                      CausalHypFlowCon,
                                      CausalChainFlowCon)

@dataclass
class Rejection():
    """
    A dataclass storing information about why a Hypothesis was rejected
    in a Solution.

    Attributes:
    -----------
    rejected_hyp : Hypothesis
        The hypothesis that was rejected in the Solution.
    explanation : str
        A text explanation of why the Hypothesis was rejected.
    """

    rejected_hyp: Hypothesis
    explanation: str

# end class Rejection

@dataclass
class HypConRejection(Rejection):
    """
    A Rejection whose reason is that the rejected hypothesis
    contradicts another hypothesis which was accepted instead of it. 

    Attributes:
    contradicting_hyp : Hypothesis
        The accepted hypothesis that contradicts with the rejected hypothesis.
    contradiction : Contradiction
        The contradiction between the rejected and accepted hypotheses.
    """

    contradicting_hyp: Hypothesis
    contradiction: HypothesisCon

# end class HypSetConRejection
    
@dataclass
class HypSetConRejection(Rejection):
    """
    A Rejection whose reason is that the rejected hypothesis is part of a
    hypothesis set which contradictions another hypothesis set that was
    accepted instead of it. 

    Attributes:
    contradicting_hyp_set : Hypothesis
        The accepted hypothesis set that contradicts with the rejected 
        hypothesis' set. 
    contradiction : Contradiction
        The contradiction between the rejected and accepted hypotheses.
    """

    contradicting_hyp_set: HypothesisSet
    contradiction: HypothesisSetCon

# end class HypSetConRejection

@dataclass
class CausalCycleRejection(Rejection):
    '''
    A Rejection whose reason is that accepting the hypothesis would have
    meant creating a causal cycle.

    Attributes:
        contradicting_hyps : list[Hypothesis]
            The hypotheses that were accepted instead of the rejected
            hypothesis.
        contradiction : CausalCycleCon
            The CausalCycleCon that caused the rejected hypothesis to be
            rejected.
    '''
    contradicting_hyps: list[Hypothesis]
    contradiction: CausalCycleCon
# end CausalCycleRejection

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
    accepted_hyp_sets : dict[int, HypothesisSet]
        The hypothesis sets accepted in this solution.
    energy : float
        The energy value for this solution's accepted hypothesis set.
        Result of solving the MWIS problem. Lower energy means the hypothesis
        set is better.
    rejections : list[Rejection]
        The set of Rejections for hypotheses that were not accepted in
        this solution. 
    """

    id: int = field(init=False)
    parameters: ParameterSet
    accepted_hypotheses: dict[int, Hypothesis]
    accepted_hyp_sets: dict[int, HypothesisSet]
    energy: float
    rejections: list[Rejection]

    _next_id = 0
    def __post_init__(self):
        # Assign the id, then increment the class ID counter so the next
        # Solution gets a unique id. 
        self.id = Solution._next_id
        Solution._next_id += 1
    # end __post_init__
# end class Solution
        
@dataclass
class SolutionSet():
    """
    A set of solutions to the sensemaking MOP problem made from a single
    ParameterSet

    Attributes:
    -----------
    id : int
        A unique integer identifier. Matches the ID of the parameter set
        used to make this SolutionSet.
    parameters : ParameterSet
        The parameter set used to make this solution set.
    individual_scores : dict[int, float]
        The individual scores given to each hypothesis, keyed by hypothesis id.
    paired_scores : dict[frozenset[int, int], float]
        The paired scores given to each pair of hypotheses whose joint
        acceptance affected their scores. Keyed by frozenset pairs of hypothesis
        ids.
        If IDs are negative, they refer to an ID triplet. The IDs of all three
        hypotheses in the triplet can be obtained from the id_triplet dict.
    hyp_sets : dict[int, HypothesisSet]
        The hypothesis sets used in this solution, keyed by the set' ID.
        Hypothesis set IDs are always negative.
    contradictions : list[Contradiction]
        The set of contradictions between hypotheses that led to this
        solution set. A single set of parameters should yield a single
        set of contradictions for every solution in this set. 
    solutions : List[Solution]
        The set of solutions themselves.
    """

    id: int = field(init=False)
    parameters: ParameterSet
    individual_scores: dict[int, float]
    paired_scores: dict[frozenset[int, int], float]
    hyp_sets: dict[int, HypothesisSet]
    contradictions: list[Contradiction]
    solutions: list[Solution]

    def __post_init__(self):
        # Assign the id.
        self.id = self.parameters.id
    # end __post_init__
# end class SolutionSet

class HypothesisEvaluator():
    """
    Handles evaluating a knowledge graph and a set of hypotheses.

    Scores the hypotheses and applies constraints.

    Attributes:
    -----------
    """

    def __init__(self, ):
        """

        """
        print('Initializing hypothesis evaluator')
    # end __init__

    def evaluate_hypotheses(self, knowledge_graph: KnowledgeGraph,
                 hypotheses: dict[int, Hypothesis],
                 parameter_set: ParameterSet) -> SolutionSet:
        """
        Evaluate a knowledge graph and a set of hypotheses.

        Parameters
        ----------
        knowledge_graph : KnowledgeGraph
            The knowledge graph to be evaluated.
        hypotheses : dict[int, Hypothesis]
            The set of hypotheses to be evaluated with the knowledge graph. A
            dictionary of Hypothesis objects, keyed by their ids.
        parameter_set : ParameterSet
            The set of system parameters being used for this evaluation.
            
        Returns
        -------
        solution_set : SolutionSet
            A set of solutions to the problem of which hypotheses to accept
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
        hyp_sets = dict()

        contradictions = list()

        # Get scores making sure all hypotheses are only accepted when their
        # premises are accepted.
        #individual_scores, paired_scores = self._predict_premise_scores(
        #    hypotheses=hypotheses)
        #timers["end_predict_premise"] = timer()

        # Score all SameObjectHyps
        # Adds to individual and paired score dicts in-place.
        new_hyp_sets, cons = self._predict_same_object_scores(
            hypotheses=hypotheses,
            individual_scores=individual_scores,
            paired_scores=paired_scores,
            knowledge_graph=knowledge_graph,
            parameter_set=parameter_set)
        contradictions.extend(cons)
        hyp_sets.update(new_hyp_sets)
        timers["end_same_object"] = timer()

        # Score all CausalSequenceHyps.
        # Adds to individual and paired score dicts in-place.
        new_hyp_sets, cons = self._predict_causal_sequence_scores(
            hypotheses=hypotheses,
            individual_scores=individual_scores,
            paired_scores=paired_scores,
            knowledge_graph=knowledge_graph,
            parameter_set=parameter_set
        )
        contradictions.extend(cons)

        # If there are too many contradictions, this'll take too long.
        # Abort here and return an empty solution set.
        if len(contradictions) > 10000:
            print(f'HypothesisEvaluator.evaluate_hypotheses:' 
                  + f' {len(contradictions)} contradictions. Aborting.')
            solution_set = SolutionSet(parameters=parameter_set,
                                       individual_scores=dict(),
                                       paired_scores=dict(),
                                       hyp_sets=dict(),
                                       contradictions=list(),
                                       solutions=list())
            return solution_set
        # end if

        hyp_sets.update(new_hyp_sets)
        timers["end_causal_sequence"] = timer()

        # Resolve all the hypothesis sets' scores between them and their member 
        # hypotheses and them and other hypothesis sets.
        self._calculate_hyp_set_scores(hyp_sets=hyp_sets,
                                       hypotheses=hypotheses,
                                       individual_scores=individual_scores,
                                       paired_scores=paired_scores)

        #print("Done scoring.")

        # Solve the maximum weight independent set problem consisting of these
        # hypotheses' ids and their predicted scores.
        solution_sets, energies_list = self._solve_mwis(
            individual_scores=individual_scores, paired_scores=paired_scores)
        timers["end_solve_mwis"] = timer()
        
        #print("Done solving MWIS")

        # Put together the solutions and the solution set.
        solutions = list()
        for i in range(len(solution_sets)):
            accepted_h_ids = solution_sets[i]
            accepted_hyps = dict()
            accepted_hyp_sets = dict()
            for accepted_h_id in accepted_h_ids:
                # Gather all accepted hypotheses
                if accepted_h_id in hypotheses:
                    accepted_hyps[accepted_h_id] = hypotheses[accepted_h_id]
                # If this id is for a hypothesis set, 
                # add the hypotheses in the set to the solution set and the
                # set itself to the solution set. 
                elif accepted_h_id in hyp_sets:
                    hyp_set = hyp_sets[accepted_h_id]
                    accepted_hyp_sets[accepted_h_id] = hyp_set
                    for h_id in hyp_set.hypotheses.keys():
                        if h_id in accepted_h_ids:
                            print(f'HypothesisEvaluator.evaluate_hypotheses:'
                                  + f' Error: both hypothesis set {hyp_set.id}'
                                  + f' and individual hypothesis {h_id}'
                                  + f' accepted.')
                        accepted_hyps[h_id] = hypotheses[h_id]
                    # end for
                else:
                    print(f'HypothesisEvaluator.evaluate_hypotheses : id ' +
                          f'{accepted_h_id} not in hypotheses or triplets.')
                # end else
            # end for
            # Generate Rejections for all rejected hypotheses.
            rejections = self._generate_rejections(
                hypotheses=hypotheses,
                accepted_ids=accepted_h_ids,
                accepted_hypotheses=accepted_hyps,
                contradictions=contradictions,
                individual_scores=individual_scores,
                paired_scores=paired_scores)
            solution = Solution(parameters=parameter_set,
                                accepted_hypotheses=accepted_hyps,
                                accepted_hyp_sets=accepted_hyp_sets,
                                energy=energies_list[i],
                                rejections=rejections)
            solutions.append(solution)
        # end for
        solution_set = SolutionSet(parameters=parameter_set,
                                   individual_scores=individual_scores,
                                   paired_scores=paired_scores,
                                   hyp_sets=hyp_sets,
                                   contradictions=contradictions,
                                   solutions=solutions)

        #print("Times taken:")
        #print(f'Total time spent predicting scores: {timers["end_same_object"] - timers["start"]}')
        #print(f'Predict premise scores: {timers["end_predict_premise"] - timers["start"]}')
        #print(f'Predict ConceptEdgeHyp scores: {timers["end_concept_edge"] - timers["end_predict_premise"]}')
        #print(f'Predict NewObjectHyp scores: {timers["end_new_object"] - timers["end_concept_edge"]}')
        #print(f'Predict PersistObjectHyp scores: {timers["end_persist_object"] - timers["end_new_object"]}')
        #print(f'Predict SameObjectHyp scores: {timers["end_same_object"] - timers["end_persist_object"]}')
        #print(f'Total time spent solving MWIS: {timers["end_solve_mwis"] - timers["end_same_object"]}')

        return solution_set
    # end evaluate_hypotheses

    def _generate_rejections(self, hypotheses: dict[int, Hypothesis],
                             accepted_ids: list[int],
                             accepted_hypotheses: dict[int, Hypothesis],
                             contradictions: list[Contradiction],
                             individual_scores: dict[int, float],
                             paired_scores: dict[int, float])->list[Rejection]:
        """
        Generates Rejections for all the hypotheses not accepted in a Solution.
        """
        rejections = list()
        # Gather all the rejected hypotheses.
        rejected_hyps = {h_id: h for h_id, h in hypotheses.items()
                         if not (h_id in accepted_hypotheses)}
        # Go through each one, determine why it was rejected, and make a
        # Rejection for it.
        for rejected_hyp in rejected_hyps.values():
            # First, check for a HypConRejection.
            for contradiction in contradictions:
                # For hypothesis contradictions
                # See if this contradiction involves the rejected hypothesis
                # and if the other hypothesis was accepted.
                # If so, the hypothesis was rejected because it contradicts
                # with an accepted hypothesis. 
                if issubclass(type(contradiction), HypothesisCon):
                    if (rejected_hyp in contradiction 
                        and contradiction.other_hypothesis(rejected_hyp).id in
                        accepted_hypotheses):
                        contradicting_hyp = contradiction.other_hypothesis(rejected_hyp)
                        explanation = (f'Hypothesis {str(rejected_hyp)} was rejected'
                                    + f' because it has a {type(contradiction).__name__} contradiction'
                                    + f' with accepted Hypothesis {str(contradicting_hyp)}.')
                        rejections.append(HypConRejection(
                            rejected_hyp=rejected_hyp,
                            explanation=explanation,
                            contradicting_hyp=contradicting_hyp,
                            contradiction=contradiction))
                    # end if
                # end if
                # For hypothesis set contradictions
                # See if one of the sets of this contradiction involves the
                # rejected hypothesis and if the other set's hypotheses were
                # all accepted. 
                # If so, the hypothesis was rejected because the set it was in
                # contradicts with an accepted hypothesis set.
                elif issubclass(type(contradiction), HypothesisSetCon):
                    if rejected_hyp in contradiction:
                        other_hyp_set = contradiction.other_hyp_set(rejected_hyp)
                        other_set_accepted = True
                        for hyp in other_hyp_set.hypotheses.values():
                            if hyp.id not in accepted_hypotheses:
                                other_set_accepted = False
                                break
                            # end if
                        # end for
                        if other_set_accepted:
                            contradicting_hyp_set = contradiction.other_hyp_set(rejected_hyp)
                            explanation = (f'Hypothesis {rejected_hyp} was rejected'
                                    + f' because its set {contradiction.get_hyp_set(rejected_hyp).id}'
                                    + f' has a {type(contradiction).__name__} contradiction'
                                    + f' with accepted set {contradicting_hyp_set.id}.')
                            rejections.append(HypSetConRejection(
                                rejected_hyp=rejected_hyp,
                                explanation=explanation,
                                contradicting_hyp_set=contradicting_hyp_set,
                                contradiction=contradiction
                            ))
                        # end if
                    # end if
                # end elif
                # For causal cycle contradictions.
                elif type(contradiction) == CausalCycleCon:
                    # If the rejected hyp was in the causal chain...
                    # See if all the other hypotheses in the chain were accepted.
                    # If so, this one was rejected to avoid a causal cycle. 
                    if not rejected_hyp in contradiction.causal_chain:
                        continue
                    all_other_accepted = True
                    contradicting_hyps = list()
                    for hyp in contradiction.causal_chain.get_hypothesis_list():
                        if hyp == rejected_hyp:
                            continue
                        if hyp.id in accepted_hypotheses:
                            contradicting_hyps.append(hyp)
                        elif hyp.id not in accepted_hypotheses:
                            all_other_accepted = False
                    # end for
                    if not all_other_accepted:
                        continue
                    explanation = (f'Hypothesis {rejected_hyp} was rejected'
                            + f' because it forms a causal cycle with'
                            + f' accepted hypothesis(es)')
                    for hyp in contradicting_hyps:
                        explanation += f' hypothesis {hyp},'
                    # end for
                    explanation.rstrip(',')
                    explanation += (f' to/from image {contradiction.image.id}.')
                    rejection = CausalCycleRejection(
                        rejected_hyp=rejected_hyp,
                        explanation=explanation,
                        contradicting_hyps=contradicting_hyps,
                        contradiction=contradiction
                    )
                    rejections.append(rejection)
                # end elif
            # end for contradiction in contradictions
        # end for rejected_hyp in rejected_hyps
        return rejections
    # end _generate_rejections

    def _integrate_scores(self, score_dict: dict, additional_scores: dict):
        """
        Integrates the dictionary of scores in additional_scores into the
        dictionary of scores in base_scores in-place.
        """
        for score_key, score in additional_scores.items():
            self._integrate_score(score_dict=score_dict, score_key=score_key,
                                  score=score)
        # end for
    # end _integrate_scores
    def _integrate_score(self, score_dict: dict, score_key, score: float):
        """
        Integrates a single score into a dictionary of scores in-place.
        """
        if not score_key in score_dict:
            score_dict[score_key] = 0
        score_dict[score_key] += score
    # end _integrate_score
        
    # Get all of the paired scores for a hypothesis or hypothesis set.
    # Returns a dictionary of scores keyed by the ID of the other half of the 
    # paired score key.
    def _get_all_paired_scores(self, score_dict: dict, id: int):
        """
        
        """
        all_paired_scores = dict()
        for id_pair, score in score_dict.items():
            if not id in id_pair:
                continue
            other_id = 0
            for id_2 in list(id_pair):
                if not id_2 == id:
                    other_id = id_2
            # end for
            all_paired_scores[other_id] = score
        # end for
        return all_paired_scores
    # end _get_all_paired_scores
    
    def _calculate_hyp_set_scores(self, 
                                  hyp_sets: dict[int, HypothesisSet], 
                                  hypotheses: dict,
                                  individual_scores: dict, 
                                  paired_scores: dict):
        """
        Resolves the individual and paired scores for each hypothesis set, their
        member hypotheses, and other hypothesis sets.

        Adjust their scores in the individual and paired scores dicts in-place.
        """

        hyp_set_list = list(hyp_sets.values())

        for n in range(len(hyp_set_list)):
            hyp_set = hyp_set_list[n]
            # Individual Score
            # The hyp set's individual score is equal to the sum of the
            # individual scores of each of its member hyps, as well as
            # the sum of the paired scores between each of its member hyps.
            # If this is an all_or_ex set, also add +k * H_SCORE_OFFSET to
            # cancel out the k -H_SCORE_OFFSETS amongst its member hyps.
            ind_score_to_add = 0
            if hyp_set.is_all_or_ex:
                k = len(hyp_set.hypotheses)
                ind_score_to_add += k * const.H_SCORE_OFFSET
            set_hyps = list(hyp_set.hypotheses.values())
            for i in range(len(set_hyps)):
                hyp = set_hyps[i]
                # Add this hyp's individual score to the set's individual score.
                ind_score_to_add += individual_scores[hyp.id]
                # If this is the last hypothesis, stop here.
                if i == len(set_hyps) - 1:
                    break
                # Add this hyp's paired score to other hyps in this set to
                # the set's individual score.
                for j in range(i + 1, len(set_hyps)):
                    other_hyp = set_hyps[j]
                    pair_id_key = frozenset([hyp.id, other_hyp.id])
                    if pair_id_key in paired_scores:
                        ind_score_to_add += paired_scores[pair_id_key]
                # end for j
            # end for i
            self._integrate_score(score_dict=individual_scores,
                                  score_key=hyp_set.id,
                                  score=ind_score_to_add)

            # Paired Scores to hyps
            for hyp in set_hyps:
                # The hyp set has a large negative paired score with each of
                # its members so that the entire set isn't accepted alongside
                # its members individually.
                self._integrate_score(score_dict=paired_scores,
                                      score_key=frozenset([hyp_set.id, hyp.id]),
                                      score=-const.H_SCORE_OFFSET)
                # Paired scores from member hyps to non-member hyps get added as
                # paired scores from the hyp set to the non-member hyp.
                hyp_paired_scores = self._get_all_paired_scores(paired_scores,
                                                                hyp.id)
                for other_id, paired_score in hyp_paired_scores.items():
                    # Check if this id is a hypothesis' id and the hyp is
                    # not a member of this set.
                    if other_id in hypotheses and not other_id in hyp_set:
                        # Add a paired score between the non-member hyp and
                        # the hyp set. 
                        id_pair = frozenset([hyp_set.id, other_id])
                        self._integrate_score(score_dict=paired_scores,
                                              score_key=id_pair,
                                              score=paired_score)
                    # end if
                # end for
            # end for

            # Paired Scores to hyp sets
            #   The sum of paired scores between non-shared hyps gets added as a
            #   paired score between the hyp sets.
            if n == len(hyp_set_list) - 1:
                continue
            for m in range(n + 1, len(hyp_set_list)):
                other_hyp_set = hyp_set_list[m]
                other_set_hyps = list(other_hyp_set.hypotheses.values())
                hyp_set_pair = frozenset([hyp_set.id, other_hyp_set.id])
                paired_score_to_add = 0
                for hyp in set_hyps:
                    for other_hyp in other_set_hyps:
                        # If this is a shared hyp, don't add its paired score.
                        if other_hyp in hyp_set:
                            continue
                        hyp_pair = frozenset([hyp.id, other_hyp.id])
                        if hyp_pair in paired_scores:
                            paired_score_to_add += paired_scores[hyp_pair]
                    # end for
                # end for
                self._integrate_score(score_dict=paired_scores,
                                      score_key=hyp_set_pair,
                                      score=paired_score_to_add)
            # end for

            # Special cases for sets with single members.
            # If a set has a single hyp, copy all of the paired scores
            # of that set, excluding ones to the hyp itself, to the hyp.
            if len(hyp_set.hypotheses) == 1:
                single_hyp = list(hyp_set.hypotheses.values())[0]
                # Gather all the paired scores to integrate, then
                # integrate them all after.
                paired_scores_to_integrate = list()
                for id_pair, paired_score in paired_scores.items():
                    # Is this a paired score for this hyp set?
                    if hyp_set.id in id_pair:
                        id_pair_list = list(id_pair)
                        # If so, find the other id in the pair.
                        other_id = id_pair_list[0]
                        if other_id == hyp_set.id:
                            other_id = id_pair_list[1]
                        # end if
                        # If the other id is that of the hyp set's single hyp,
                        # skip this.
                        if other_id == single_hyp.id:
                            continue
                        # end if
                        # Add a paired score between this hyp set's single
                        # hyp and the other id in the pair.
                        new_id_pair = frozenset([single_hyp.id, other_id])
                        paired_scores_to_integrate.append([new_id_pair, paired_score])
                    # end if
                # end for
                for paired_score_to_integrate in paired_scores_to_integrate:
                    self._integrate_score(score_dict=paired_scores,
                                          score_key=paired_score_to_integrate[0],
                                          score=paired_score_to_integrate[1])
                # end for
            # end if

        # end for n in range(len(hyp_set_list)):
    # end _calculate_hyp_set_scores

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
        individual_scores: dict[int, float],
        paired_scores: dict[frozenset[int, int], float],
        knowledge_graph: KnowledgeGraph,
        parameter_set: ParameterSet):
        """
        Predict scores for all of the SameObjectHyps.
        
        Parameters
        ----------
        hypotheses : dict[int, Hypothesis]
            All of the Hypotheses, keyed by id.
        individual_scores : dict[int, float]
            The individual scores for each Hypothesis, keyed by hypothesis id.

            This function adds any new individual scores to the individual
            scores dictionary in-place.
        paired_scores : dict[frozenset[int, int], float]
            Existing paired scores between hypotheses. Key is a pair of
            hypothesis ids. Value is the score between them. 
            
            This function adds any new paired scores to the paired scores
            dictionary in-place.
        parameter_set : ParameterSet
            The parameters being used in this evaluation.
        Returns
        -------
        hyp_sets : dict[int, frozenset[int, int, int]]
            Any new hypothesis sets made for all of the transitive property 
            triplets found between SameObjectHyps, keyed by the negative integer 
            ID the triplet was assigned.
        contradictions : list[Contradiction]
            The contradictions found while predicting same object scores.
        """
        hyp_sets = dict()
        contradictions = list()
        # Get all the SameObjectHyps
        same_object_hyps = [h for h in hypotheses.values()
                         if type(h) == SameObjectHyp]
        for hypothesis in same_object_hyps:
            # Individual score is based on its similarity score.
            score = hypothesis.get_individual_score(parameter_set)
            # Accepting this hypothesis also increases the density of the
            # overall knowledge graph by 2/(n(n-1)), where n is the number
            # of instances in the knowledge graph.
            n = knowledge_graph.get_instance_count()
            density_increase = 2 / (n * (n - 1))
            density_score = density_increase * parameter_set.density_weight
            score += density_score
            self._integrate_score(score_dict=individual_scores,
                                  score_key=hypothesis.id,
                                  score=score)
        # end for

        # All SameObjectHyps should now have an individual score and
        # its paired scores with any of its premise hypotheses.
        # Find all of the SameObjectHyp pairs that have in-image transitivity
        # contradictions with one another. 

        in_image_trans_cons = self._generate_in_image_trans_cons(
            hypotheses=hypotheses)

        # Add the contradictions to the overall list of contradictions.
        contradictions.extend(in_image_trans_cons)
        # Make ID pairs for each pair of hypotheses in an in-image transitivity
        # contradiction with each other. 
        id_pairs = set()
        for contradiction in in_image_trans_cons:
            id_pairs.add(frozenset([contradiction.hypothesis_1.id, 
                                    contradiction.hypothesis_2.id]))
        # end for
        # For each pair, set their paired score to a large negative number to
        # enforce the fact that they should never be accepted together.
        for id_pair in id_pairs:
            self._integrate_score(paired_scores, id_pair, -const.H_SCORE_OFFSET)
        
        # Find all SameObjectHyp triplets for which rejecting one creates
        # a tween-image transitivity contradiction. 
        # Find all of the transitive property triplets.

        tween_image_trans_cons, new_hyp_sets = self._generate_tween_image_trans_cons(
            hypotheses=hypotheses)
        hyp_sets.update(new_hyp_sets)
        contradictions.extend(tween_image_trans_cons)
        # Accepting a hypothesis set means accepting every single
        # hypothesis in the set.
        # Not accepting the hypothesis set means rejecting at least one 
        # hypothesis of the set. 
        # Rejecting exactly one member of one of these sets causes a tween-image
        # transitivity contradiction between the remaining two members.
        # Thus, if the entire set is not accepted, only one member may be
        # accepted. Accepting two members causes a contradiction. 
        # Set the paired score of any pair of hypotheses in the same set to be
        # a large negative number, to enforce the fact that they should never
        # be accepted together if the entire set is not accepted.
        for hyp_set in hyp_sets.values():
            hyp_list = hyp_set.get_hypothesis_list()
            for i in range(len(hyp_list)):
                hyp_1 = hyp_list[i]
                if i == len(hyp_list) - 1:
                    continue
                for j in range(i + 1, len(hyp_list)):
                    hyp_2 = hyp_list[j]
                    if hyp_1 == hyp_2:
                        continue
                    id_pair = frozenset([hyp_1.id, hyp_2.id])
                    self._integrate_score(score_dict=paired_scores, 
                                          score_key=id_pair, 
                                          score=-const.H_SCORE_OFFSET)
                # end for
            # end for
        # end for

        return hyp_sets, contradictions
    # end _predict_same_object_scores

    def _generate_in_image_trans_cons(self, 
                hypotheses: dict[int, Hypothesis]) -> list[InImageTransCon]:
        """
        Finds all the pairs of SameObjectHyps that have an In Image Transitivity
        Contradiction with one another.

        Two SameObjectHyps have an In-Image Transitivity Contradiction if they 
        both assert that one Object is equal to two other Objects that both
        appear in the same image. 

        Returns a list of InImageTransCons.
        """
        contradictions = list()

        # Get all the SameObjectHyps.
        same_object_hyps = [h for h in hypotheses.values()
                            if type(h) == SameObjectHyp]
        # Two SameObjectHyps have an InImageTransCon if they:
        #   1. Share an Object.
        #   2. Both have non-shared Objects that are in the same scene. 
        for i in range(len(same_object_hyps)):
            hypothesis_1 = same_object_hyps[i]
            if i >= len(same_object_hyps) - 1:
                break
            for j in range(i + 1, len(same_object_hyps)):
                hypothesis_2 = same_object_hyps[j]
                # See if one of the Objects matches between hypothesis 1 and 2.
                # Then, hypothesis 1 has one non-matching Object and
                # hypothesis 2 has one non-matching Object.
                # Find the matching Object, hypothesis 1's non-matching Object,
                # and hypothesis 2's non-matching Object.
                shared_object = hypothesis_1.get_shared_object(hypothesis_2)
                if shared_object is None:
                    continue
                unique_object_1 = hypothesis_1.get_other_object(shared_object)
                unique_object_2 = hypothesis_2.get_other_object(shared_object)
                # If the two non-matching Objects are both in the same scene,
                # this is a contradiction!
                if (unique_object_1.get_image() == unique_object_2.get_image()):
                    explanation = ('Hypothesis ' + str(hypothesis_1) + ' and '
                        + 'hypothesis ' + str(hypothesis_2) + ' assert that '
                        + 'object ' + str(unique_object_1) + ' and ' +
                        'object ' + str(unique_object_2) + ', which are '
                        + 'both in Image ' + str(unique_object_1.get_image())
                        + ', are equal to object ' + str(shared_object)
                        + '. This is a Within Image Transitivity Contradiction.')
                    contradiction = InImageTransCon(explanation=explanation,
                                                    hypothesis_1=hypothesis_1,
                                                    hypothesis_2=hypothesis_2,
                                                    obj_1=unique_object_1,
                                                    obj_2=unique_object_2,
                                                    shared_obj=shared_object)
                    contradictions.append(contradiction)
                # end if
            # end for hypothesis_2
        # end for hypothesis_1
        return contradictions
    # end _generate_in_image_trans_cons

    def _generate_tween_image_trans_cons(self, 
        hypotheses: dict[int, Hypothesis]) -> tuple[list[TweenImageTransCon], 
                                               set[dict[int, frozenset[int, int, int]]]]:
        """
        Finds all the triplets of SameObjectHyps that have a Between Image
        Transitivity Contradiction with one another. 

        Two SameObjectHyps have a Tween-Image Transitivity Contradiction if they 
        both assert that one Object is equal to two other Objects but there is
        no Hypothesis asserting that the two other Objects also equal each other.

        In practice, we find all triplets of SameObjectHyps where rejecting any
        one of them would cause the other two to have a TweenImageTransCon with
        each other. 

        Returns the TweenImageTransCons created and triplets of
        Hypotheses that mutually could have TweenImageTransCons with each other
        as hypothesis sets.
        """
        contradictions = list()
        # First, find all the transitive property triplet IDs.
        all_id_triplets = self._find_transitive_property_triplets(hypotheses)
        # Make a HypothesisSet out of each triplet.
        new_hyp_sets = dict()
        
        for id_triplet in all_id_triplets:
            hyp_triplet = [hypotheses[id] for id in id_triplet]
            # This is an all-or-ex set; either all of its members get accepted
            # together or none of them get accepted together
            triplet_set = HypothesisSet(hyp_triplet, is_all_or_ex=True)
            new_hyp_sets[triplet_set.id] = triplet_set
        # end for

        # For each triplet, make three TweenImageTransCons; one for each pair
        # of hypotheses. 
        for hyp_set in new_hyp_sets.values():
            hyp_list = hyp_set.get_hypothesis_list()
            con_1 = self._generate_tween_image_trans_con(hypothesis_1=hyp_list[0],
                                                         hypothesis_2=hyp_list[1],
                                                         joining_hypothesis=hyp_list[2],
                                                         hyp_set_id=hyp_set.id)
            con_2 = self._generate_tween_image_trans_con(hypothesis_1=hyp_list[0],
                                                         hypothesis_2=hyp_list[2],
                                                         joining_hypothesis=hyp_list[1],
                                                         hyp_set_id=hyp_set.id)
            con_3 = self._generate_tween_image_trans_con(hypothesis_1=hyp_list[1],
                                                         hypothesis_2=hyp_list[2],
                                                         joining_hypothesis=hyp_list[0],
                                                         hyp_set_id=hyp_set.id)
            contradictions.append(con_1)
            contradictions.append(con_2)
            contradictions.append(con_3)
        # end for

        return contradictions, new_hyp_sets
    # end _generate_tween_image_trans_cons

    def _generate_tween_image_trans_con(self,
                                        hypothesis_1: SameObjectHyp, 
                                        hypothesis_2: SameObjectHyp,
                                        joining_hypothesis: SameObjectHyp,
                                        hyp_set_id: int):
        """
        Makes a TweenImageTransCon between the hypothesis 1 and hypothesis 2.
        """
        # Figure out obj_1, obj_2, and shared_obj.
        shared_obj = hypothesis_1.get_shared_object(hypothesis_2)
        obj_1 = hypothesis_1.get_other_object(shared_obj)
        obj_2 = hypothesis_2.get_other_object(shared_obj)
        # Make the TweenImageTransCon
        explanation = ('Hypothesis ' + str(hypothesis_1) + ' and Hypothesis ' +
                       str(hypothesis_2) + ' assert that Object ' + str(obj_1) +
                       ' and Object ' + str(obj_2) + ' both equal Object ' +
                       str(shared_obj) + ', requiring Hypothesis ' +
                       str(joining_hypothesis) + ' between Objects ' + str(obj_1) +
                       ' and ' + str(obj_2) + ' to maintain the transitive' +
                       ' property.')
        contradiction = TweenImageTransCon(explanation=explanation,
                                           hypothesis_1=hypothesis_1,
                                           hypothesis_2=hypothesis_2,
                                           obj_1=obj_1,
                                           obj_2=obj_2,
                                           shared_obj=shared_obj,
                                           joining_hyp=joining_hypothesis,
                                           hyp_set_id=hyp_set_id)
        return contradiction
    # end _generate_tween_image_trans_con

    def _find_transitive_property_triplets(self, 
            hypotheses: dict[int, Hypothesis]) -> set[frozenset[int, int, int]]:
        """
        Finds all the transitive property triplets amongst the
        SameObjectHyps in the hypotheses passed in.

        Three SameObjectHyps form a triplet if the transitive
        property requires that they all be accepted if at least two of them are
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
                shared_object = hypothesis_1.get_shared_object(hypothesis_2)
                if shared_object is None:
                    continue
                unique_object_1 = hypothesis_1.get_other_object(shared_object)
                unique_object_2 = hypothesis_2.get_other_object(shared_object)

                # Look for a third hypothesis between the other two hypotheses'
                # non-matching objects.
                for hypothesis_3 in same_object_hyps:
                    if hypothesis_1 == hypothesis_3:
                        continue
                    elif hypothesis_2 == hypothesis_3:
                        continue
                    # end elif
                    if (hypothesis_3.has_object(unique_object_1) and
                        hypothesis_3.has_object(unique_object_2)):
                        # This is a transitive property triplet.
                        id_triplet = frozenset([hypothesis_1.id, 
                                                hypothesis_2.id, 
                                                hypothesis_3.id])
                        id_triplets.add(id_triplet)
                        break
                    # end if
                    #else:
                    #    print('HypothesisEvaluator.FindTransitivePropertyTriplets : '
                    #          + 'no joining hypothesis found for ' + str(hypothesis_1)
                    #          + ' and ' + str(hypothesis_2))
                # end for hypothesis_3
            # end for hypothesis_2
        # end for hypothesis_1
        return id_triplets
    # end _find_transitive_property_triplets

    def _predict_causal_sequence_scores(self, 
        hypotheses: dict[int, Hypothesis], 
        individual_scores: dict[int, float],
        paired_scores: dict[frozenset[int, int], float],
        knowledge_graph: KnowledgeGraph,
        parameter_set: ParameterSet) -> dict[int, float]:
        """
        Predict scores for all of the CausalSequenceHyps.
        
        Parameters
        ----------
        hypotheses : dict[int, Hypothesis]
            All of the Hypotheses, keyed by id.
        individual_scores : dict[int, float]
            The individual scores for each Hypothesis, keyed by hypothesis id.

            This function adds any new individual scores to the individual
            scores dictionary in-place.
        paired_scores : dict[frozenset[int, int], float]
            Existing paired scores between hypotheses. Key is a pair of
            hypothesis ids. Value is the score between them. 
            
            This function adds any new paired scores to the paired scores
            dictionary in-place.
        parameter_set : ParameterSet
            The system parameters being used for this evaluation.

        Returns
        -------
        hyp_sets : dict[int, HypothesisSet]
            Any new HypothesisSets that were created while generating 
            contradictions.
        contradictions : list[Contradiction]
            The contradictions found while predicting causal sequence scores.
        """
        hyp_sets = dict()
        contradictions = list()

        # Get all causal cycle contradictions and any new hypothesis sets in 
        # those contradictions.
        causal_cycle_cons, new_hyp_sets = self._generate_causal_cycle_cons(
            knowledge_graph=knowledge_graph,
            hypotheses=hypotheses)
        hyp_sets.update(new_hyp_sets)
        contradictions.extend(causal_cycle_cons)

        # If all of the hypotheses in a CausalCycleCon are accepted together,
        # it would be a contradiction.
        # Set paired scores such that all hypotheses in the same CausalCycleCon 
        # cannot be accepted together. 
        for causal_cycle_con in causal_cycle_cons:
            # The chain that forms the causal cycle contradiction should be
            # given a large negative score, since accepting it is a
            # contradiction.
            self._integrate_score(score_dict=individual_scores,
                                  score_key=causal_cycle_con.causal_chain.id,
                                  score=-const.H_SCORE_OFFSET)
            
            # If there are only two hypotheses, give them a large negative
            # paired score with each other.
            if len(causal_cycle_con.causal_chain) == 2:
                hyps = causal_cycle_con.causal_chain.get_hypothesis_list()
                hyp_1 = hyps[0]
                hyp_2 = hyps[1]
                id_pair = frozenset([hyp_1.id, hyp_2.id])
                score = -const.H_SCORE_OFFSET
                self._integrate_score(score_dict=paired_scores,
                                      score_key=id_pair,
                                      score=score)
            # end if
            # If there are three hypotheses, each pair of hypotheses in the 
            # contradiction must have a large negative score with the last
            # hypothesis in the contradiction.
            elif len(causal_cycle_con.causal_chain) == 3:
                subset_ex_pairs = causal_cycle_con.get_subset_exclusion_pairs()
                for subset, hyp in subset_ex_pairs:
                    id_pair = frozenset([subset.id, hyp.id])
                    score = -const.H_SCORE_OFFSET
                    self._integrate_score(score_dict=paired_scores,
                                          score_key=id_pair,
                                          score=score)
                # end for
            # end elif
            # If there are causal cycles of any other length, something has
            # gone wrong.
            else:
                print(f'HypothesisEvaluator._predict_causal_sequence_scores'
                      + f': Error! CausalCycleCon has chain of length'
                      + f' {len(causal_cycle_con.causal_chain)}.')
            # end else
        # end for

        # Get all CausalSequenceHyps
        causal_sequence_hyps = [h for h in hypotheses.values()
                                if type(h) == CausalSequenceHyp]
        # Go through each one and predict its score.
        for hyp in causal_sequence_hyps:
            # The individual score is the sum of the scores of this hyp's
            # causal path evidence.
            # STORY CURVE: it also calculates and adds the hypothesis' compliance
            # to the story curve to its score.
            score = hyp.get_individual_score(parameter_set)
            # Accepting this hypothesis also increases the density of the
            # overall knowledge graph by 2/(n(n-1)), where n is the number
            # of instances in the knowledge graph.
            n = knowledge_graph.get_instance_count()
            density_increase = 2 / (n * (n - 1))
            density_score = density_increase * parameter_set.density_weight
            score += density_score
            self._integrate_score(score_dict=individual_scores,
                                  score_key=hyp.id,
                                  score=score)
            # For each piece of continuity evidence, add a paired score.
            # We aren't expressing when a piece of continuity evidence is missing
            # (i.e. if the subject or object does NOT match).
            # Sum the continuity evidence scores first, then apply the threshold 
            # and the weight on the sum. 
            continuity_ev_score = 0
            # If the objects do not match, that's continuity evidence with a
            # score of 0. 
            #no_continuity_score_penalty = -parameter_set.continuity_ev_thresh * parameter_set.continuity_ev_weight
            # Give the causal sequence hyp an initial penalty to its individual 
            # score equal to the threshold.

            # If the subjects do not match, that's continuity evidence with a
            # score of 0. 

            # Give the causal sequence hyp an initial penalty to its individual
            # score equal to the threshold. 
            # In total, add -2 * the continuity evidence threshold to this
            # hypothesis' individual score. If it's accepted alone at this point
            # without any continuity evidence, it carries that penalty. 

            # Not using this continuity penalty because it's being handled
            # by the continuity weight. 

            #self._integrate_score(score_dict=individual_scores,
            #                      score_key=hyp.id,
            #                      score=no_continuity_score_penalty * 2)
            paired_hyp_id_pairs = list()
            for continuity_ev in hyp.continuity_evs:
                id_pair = frozenset([hyp.id, continuity_ev.joining_hyp.id])
                paired_hyp_id_pairs.append(id_pair)
                continuity_ev_score += 1
                # The value of the paired score for a piece of continuity
                # evidence is just the continuity evidence weight itself.
                #paired_score = 1.0

                # Also offset the hypothesis' initial 
                # individual score penalty. We know that this piece of
                # continuity evidence exists now, so we don't need it.
                #self._integrate_score(score_dict=individual_scores,
                #                      score_key=hyp.id,
                #                      score=-no_continuity_score_penalty)
            # end for
            
            # First, apply a penalty to the individual score of this hypothesis
            # equal to the penalty of the continuity evidence threshold if there
            # was no continuity.
            no_continuity_penalty = -parameter_set.continuity_ev_thresh
            # Apply the weight.
            no_continuity_penalty *= parameter_set.continuity_ev_weight
            self._integrate_score(score_dict=individual_scores,
                                score_key=hyp.id,
                                score=no_continuity_penalty)

            # Apply the continuity evidence threshold.
            if continuity_ev_score < parameter_set.continuity_ev_thresh:
                continuity_ev_score -= parameter_set.continuity_ev_thresh
            # Apply the continuity evidence weight.
            continuity_ev_score *= parameter_set.continuity_ev_weight
            # Add a score offsetting the no-continuity penalty so it can be 
            # mitigated when the hypotheses that establish continuity are accepted. 
            continuity_ev_score -= no_continuity_penalty
            # If there were continuous hypotheses:
            if len(paired_hyp_id_pairs) > 0:
                # Integrate the score as a paired score divided amongst all the
                # hypotheses that makes this continuity true. 
                divided_score = continuity_ev_score / len(paired_hyp_id_pairs)
                for id_pair in paired_hyp_id_pairs:
                    self._integrate_score(score_dict=paired_scores,
                                        score_key=id_pair,
                                        score=divided_score)
                # end for
            # end if
        # end for hyp

        return hyp_sets, contradictions
    # end _predict_causal_sequence_scores

    def _generate_causal_cycle_cons(self,
                                   knowledge_graph: KnowledgeGraph,
                                   hypotheses: dict[int, Hypothesis]
        ) -> tuple[list[CausalCycleCon], dict[int, HypothesisSet]]:
        """
        If there is a chain of causal hypotheses that start and end at the
        same image, those hypotheses form a cycle. Accepting all of those
        hypotheses together would be a CausalCycleCon. 

        Returns a list of CausalCycleCons and a dictionary of CausalHypSets, 
        keyed by their negative number ids.
        """
        # DEBUG: DISABLING CAUSAL CYCLE CONS TO REDUCE COMBINATORIAL EXPLOSION
        return list(), dict()
        # Get all causal hypotheses.
        causal_hyps = [h for h in hypotheses.values() 
                       if type(h) is CausalSequenceHyp]

        # Lists of causal chains, keyed by length of causal chain and the id
        # of the image the chain starts from.
        # Each causal chain is an ordered list of causal sequence hypotheses. 
        # Key 1: length of causal chain.
        # Key 2: id of starting image of chain.
        # Value: list of causal sequence hypotheses.
        all_causal_chains: dict[int, dict[int, list[list[CausalSequenceHyp]]]] = dict()

        # For causal chain length k.
        # The minimum length of a causal chain is 1.
        # The maximum length of a causal chain is the number of images.
        for k in range(1, len(knowledge_graph.images) + 1):
            if not k in all_causal_chains:
                all_causal_chains[k] = dict()
            # Image i is the starting image.
            for image_i in knowledge_graph.images.values():
                if not image_i.id in all_causal_chains[k]:
                    all_causal_chains[k][image_i.id] = list()
                # If this is not the base case, get all the causal chains of 
                # length k - 1 that start at image i.
                i_causal_chains: list[list[CausalSequenceHyp]] = list()
                if not k == 1:
                    i_causal_chains = all_causal_chains[k - 1][image_i.id]
                # Image j is the ending image. 
                for image_j in knowledge_graph.images.values():
                    #if image_i == image_j:
                        #if k < len(knowledge_graph.images):
                        #    continue
                    #    continue
                    # end if
                    # Base case.
                    if k == 1:
                        # Get all the causal hypotheses from image_i to
                        # image_j.
                        i_j_hyps = [h for h in causal_hyps
                                    if h.get_true_source_image() == image_i
                                    and h.get_true_target_image() == image_j]
                        # Start a new causal chain starting from image_i for 
                        # each one.
                        for hyp in i_j_hyps:
                            all_causal_chains[1][image_i.id].append([hyp])
                        # end for
                        continue
                    # end if
                    # Go through each causal chain of length k - 1 starting at 
                    # image i that hasn't already ended at image j.
                    for i_causal_chain in [c for c in i_causal_chains
                                           if image_j not in 
                                           [h.get_true_target_image()
                                            for h in c]]:
                        # Get all the causal hypotheses leading from the image
                        # at the end of this chain to image j.
                        last_image = i_causal_chain[-1].get_true_target_image()
                        i_j_hyps = [h for h in causal_hyps
                                    if h.get_true_source_image() == last_image
                                    and h.get_true_target_image() == image_j]
                        # For each one, make a new chain by taking the current
                        # chain and placing the new hypothesis at the end.
                        for new_hyp in i_j_hyps:
                            new_chain = list()
                            for existing_hyp in i_causal_chain:
                                new_chain.append(existing_hyp)
                            # end for
                            new_chain.append(new_hyp)
                            all_causal_chains[k][image_i.id].append(new_chain)
                        # end for
                    # end for
                # end for
            # end for
        # end for

        # Remove all causal chains for length 1. These can never form a cycle.
        del all_causal_chains[1]

        # Now that we have all the causal chains, gather all the chains leading
        # between each pair of images.
        # First key is the id of the image at the start of the chain.
        # Second key is the id of the image at the end of the chain.
        # Value is a list of the CausalHypChains between the start image and the
        # end image.
        image_pair_chains: dict[int, dict[int, list[CausalHypChain]]] = dict()
        # Key is the id of an image.
        # Value is a list of chains starting at that image.
        for image_i in knowledge_graph.images.values():
            for image_j in knowledge_graph.images.values():
                # For each length of causal chain greater than 1.
                for k in range(2, len(knowledge_graph.images)):
                    # Get all the causal chains starting at image_i and
                    # ending at image_j
                    chains_to_add = [c for c in all_causal_chains[k][image_i.id]
                                     if c[-1].get_true_target_image() == image_j]
                    # Make a hypothesis set out of it.
                    for chain in chains_to_add:
                        new_hyp_set = CausalHypChain(chain)
                        if not image_i.id in image_pair_chains:
                            image_pair_chains[image_i.id] = dict()
                        if not image_j.id in image_pair_chains[image_i.id]:
                            image_pair_chains[image_i.id][image_j.id] = list()
                        image_pair_chains[image_i.id][image_j.id].append(new_hyp_set)
                    # end for
                # end for
            # end for
        # end for

        # Now that we have all the chains leading from each image to each other 
        # image, we can make a CausalCycleCon for each chain that starts and
        # ends at the same image.
        # Keep track of each chain of causal sequence hyps
        # that we end up using for a contradiction.  
        # Also keep track of their subsets, if they have any.
        # The key of each set will be a negative number, starting at -1.
        new_hyp_sets = dict()
        causal_cycle_cons = list()
        for i in range(len(knowledge_graph.images) - 1):
            image_i = list(knowledge_graph.images.values())[i]
            # If there are no causal chains starting at image i or not causal
            # chains starting at image i and ending at image i, go to the
            # next image.
            if (not image_i.id in image_pair_chains
                or not image_i.id in image_pair_chains[image_i.id]):
                continue

            # Get all causal chains from image i to image i.
            cycle_chains = image_pair_chains[image_i.id][image_i.id]

            # Make a CausalCycleCon for each chain that forms a cycle. 
            for cycle_chain in cycle_chains:
                explanation = f'Causal chain {cycle_chain.id} of hypotheses'
                for h in cycle_chain.get_hypothesis_list():
                    explanation += f' {h.id},'
                # end for
                explanation.rstrip(',')
                explanation += (f' asserts a causal cycle to and from image'
                                + f' {image_i.id}. Accepting all hypotheses'
                                + f' in this chain together is a contradiction.')
                con = CausalCycleCon(explanation=explanation,
                                     image=image_i,
                                     causal_chain=cycle_chain)
                causal_cycle_cons.append(con)
                # Add the cycle to the set of new hyp sets.
                if not cycle_chain.id in new_hyp_sets:
                    new_hyp_sets[cycle_chain.id] = cycle_chain
                # If the CausalCycleCon has any subsets, add those to the new
                # hyp sets too.
                for subset in con.subsets:
                    if not subset.id in new_hyp_sets:
                        new_hyp_sets[subset.id] = subset
                # end for
            # end for cycle_chain
        # end for i

        return causal_cycle_cons, new_hyp_sets
    # end _generate_causal_cycle_cons

    def _causal_hyps_would_contradict(self, 
                                      hyp_1: CausalSequenceHyp, 
                                      hyp_2: CausalSequenceHyp) -> bool:
        """
        Returns whether or not two causal sequence hypotheses would contradict
        one another.
        """
        if (hyp_1.get_true_source_image() == hyp_2.get_true_target_image()
            and hyp_1.get_true_target_image() == hyp_2.get_true_source_image()):
            return True
        else:
            return False
    # end _causal_hyps_would_contradict

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
            # DEBUG
            #for sample_item in sample.items():
            #    print("sample item " + str(sample_item))
            solution_set = [h_id for h_id, score in sample.items()
                            if score == 1]
            solution_sets.append(solution_set)
        # end for
        return (solution_sets, energies)
    # end _solve_mwis

# end class HypothesisEvaluator