from enum import Enum

# The system's constants.
# This includes mappings and definitions, as well as paths and directories.

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

# Intersection Over Union threshold.
# For determining bounding-box overlap.
IOU_THRESHOLD = 0.5

# The focal score given to focal nodes in scene graphs.
DEFAULT_FOCAL_SCORE = 8.0

# How much Instance Centrality decays every time it is propagated.
CENTRALITY_DECAY = 0.5

# How much we offset hypothesis scores by to ensure it does or does not appear
# with another hypothesis in MWIS calculations.
H_SCORE_OFFSET = 1000.0

# Actions the system should ignore.
FILTERED_ACTIONS = ["sit", "attach", "be", "have", "keep", "wear"]

# Objects the system should ignore.
FILTERED_OBJECTS = ["hand", "head", "hair", "eyelid", 
                    "shirt", "glove", "clothing", "sunglasses", "short_pants",
                    "wheel"]

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
COHERENCE_TO_RELATIONSHIP["causal"] = ["Causes",
                                       "HasSubevent", "HasFirstSubevent",
                                       "HasLastSubevent", "HasPrerequisite",
                                       "ReceivesAction",
                                       "MotivatedByGoal",
                                       "Desires",
                                       "CausesDesire"]
# Removed from causal: UsedFor, CapableOf, CreatedBy
# Moved from Affective to Causal: MotivatedByGoal, Desires, CausesDesire
#COHERENCE_TO_RELATIONSHIP["affective"] = ["MotivatedByGoal", "ObstructedBy",
#                                    "Desires", "CausesDesire"]
COHERENCE_TO_RELATIONSHIP["affective"] = ["ObstructedBy"]
COHERENCE_TO_RELATIONSHIP["spatial"] = ["AtLocation", "LocatedNear"]
COHERENCE_TO_RELATIONSHIP["other"] = ["UsedFor", "CapableOf", "CreatedBy"]
RELATIONSHIP_TO_COHERENCE = dict()
for coherence, cn_rel_list in COHERENCE_TO_RELATIONSHIP.items():
    for cn_rel in cn_rel_list:
        RELATIONSHIP_TO_COHERENCE[cn_rel] = coherence
    # end for
# end for

# An enum for concept types.
class ConceptType(Enum):
    OBJECT = 'OBJECT'
    ACTION = 'ACTION'
# end class ConceptType