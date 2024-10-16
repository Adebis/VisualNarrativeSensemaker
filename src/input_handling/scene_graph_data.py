from dataclasses import dataclass, field
from commonsense.commonsense_data import Synset
from typing import Union

import cv2

@dataclass
class Image:
    """
    A class to represent a scene graph's image.

    ...

    Attributes
    ----------
    id : int
        The unique identifier for this image. Corresponds to the image's file
        name without its extension.
    index : int
        The image's place in a sequence of images.
    file_path : str
        The file path to this image's file. 
    matrix : Mat
        The cv2 matrix representation of this Image. Built by this Image after
        it has been initialized with its file path.
    """
    id: int
    index: int
    file_path: str
    matrix: cv2.Mat = field(init=False)

    def __post_init__(self):
        """
        After initialization, gets the cv2 matrix representation for this Image
        from its file.
        """
        self.matrix = cv2.imread(self.file_path)
    # end __post_init__

    def __repr__(self):
        return (f'image {self.id} (index {self.index})')

# end class Image

@dataclass
class BoundingBox:
    """
    A class to represent a bounding box for an image, as listed in its scene 
    graph.

    ...

    Attributes
    ----------
    h : int
        The height of the bounding box, in pixels.
    w: int
        The width of the bounding box, in pixels.
    x : int
        The x-coordinate of the top-left corner of the bounding box.
    y : int
        The y-coordinate of the top-left corner of the bounding box.
    """
    h: int
    w: int
    x: int
    y: int

    def __repr__(self):
        return(f'x: {self.x}, y: {self.y}, w: {self.w}, h: {self.h}')
# end class BoundingBox

@dataclass
class SceneGraphObject:
    """
    A class to keep track of a scene graph object's data.

    Mirrors the format of object entries in scene graph json files.

    Also keeps track of the Image that this scene graph object came from.

    ...

    Attributes
    ----------
    names : list[str]
        The names this object was annotated with.
    synsets : list[Synset]
        The Synsets associated with this object.
    object_id : int
        The integer ID for this object in the scene graph. 
        
        Referenced in other parts of the scene graph's json.
    bounding_box : BoundingBox
        The bounding box for this object. 
        
        Defined by the x and y coordinates of its top-left corner, its height, 
        and its width.
    image : Image
        The Image this scene graph object came from.
    attributes : list[str], optional
        A list of the attributes this object was annotated with.
        
        Objects may not have any attributes in its annotations. The default 
        value is the empty list.
    """
    names: list[str]
    synsets: list[Synset]
    object_id: int
    bounding_box: BoundingBox
    image: Image
    attributes: list[str] = field(default_factory=list)

    def get_matrix(self) -> cv2.Mat:
        """
        Gets the cv2 matrix representation of this scene graph data's bounding
        box by slicing it from its Image.
        """
        box = self.bounding_box
        return self.image.matrix[box.y:box.y + box.h, box.x:box.x + box.w]
    # end get_matrix
# end class SceneGraphObject

@dataclass
class SceneGraphRelationship:
    """
    A class to keep track of a scene graph relationship's data.

    Mirrors the format of relationship entries in scene graph json files.

    Also keeps track of the Image this scene graph relationship came from.

    ...

    Attributes
    ----------
    predicate : str
        The predicate that this relationship is based off of.
    synsets : list[Synset]
        The Synsets associated with this relationship's predicate.
    relationship_id : int
        Unique identifier for this relationship.
    object_id : int
        object_id of the object of this relationship. 
        
        The object is the thing the predicate is being done to.
        
        Corresponds to a scene graph object's object_id.

        If this relationship has no object, object_id is -1.
    subject_id : int
        object_id of the subject of this relationship.

        The subject is the thing doing the predicate.

        Corresponds to a scene graph object's object_id.
    image : Image
        The Image this scene graph relationship came from.
    """
    predicate: str
    synsets: list[Synset]
    relationship_id: int
    object_id: int
    subject_id: int
    image: Image