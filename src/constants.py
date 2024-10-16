from enum import Enum

# The system's constants.
# This includes mappings and definitions, as well as paths and directories.

# An enum for concept types.
class ConceptType(Enum):
    OBJECT = 'OBJECT'
    ACTION = 'ACTION'
# end class ConceptType
    
# An enum for causal flow directions.
class CausalFlowDirection(Enum):
    FORWARD = 'FORWARD'
    BACKWARD = 'BACKWARD'
    NEUTRAL = 'NEUTRAL'
    NONE = 'NONE'

    @classmethod
    def reverse(cls, causal_flow_direction):
        '''
        Returns the reverse of a causal flow direction.
        '''

        if causal_flow_direction == cls.FORWARD:
            return cls.BACKWARD
        elif causal_flow_direction == cls.BACKWARD:
            return cls.FORWARD
        else:
            return cls.NONE
    # end reverse

# end class CausalFlowDirection

# The directory of all of this project's data files.
DATA_DIRECTORY = 'data'
# The directory of this project's input files.
INPUT_DIRECTORY = (f'{DATA_DIRECTORY}/inputs')
# The directory of this project's scene graph annotation files.
ANNOTATIONS_DIRECTORY = (f'{INPUT_DIRECTORY}/scene_graphs')
# The directory of this project's scene graph image files.
IMAGES_DIRECTORY = (f'{INPUT_DIRECTORY}/images')
# The directory of this project's output files.
OUTPUT_DIRECTORY = (f'{DATA_DIRECTORY}/outputs')

# The file path to this project's concepts database file.
DATABASE_FILE_PATH = (f'{DATA_DIRECTORY}/commonsense_knowledge.db')
# Absolute path version
#DATABASE_FILE_PATH = ('C:/Users/zevsm/Documents/GitHub/VisualNarrativeSensemaker/data/commonsense_knowledge.db')

# Intersection Over Union threshold.
# For determining bounding-box overlap.
IOU_THRESHOLD = 0.5

# The focal score given to focal nodes in scene graphs.
DEFAULT_FOCAL_SCORE = 8.0

# How much Instance Centrality decays every time it is propagated.
CENTRALITY_DECAY = 0.5

# How much we offset hypothesis scores by to ensure it does or does not appear
# with another hypothesis in MWIS calculations.
# 10 million
H_SCORE_OFFSET = 10000000.0

# Actions the system should ignore.
FILTERED_ACTIONS = ["sit", "attach", "be", "have", "keep", "wear", "stand", 
                    "approach", "in", "along"]
# FILTERED_ACTIONS = ["sit", "attach", "be", "have", "keep", "wear", "approach"]

# Objects the system should ignore.
FILTERED_OBJECTS = ["hand", "head", "hair", "eyelid", "suit",
                    "shirt", "glove", "clothing", "sunglasses", "short_pants",
                    "wheel", "eye", "nose", "mouth", "ear", "backpack", "hat",
                    "paw", "tooth", "pad", "leg", "tongue", "tail", "lip",
                    "haunch", "arm", "part", "face", "cap", "belt", "knee",
                    "spectacles"]

# Attributes which describe the color of an object.
COLOR_ATTRIBUTES = ["green", "grey", "gray", "white", "orange", "brown",
                    "black", "red", "blue", "greenish", "yellow", "silver",
                    "pink", "gold", "beige", ]

# ConceptNet relationships that indicate a relationship between an action and
# another action.
ACTION_ACTION_RELATIONSHIPS = ["/r/HasSubevent",
                               "/r/Causes",
                               "/r/HasFirstSubevent",
                               "/r/HasLastSubevent",
                               "/r/HasPrerequisite",
                               "/r/ObstructedBy",
                               "/r/MotivatedByGoal",
                               "/r/CausesDesire"]

# ConceptNet relationships that indicate a relationship between an object and
# an action.
OBJECT_ACTION_RELATIONSHIPS = ["/r/Causes",
                               "/r/ReceivesAction",
                               "/r/CapableOf",
                               "/r/ObstructedBy"]


# A mapping of conceptnet relationship types to
# Narrative Coherence elements.
COHERENCE_TO_RELATIONSHIP = dict()
COHERENCE_TO_RELATIONSHIP["referential"] = ["IsA", "PartOf", "HasA",
                                            "DefinedAs", "MannerOf"]
COHERENCE_TO_RELATIONSHIP['causal'] = ["Causes",
                                       "HasFirstSubevent",
                                       "HasLastSubevent", "HasPrerequisite",
                                       "CausesDesire"]

# Removed from causal:
#   MotivatedByGoal - inconsistent use in ConceptNet; sometimes the cause of
#   something is listed as the goal that's motivating something.
#   E.g., drink water -> motivated by goal -> parched.
#   HasSubevent - unlcear whether the subevent happens before or after the
#   action in question.
#   e.g. drink -> HasSubevent -> open mouth, open mouth should happen before.
#   drink -> HasSubevent -> quench_thirst, quench_thirst should happen after.

# Which direction the flow of events for each causal relationship
# is; either forward, from source to target, e.g. the source must have happened
# first before the target, or backward, from target to source, e.g. the target
# must have happened first before the source.
CAUSAL_RELATIONSHIP_DIRECTION = dict()
CAUSAL_RELATIONSHIP_DIRECTION["Causes"] = CausalFlowDirection.FORWARD
#CAUSAL_RELATIONSHIP_DIRECTION["HasSubevent"] = CausalFlowDirection.FORWARD
CAUSAL_RELATIONSHIP_DIRECTION["HasFirstSubevent"] = CausalFlowDirection.BACKWARD
CAUSAL_RELATIONSHIP_DIRECTION["HasLastSubevent"] = CausalFlowDirection.FORWARD
CAUSAL_RELATIONSHIP_DIRECTION["HasPrerequisite"] = CausalFlowDirection.BACKWARD
#CAUSAL_RELATIONSHIP_DIRECTION["ReceivesAction"] = CausalFlowDirection.BACKWARD
#CAUSAL_RELATIONSHIP_DIRECTION["MotivatedByGoal"] = CausalFlowDirection.FORWARD
#CAUSAL_RELATIONSHIP_DIRECTION["Desires"] = CausalFlowDirection.FORWARD
CAUSAL_RELATIONSHIP_DIRECTION["CausesDesire"] = CausalFlowDirection.FORWARD
# Removed from causal: UsedFor, CapableOf, CreatedBy
# Moved from Affective to Causal: MotivatedByGoal, Desires, CausesDesire
#COHERENCE_TO_RELATIONSHIP["affective"] = ["MotivatedByGoal", "ObstructedBy",
#                                    "Desires", "CausesDesire"]
COHERENCE_TO_RELATIONSHIP["affective"] = ["Desires", "MotivatedByGoal", "ObstructedBy"]
COHERENCE_TO_RELATIONSHIP["spatial"] = ["AtLocation", "LocatedNear"]
COHERENCE_TO_RELATIONSHIP["other"] = ["UsedFor", "CapableOf", "CreatedBy"]
RELATIONSHIP_TO_COHERENCE = dict()
for coherence, cn_rel_list in COHERENCE_TO_RELATIONSHIP.items():
    for cn_rel in cn_rel_list:
        RELATIONSHIP_TO_COHERENCE[cn_rel] = coherence
    # end for
# end for

