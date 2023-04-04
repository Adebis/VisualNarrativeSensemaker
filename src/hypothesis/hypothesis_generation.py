from timeit import default_timer as timer

from commonsense.querier import CommonSenseQuerier
from commonsense.commonsense_data import (CommonSenseNode, CommonSenseEdge, 
                                          ConceptNetNode, WordNetNode)
from knowledge_graph.graph import KnowledgeGraph 
from knowledge_graph.items import (Concept, Instance, Object, Action, Edge)

import constants as const
from constants import ConceptType

from hypothesis.hypothesis import (Hypothesis, ConceptEdgeHyp, 
                                   NewObjectHyp, 
                                   ObjectDuplicateHypothesis,
                                   ObjectPersistenceHypothesis,
                                   ActionHypothesis, Evidence, 
                                   ConceptEdgeEvidence)

class HypothesisGenerator:
    """
    Handles generating hypotheses from a knowledge graph.
    """

    def __init__(self, commonsense_querier: CommonSenseQuerier):
        print(f'Initializing HypothesisGenerator')
        self._commonsense_querier = commonsense_querier
    # end __init__

    def generate_hypotheses(self, knowledge_graph: KnowledgeGraph) -> dict[int, Hypothesis]:
        """
        Generates hypotheses from a knowledge graph.

        Returns a dictionary of hypotheses, keyed by hypothesis id.
        """
        hypotheses = dict()
        print("Generating hypotheses")

        #action_hypotheses = self._generate_action_hypotheses(knowledge_graph)
        #hypotheses.update(action_hypotheses)

        # Make ConceptEdgeHypotheses between all observed Instances.
        observation_hypotheses = self._hypothesize_for_observations(
            knowledge_graph)
        hypotheses.update({h.id: h for h in observation_hypotheses})

        # Make Hypotheses to establish continuity between Images.
        continuity_hypotheses = self._hypothesize_for_continuity(knowledge_graph)
        hypotheses.update({h.id: h for h in continuity_hypotheses})

        print("Done generating hypotheses")
        return hypotheses
    # end generate_hypotheses

    def _hypothesize_for_observations(self, knowledge_graph: KnowledgeGraph):
        """
        Makes concept edge hypotheses between all observed Instances in 
        the knowledge graph with every other observed Instance in the same scene. 

        Returns a list of all the hypotheses generated.
        """
        new_hypotheses = list()
        # Keep track of every pair of instances we've checked.
        # Each item in the set is a tuple of the ids of a pair of Instances.
        instance_pairs_checked = set()
        # Treat every image as its own scene.
        for image in knowledge_graph.images.values():
            instances = knowledge_graph.get_scene_instances(image)

            # Generate concept edge hypotheses between every instance and
            # every other instance in the same scene.
            for instance_1 in instances:
                for instance_2 in instances:
                    # Don't make concept edge hypotheses between an instance
                    # and itself.
                    if instance_1 == instance_2:
                        continue
                    # Have to check the id pairs in both orders.
                    id_pair_1 = (instance_1.id, instance_2.id)
                    id_pair_2 = (instance_2.id, instance_1.id)
                    # Don't make a hypothesis between a pair of instances that 
                    # have already been checked for concept edge hypotheses.
                    if (id_pair_1 in instance_pairs_checked
                        or id_pair_2 in instance_pairs_checked):
                        continue
                    # Generate concept edge hypotheses between the two.
                    hypotheses = self._hypothesize_concept_edge(
                        instance_1=instance_1, instance_2=instance_2)
                    new_hypotheses.extend(hypotheses)
                    # Log that the two instances have checked each other.
                    instance_pairs_checked.add(id_pair_1)
                    instance_pairs_checked.add(id_pair_2)
                # end for
            # end for
        # end for
        return new_hypotheses
    # _hypothesize_for_observations

    def _hypothesize_concept_edge(self, instance_1: Instance, 
                                  instance_2: Instance):
        """
        Makes concept edge hypotheses between two Instances based on the
        edges between their Concepts. 

        Returns a list of all the hypotheses generated.
        """
        hypotheses = list()
        # Go through all of the edges from instance 1's Concepts.
        for concept in instance_1.concepts:
            # Get every edge with other Concepts and see if any of them are
            # with one of instance 2's concepts.
            concept_edges = concept.get_concept_edges()
            for edge in concept_edges:
                if edge.get_other_node(concept) in instance_2.concepts:
                    source_instance = None
                    target_instance = None
                    if edge.source == concept:
                        source_instance = instance_1
                        target_instance = instance_2
                    else:
                        source_instance = instance_2
                        target_instance = instance_1                     
                    # If it is, make a ConceptEdgeHypothesis of the two.
                    hypothesis = ConceptEdgeHyp(
                        source_instance=source_instance, 
                        target_instance=target_instance, 
                        edge=edge)
                    hypotheses.append(hypothesis)
                # end if
            # end for
        # end for
        return hypotheses
    # end _hypothesize_concept_edge

    def _hypothesize_for_continuity(self, knowledge_graph: KnowledgeGraph):
        """
        Generates Hypotheses to repair continuity between images.

        Returns a list of generated Hypotheses.
        """
        all_new_hypotheses = self._hypothesize_object_persistence(
            knowledge_graph=knowledge_graph)
        
        # Get all observed and hypothesized Objects.
        all_objects = list(knowledge_graph.objects.values())
        all_objects.extend([h.object_ for h in all_new_hypotheses
                            if type(h) == ObjectPersistenceHypothesis])

        for current_object in all_objects:
            # Get all the images the Object is NOT in.
            absent_images = list()
            for image in knowledge_graph.images.values():
                if not image.id in current_object.images:
                    absent_images.append(image)
            # end for

            for image in absent_images:
                # Go through each observed Object in this image and make an
                # ObjectDuplicateHypothesis with any of them whose Concepts
                # overlap with this current Object.
                scene_instances = knowledge_graph.get_scene_instances(image)
                for scene_instance in scene_instances:
                    # Only check other Objects.
                    if not type(scene_instance) == Object:
                        continue
                    # See if any of the concepts overlap.
                    for concept in current_object.concepts:
                        if scene_instance.has_concept(concept):
                            # If they do, make an ObjectDuplicateHypothesis.
                            new_od_h = ObjectDuplicateHypothesis(
                                object_1=current_object,
                                object_2=scene_instance)
                            all_new_hypotheses.append(new_od_h)
                            break
                        # end if
                    # end for
                # end for scene_instance in scene_instances

            # end for image in absent_images

        # end for current_object in all_objects.values()

        return all_new_hypotheses
    # end _hypothesize_for_continuity

    def _hypothesize_object_persistence(self, knowledge_graph: KnowledgeGraph):
        """
        Generates ObjectPersistenceHypotheses for all observed Objects
        in the knowledge graph.

        Returns a list of all the new Hypotheses that were generated.
        """
        new_hypotheses = list()
        # Go through every observed Object in the knowledge graph.
        for current_object in knowledge_graph.objects.values():
            # Get all the images the Object is NOT in.
            absent_images = list()
            for image in knowledge_graph.images.values():
                if not image.id in current_object.images:
                    absent_images.append(image)
            # end for
            # For each Image the Object is not in, make a NewObjectHyp 
            # that an Object with the current Object's Concepts, appearance, and
            # attributes is in that Image. 
            for image in absent_images:
                # Make the hypothesized Object.
                # Make sure it has the original Object's attributes and
                # appearance.
                new_object = Object(label=current_object.label,
                                    image=image,
                                    attributes=current_object.attributes,
                                    appearance=current_object.appearance,
                                    concepts=current_object.concepts,
                                    hypothesized=True)
                # Give the hypothesized Object the focal score of the Object 
                # it's copying.
                new_object.focal_score = current_object.focal_score
                # Make ConceptEdgeHypotheses to every observed Instance in the
                # same scene.
                concept_edge_hyps = list()
                for scene_instance in knowledge_graph.get_scene_instances(image):
                    concept_edge_hyps.extend(
                        self._hypothesize_concept_edge(
                            instance_1=new_object, 
                            instance_2=scene_instance))
                # end for
                # Make ConceptEdgeHypotheses to every other hypothesized
                # Object in the same scene.
                obj_hypotheses = [h for h in new_hypotheses 
                                  if type(h) == NewObjectHyp
                                  and h.obj.get_image() == image]
                for existing_hypothesis in obj_hypotheses:
                    ces_to_existing_hypotheses = self._hypothesize_concept_edge(
                        instance_1=new_object, 
                        instance_2=existing_hypothesis.obj)
                    # Make the existing Object hypothesis a premise for this
                    # concept edge hypothesis, too, since it wouldn't exist
                    # without the existing Object hypothesis.
                    for concept_edge_hyp in ces_to_existing_hypotheses:
                        concept_edge_hyp.add_premise(existing_hypothesis)
                    concept_edge_hyps.extend(ces_to_existing_hypotheses)
                # end for
                # Make the NewObjectHyp using these 
                # ConceptEdgeHypotheses as evidence.
                new_object_hyp = NewObjectHyp(
                    obj=new_object, 
                    concept_edge_hyps=concept_edge_hyps)
                # Make an ObjectDuplicateHypothesis between the original Object
                # and the hypothesized Object.
                object_duplicate_hypothesis = ObjectDuplicateHypothesis(
                    current_object, new_object)
                # Premise the ObjectDuplicateHypothesis on the 
                # NewObjectHyp, since it wouldn't exist without the 
                # new Object being hypothesized.
                object_duplicate_hypothesis.add_premise(new_object_hyp)
                # Premise the NewObjectHyp on the 
                # ObjectDuplicateHypothesis, since if it isn't a duplicate of 
                # the original Object it has no reason to exist.
                new_object_hyp.add_premise(object_duplicate_hypothesis)

                # Make the ObjectPersistenceHypothesis based on this
                # NewObjectHyp and ObjectDuplicateHypothesis.
                object_persistence_hypothesis = ObjectPersistenceHypothesis(
                    object_ = new_object,
                    new_object_hyp=new_object_hyp,
                    object_dulpicate_hypothesis=object_duplicate_hypothesis)
                
                # Premise both the object duplicate hypothesis and the offscreen
                # object hypothesis on the offscreen persistence hypothesis, as
                # they have no reason for existing without it.
                new_object_hyp.add_premise(object_persistence_hypothesis)
                object_duplicate_hypothesis.add_premise(object_persistence_hypothesis)

                # Make sure to store the new Hypotheses
                new_hypotheses.append(new_object_hyp)
                new_hypotheses.extend(concept_edge_hyps)
                new_hypotheses.append(object_duplicate_hypothesis)
                new_hypotheses.append(object_persistence_hypothesis)
            # end for image in absent_images
        # end for current_object in knowledge_graph.objects.values()
        return new_hypotheses
    # end _hypothesize_object_persistence


    # TODO: Delete this?
    def _generate_action_hypotheses(self, knowledge_graph: KnowledgeGraph):
        """
        Generates hypotheses for unobserved actions.
        """
        # Go through every action.
        # Get the commonsense actions related to each action and object instance
        # This is the basis of our set of possible non-observed actions.
        # Key an Action id. Value is a list of CommonSenseNode objects.
        related_cs_actions = list()
        for node in knowledge_graph.nodes.values():
            # If the node is neither an object nor an action, skip it.
            if not type(node) == Object and not type(node) == Action:
                continue
            
            # Follow action-action and object-action edges in the commonsense
            # data to find related potential new actions.
            for concept in node.concepts:
                for cs_edge in concept.commonsense_edges:
                    # Check if the edge has a relationship that'll lead to
                    # another action.
                    if (type(node) == Object and not cs_edge.relation in 
                        const.OBJECT_ACTION_RELATIONSHIPS):
                        continue
                    elif (type(node) == Action and not cs_edge.relation in
                          const.ACTION_ACTION_RELATIONSHIPS):
                        continue
                    # Get the id of the commonsense node on this edge which is
                    # not one of the Concept's CommonSenseNodes.
                    other_cs_node_id = -1
                    if cs_edge.start_node_id not in concept.commonsense_nodes:
                        other_cs_node_id = cs_edge.start_node_id
                    elif cs_edge.end_node_id not in concept.commonsense_nodes:
                        other_cs_node_id = cs_edge.end_node_id
                    # If both the start and end of the edge lead to concept net
                    # nodes that are represented by this Concept, the edge leads
                    # from the Concept to itself!
                    # Skip this Concept
                    else:
                        continue
                    # end else
                    # Fetch the concept net node itself.
                    other_cs_node = self._commonsense_querier.get_node(
                                                            other_cs_node_id)
                    # If it's of a filtered action, ignore it.
                    # It's a filtered action if at least one of its labels is in
                    # the list of filtered actions defined in constants.
                    if len(set(other_cs_node.labels).intersection(set(const.FILTERED_ACTIONS))) > 0:
                        continue
                    # If it has a part-of-speech, make sure it's a verb.
                    if (hasattr(other_cs_node, 'pos') and
                        not other_cs_node.pos is None 
                        and not other_cs_node.pos == 'v'):
                        # If it has a part of speech that labels it as a noun,
                        # look for a definition from an external source.
                        # Acts are nouns but are still actions.
                        if (hasattr(other_cs_node, 'source_def') and
                            not other_cs_node.source_def is None):
                            if not other_cs_node.source_def == 'act':
                                continue
                            # end if
                        else:
                            continue
                        # end if else
                    # end if
                    # Only add it to the overall list of related conceptnet
                    # actions if it's not already in it.
                    if not other_cs_node in related_cs_actions:
                        related_cs_actions.append(other_cs_node)
                # end for
            # end for
        # end for action in knowledge_graph.actions.values()

        # Now that we have all unique commonsense nodes that are actions related 
        # to existing Instances, make a hypothetical Action out of each concept 
        # net node.
        # Then, make an ActionHypothesis out of each hypothetical Action.
        # Dictionary of ActionHypothesis objects, keyed by hypothesis id.
        action_hypotheses = dict()
        timers = dict()
        timer_sums = dict()
        timer_sums['get or make_concepts'] = 0
        timer_sums['parse potential actions'] = 0
        for cs_action in related_cs_actions:
            timers['action_start'] = timer()
            # Make or get a Concept for this commonsense action.
            concept = knowledge_graph.get_or_make_concept(cs_action,
                                                          ConceptType.ACTION)
            timers['get_or_make_concept_end'] = timer()
            timer_sums['get or make_concepts'] += timers['get_or_make_concept_end'] - timers['action_start']
            # A new action hypothesis will be made for each scene in which
            # this Action is grounded by a conceptually related Instance.
            # Keep track of an action and list of evidence per scene.
            # Keyed by image id.
            new_actions = dict()
            evidence = dict()
            # Go through each of the hypothesized Action's Concept's edges to
            # other Concepts.
            if len(concept.edges) == 0:
                print(f'Error! Concept {concept} has no edges!')
            for edge in concept.edges.values():
                other_concept = edge.get_other_node(concept)
                if not type(other_concept) == Concept:
                    continue
                # Get all instances of the other Concept. These are the existing
                # Instances that might be related to the hypothezied
                # Action through a relationship between their Concepts. 
                instances = knowledge_graph.get_concept_instances(other_concept)
                # Make a piece of ConceptEdgeEvidence for each one. 

                # Organize the instance evidence by image index.
                for instance in instances:
                    # See if there's an Action and Evidence list for this 
                    # Instance's scene yet.
                    if not instance.get_image().id in new_actions:
                        # If not, start a new evidence list and make a new
                        # hypothetical action for this image.
                        new_actions[instance.get_image().id] = Action(
                            label=concept.label, image=instance.get_image(),
                            concepts=[concept], hypothesized=True)
                        evidence[instance.get_image().id] = list()
                    # end if
                    # Make evidence for this conceptually related Instance.
                    new_evidence = None
                    if edge.source == concept:
                        new_evidence = ConceptEdgeEvidence(
                            source_instance=new_actions[instance.get_image().id],
                            target_instance=instance,
                            edge=edge)
                    elif edge.target == concept:
                        new_evidence= ConceptEdgeEvidence(
                            source_instance=instance,
                            target_instance=new_actions[instance.get_image().id],
                            edge=edge)
                    # end elif
                    if new_evidence is None:
                        print(f'Error! Hypothesized action\'s concept was ' +
                              f'neither the source nor the target of its '+
                              f' Concept edge!')
                    evidence[instance.get_image().id].append(new_evidence)
                # end for
            # end for

            for image_id, action in new_actions.items():
                # Make the ActionHypothesis for each new hypothesized Action.
                action_hypothesis = ActionHypothesis(action=action, 
                                    evidence=evidence[instance.get_image().id])
                action_hypotheses[action_hypothesis.id] = action_hypothesis
            # end for

            # DEBUG
            time_taken = timer() - timers["action_start"]
            #if time_taken > 0.1:
            #    print(f'cn action {cn_action.uri}, edges:' + 
            #          f' {len([edge for edge in concept.edges.values() if type(edge.get_other_node(concept)) == Concept])}' +
            #          f' time taken: {time_taken}')
            # end if
            timer_sums['parse potential actions'] += time_taken
            # END DEBUG

        # end for
        print(f'Time spent getting or making concepts: {timer_sums["get or make_concepts"]}')
        print(f'Total time spent parsing potential actions: {timer_sums["parse potential actions"]}')
        # Return all the action hypotheses we made.
        return action_hypotheses
    # end _generate_action_hypotheses

# end class