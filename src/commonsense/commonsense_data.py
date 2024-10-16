from dataclasses import dataclass, field
from enum import Enum
from typing import Union

@dataclass
class Synset:
    """
    A class to represent a synset. 
    
    ...

    Attributes
    ----------
    name : str
        The full text for the synset. Recognizable by NLTK WordNet.

        Has the format {word}.{pos}.{sense}. 
        
        i.e. dog.n.01
    word : str
        The word this synset represents.
    pos : str
        The part-of-speech for this synset.
    sense : str
        The sense for this synset.

        Synsets can have multiple senses. Each one is indicated by a two-digit
        number stored as a string, e.g. '01', '02'.
    
    Methods
    -------
    __repr__():
        Returns the NLTK-recognizable full text for this synset in the format
        {word}.{pos}.{sense}

        i.e. dog.n.01
    """
    name: str
    word: str = field(init=False)
    pos: str = field(init=False)
    sense: str = field(init=False)

    def __post_init__(self):
        """
        Parses the synset's attributes using the name of the synset, which is in 
        the format {word}.{pos}.{sense}.
        """
        self.word = self.name.split('.')[0]
        self.pos = self.name.split('.')[1]
        self.sense = self.name.split('.')[2]
    # end __post_init__

    def __repr__(self):
        """
        Returns the name of this synset, as recognizable in NLTK's WordNet.

        Has the format {word}.{pos}.{sense}, e.g. dog.n.01

        This representation is unique for all synsets.
        """
        return self.name
    # end __repr__

    def __eq__(self, __o: object):
        """
        Synsets are considered equal if their names are equal.
        """
        if __o == None:
            return False
        if not type(__o) == Synset:
            return False
        if self.name == __o.name:
            return True
        else:
            return False
    # end __eq__
# end class Synset

@dataclass
class CommonSenseNode:
    """
    Base class for a node in the commonsense database.

    Holds information from a node's entry in the commonsense_database, as well
    as a list of the ids of the commonsense edges incident on this node.

    Subclass implementations should have additional data specific to a specific
    commonsense knowledge source.

    ...

    Attributes
    ----------
    id : int
        The node's integer id. Matches the id column for the node's row in one 
        of the commonsense database tables.
    uri : str
        The node's uri. Matches the uri column for the node's row in one
        of the commonsense database tables.
    labels : list[str]
        A list of the terms this node represents. Each may be a single word or
        a multi-word phrase. 
    edge_ids : set[int]
        A set of the ids of the CommonSenseEdges incident on this node. ids 
        match the ids of those edges in the commonsense_database.

        Default value is the empty set.
    """
    id: int
    uri: str
    labels: list[str]
    edge_ids: set[int]

    def __init__(self, id: int, uri: str, labels: list[str], 
                 edge_ids: set[int]):
        self.id = id
        self.uri = uri
        self.labels = labels
        self.edge_ids = edge_ids
    # end __init__

    def __repr__(self):
        """
        A CommonSenseNode is represented by its uri string, which should be
        unique.
        """
        return self.uri
    # end __repr__

    def __eq__(self, __obj):
        """
        Two CommonSenseNodes are equal if their ids are equal.
        """
        if not type(__obj) == CommonSenseNode:
            return False
        elif self.id == __obj.id:
            return True
        else:
            return False
    # end __eq__
# end class CommonSenseNode

@dataclass
class CommonSenseEdge:
    """
    Base class for an edge in the commonsense database.

    Holds information from an edge's entry in the commonsense_database.
    ...

    Attributes
    ----------
    id : int
        The edge's integer id.
    uri : str
        The uri string for this edge.
    labels : list[str]
        A list of the terms this edge's relationship represents. Each may be a 
        single word or a multi-word phrase.
    relation : str
        The full string for the relation this edge represents. Includes uri
        decorators such as /r/ or fe:
    start_node_id : int
        The id of the node at the end of the edge. 
    end_node_id : int
        The id of the node at the start of the edge.
    start_node_uri : str
        The uri of the node at the start of the edge.
    end_node_uri : str
        The uri of the node at the end of the edge.
    weight : float
        The weight of the edge.
    dimension : str
        The dimension column. An abstract knowledge type for the relation,
        e.g. spatial, from 13 predefined categories. Can have multiple values
        separated by '|' and be empty. Default value is None.
    source : str
        Which knowledge source this edge came from. Can have multiple values
        separated by '|' and be empty. Default value is None.
    sentence : str
        The sentence that the edge was derived from. Can have multiple values
        separated by '|' and be empty. Default value is None. 
    """
    id: int
    uri: str
    labels: list[str]
    relation: str
    start_node_id: int
    end_node_id: int
    start_node_uri: str
    end_node_uri: str
    weight: float
    dimension: str = field(default=None)
    source: str = field(default=None)
    sentence: str = field(default=None)

    def __eq__(self, __o):
        """
        Two edges are equal if their ids are equal.
        """
        if not type(__o) == CommonSenseEdge:
            return False
        if self.id == __o.id:
            return True
        return False
    # end __eq__
    
    def get_other_node_id(self, node_id: int) -> Union[int, None]:
        """
        If the node id passed in matches one of the node ids in this edge,
        returns the non-matching node's id (i.e. the id of the node on the
        other side of this edge).

        Otherwise, returns None.
        """
        if self.start_node_id == node_id:
            return self.end_node_id
        elif self.end_node_id == node_id:
            return self.start_node_id
        else:
            return None
    # end get_other_node_id

    def get_relationship(self) -> str:
        """
        Get the relationship this edge represents from its URI.
        """
        # ConceptNet relation URIs are in the form /r/{RelationshipName},
        # e.g. /r/IsA
        # Split by forward-slash and get the third element.
        relation_split = self.relation.split('/')
        return self.relation.split('/')[2] if len(relation_split) >= 2 else ''
    # end get_relationship

    def __repr__(self):
        return self.uri
    # end __repr__

# end class CommonSenseEdge

@dataclass
class ConceptNetNode(CommonSenseNode):
    """
    A node from the ConceptNet dataset.

    Holds attributes parsed from the node's uri.

    ...

    Attributes
    ----------
    language : str
        The node's language as its two-letter version. Should be en for the most
        part, since we're filtering non-en out when building the database. 
    pos : str
        The node's term's part-of-speech. Not present in every node. Default
        value is None. 
    source : str
        The source that the data for this node came from. Concept net node
        uris sometimes include the dataset it was sourced from, such as
        Wiktionary or WordNet. 
        
        Not present in every node. Default value is None.
    source_def : str
        The definition for this node from its source. If a concept net node
        lists its source in its uri, it's always followed by a definition from
        its source. The exact nature of the definition depends on the source.
        
        Not present in every node. Default value is None.
    """
    language: str = field(init=False)
    pos: str = field(init=False, default=None)
    source: str = field(init=False, default=None)
    source_def: str = field(init=False, default=None)

    def __post_init__(self):
        """
        Parses attributes from the node's uri.
        """
        # ConceptNet derived URIs are separated by forward slashes.
        # ConceptNet uris look like this: /c/en/dog/n/wn/animal
        # Try to split by forward-slash.
        uri_split = self.uri.split('/')
        # In the split, the indices are:
        #   0: nothing | 1: c, indiciating it's a concept | 2: language
        #   3: label | 4: pos | 5: source | 6: source_def
        # Not all nodes have the attributes after the main label, dog.
        if len(uri_split) > 1:
            self.language = uri_split[2]
            if len(uri_split) >= 5:
                self.pos = uri_split[4]
            if len(uri_split) >= 6:
                self.source = uri_split[5]
            if len(uri_split) >= 7:
                self.source_def = uri_split[6]
        # end if
    # end __init__

    def __repr__(self):
        return super().__repr__()
# end class ConceptNetNode

@dataclass 
class AtomicNode(CommonSenseNode):
    """
    A node from the ATOMIC dataset.
    """
# end class AtomicNode

class FrameNetType(Enum):
    """
    FrameNet node types.
    """
    FRAME = 'FRAME'
    FRAME_ELEMENT = 'FRAME_ELEMENT'
    LEXICAL_UNIT = 'LEXICAL_UNIT'
    SEMANTIC_TYPE = 'SEMANTIC_TYPE'
# end class ConceptType

@dataclass
class FrameNetNode(CommonSenseNode):
    """
    A node from the FrameNet dataset.

    Attributes
    ----------
    frame_net_type : FrameNetType
        What type of Node this is in FrameNet, as enumerated in FrameNetType.
        Default value is FRAME.
    """
    frame_net_type: FrameNetType = field(init=False, default=FrameNetType.FRAME)

    def __post_init__(self):
        """
        Parses this node's FrameNetType from its uri.
        """
        # Framenet uris look like this: fn:fe:{label}
        # Frames only have fn:{label}
        uri_split = self.uri.split(':')
        if len(uri_split) == 2:
            self.frame_net_type = FrameNetType.FRAME
        elif len(uri_split) >= 3:
            if uri_split[1] == 'fe':
                self.frame_net_type = FrameNetType.FRAME_ELEMENT
            elif uri_split[1] == 'lu':
                self.frame_net_type = FrameNetType.LEXICAL_UNIT
            elif uri_split[1] == 'st':
                self.frame_net_type = FrameNetType.SEMANTIC_TYPE
        else:
            print(f'FrameNetNode.__post_init__ : Error! Could not find ' + 
                  f'FrameNetType for FrameNetNode {self.uri}')
    # end __post_init__

# end class FrameNetNode

@dataclass
class WordNetNode(CommonSenseNode):
    """
    A node from the WordNet dataset.

    Attributes
    ----------
    synset_text : str
        The full text for this wordnet entry's synset.
    word : str
        The synset word.
    pos : str
        The synset's part-of-speech.
    num : str
        The synset's two-digit number.
    """

    synset_text: str = field(init=False)
    word: str = field(init=False)
    pos: str = field(init=False)
    num: str = field(init=False)

    def __post_init__(self):
        """
        Parses the WordNetNode's synset information from its uri.
        """
        # WordNet uris look like this: wn:frisbee.n.01
        self.synset_text = self.uri.split(':')[1]
        synset_split = self.synset_text.split('.')
        self.word = synset_split[0]
        self.pos = synset_split[1]
        self.num = synset_split[2]
    # end __post_init__