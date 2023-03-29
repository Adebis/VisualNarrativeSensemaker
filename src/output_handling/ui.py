import sys
import json
import random
import math
import os
import shutil
from timeit import default_timer as timer

from PySide6.QtWidgets import (QLabel, QMainWindow, QWidget, QWidgetAction,
                               QFileDialog, QApplication, QHBoxLayout,
                               QVBoxLayout, QScrollArea, QPushButton,
                               QTextEdit, QMessageBox, QGraphicsScene,
                               QGraphicsView, QInputDialog, QGraphicsPixmapItem,
                               QSplitter, QGraphicsItem, QGraphicsEllipseItem, 
                               QGraphicsSimpleTextItem, QGraphicsLineItem,
                               QGraphicsRectItem)
from PySide6.QtGui import (QAction, QImage, QPixmap, QPalette, QPainter, QColor,
                           QPen, QBrush, QFont, QShortcut, QKeySequence)
from PySide6.QtCore import (QCoreApplication, Qt, Slot, QSize)

from sensemaker import SenseMaker
from input_handling.scene_graph_data import (Image, BoundingBox)
from knowledge_graph.graph import KnowledgeGraph
from knowledge_graph.items import (Node, Concept, Instance, Object, Action, 
                                   Edge)
from hypothesis.hypothesis import Hypothesis


import constants as const

MAX_Z_VALUE = 1000000
MIN_Z_VALUE = -1000000

class MainUI(QMainWindow):
    """
    The program's main GUI controller.
    """
    # UI Contains:
    #   A menu bar
    #   A graphics scene to handle images and 2d shapes
    #   A graphics view to show the graphics scene
    #   A text output
    def __init__(self):
        super(MainUI, self).__init__()

        print("Initializing Main UI")

        # It's considered best practice to set layouts on a central widget
        # instead of on the main window itself.
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Set the initial size for this window
        self.resize(900, 900)

        # Initialize global variables
        self.menu_item_actions = dict()
        self.sensemaker = None
        self.focus_node_item = None

        # Initialize UI variables
        # A scene to show the images and nodes.
        self.image_scene = QGraphicsScene()
        # A view to show the scene.
        self.image_view = QGraphicsView(self.image_scene)
        # Some behaviors for the view
        # When you left click and drag, it scrolls the view.
        #self.image_view.setDragMode(QGraphicsView.ScrollHandDrag)

        # A text edit to display text information and output.
        self.text_output = QTextEdit()
        # Make sure it's set to read-only
        self.text_output.setReadOnly(True)

        # Make the menu bar.
        menu = self.menuBar()
        # Add a file menu to the menu bar.
        file_menu = menu.addMenu("File")
        # Make the menu action to enter run the test set. 
        test_set_act = QAction("Run Test Set", self)
        test_set_act.triggered.connect(self._run_test_set)
        # Set the shortcut to ctrl + t
        test_set_act.setShortcut(QKeySequence("ctrl+t"))
        file_menu.addAction(test_set_act)

        # Make an upper-level vertical layout with a resizeable splitter bar
        # between each element. 
        main_layout = QVBoxLayout(self.centralWidget())

        main_splitter = QSplitter()
        #main_layout.resize(self.size())
        main_splitter.setOrientation(Qt.Vertical)
        main_splitter.addWidget(self.image_view)
        main_splitter.addWidget(self.text_output)

        main_layout.addWidget(main_splitter)

        #self.text_output.setText("Initialization complete.")
        # Automatically run the test set after initialization.
        self._run_test_set()
    # end __init__

    def _run_test_set(self):
        """
        Runs sensemaking on the current test set, defined in this function.
        """
        print("Run test set selected")

        # Set 10
        test_set_ids = [2402873, 2391830, 2406899]

        self.write_output_text(f'Running test set [{test_set_ids[0]}, ' +
                               f'{test_set_ids[1]}, {test_set_ids[2]}]')

        self._run_sensemaking(test_set_ids)
    # end run_test_set

    def _run_sensemaking(self, image_set_ids: list[int]):
        """
        Runs sensemaking on a sequence of images, as specified by their ids.

        Calls draw_scenes after to display the results.
        """
        # Clear the scene to remove all existing items. 
        self.image_scene.clear()
        # Run the sensemaker and get its results.
        # Make a sensemaker and run sensemaking.
        self.sensemaker = SenseMaker()
        results = self.sensemaker.perform_sensemaking(image_set_ids)
        self._draw_scenes(knowledge_graph=results[0],
                          hypotheses=results[1])
    # end run_sensemaking

    # ======= DRAWING FUNCTIONS =======
    def _draw_scenes(self, 
                     knowledge_graph: KnowledgeGraph, 
                     hypotheses: dict[int, Hypothesis]):
        """
        Draws a knowledge graph's nodes and edges on top of the images the
        knowledge graph was made from. 
        """
        print("Drawing scenes")
        # Get the Image objects for all three images.
        # Each contains the path to the image file it came from.
        images_unordered = knowledge_graph.images.values()
        # Order the images by their index, which is their order in the image
        # sequence.
        images_ordered = {image.index: image for image in images_unordered}

        # Make pixmaps for each image in the scene.
        # Store the QGraphicsPixmapItems made after they're added to the scene.
        # Keyed by image id.
        image_pixmaps = dict()
        x_offset = 0
        y_offset = 0
        for index in range(len(images_ordered)):
            image = images_ordered[index]
            print(f'Drawing {image}')
            image_to_draw = QImage(image.file_path)
            # Returns a QGraphicsPixmapItem
            image_pixmap = self.image_scene.addPixmap(
                QPixmap.fromImage(image_to_draw))
            # Place the images behind any other item.
            image_pixmap.setZValue(MIN_Z_VALUE)
            # Offset the image.
            image_pixmap.setPos(x_offset, y_offset)
            # Add this image's width to the x-offset so the next image gets
            # drawn to the right of it.
            x_offset += image_pixmap.pixmap().size().width()
            # If this is an even-numbered image, set the y-offset of the next 
            # image to this image's height so the next image is drawn below it.
            # This will help see edges between nodes of non-adjacent images,
            # since the edges will be drawn over empty space instead of over
            # another image. 
            if index % 2 == 0:
                y_offset = image_pixmap.pixmap().size().height()
            # end if
            # If this is an odd-numbered image, remove the y-offset.
            elif index % 2 == 1:
                y_offset = 0
            # end elif
            image_pixmaps[image.id] = image_pixmap
        # end for

        # Make node graphics items from the knowledge graph.
        node_graphics_items = self._make_node_graphics_items(
            knowledge_graph=knowledge_graph, image_pixmaps=image_pixmaps)
        
        # Add the node graphics items to this scene.
        for node_graphics_item in node_graphics_items:
            self.image_scene.addItem(node_graphics_item)

        # Show the scene.
        self.image_view.show()
    # end draw_scenes

    def _make_node_graphics_items(self, knowledge_graph: KnowledgeGraph, 
                                  image_pixmaps: dict[int, QGraphicsPixmapItem]):
        """
        Make the NodeGraphicsItems for the nodes in the knowledge graph.

        Returns a list of the NodeGraphicsItem that were made.
        """
        node_graphics_items = list()
        # Make NodeGraphicsItems for each Object.
        for object_node in knowledge_graph.objects.values():
            # Make the scene coordinates of the center position the center of 
            # its bounding box, if any, plus its image offset.
            center_pos = (0, 0)
            bounding_box = None
            if not len(object_node.scene_graph_objects) == 0:
                bounding_box = object_node.scene_graph_objects[0].bounding_box
                center_pos = (bounding_box.x + (bounding_box.w/2),
                              bounding_box.y + (bounding_box.h/2))
            # end if
            # Apply the image offset.
            image_pixmap = image_pixmaps[object_node.get_image().id]
            center_pos = (center_pos[0] + image_pixmap.scenePos().x(),
                          center_pos[1] + image_pixmap.scenePos().y())
            radius = 5
            node_graphics_item = NodeGraphicsItem(node=object_node, 
                                                  center_pos=center_pos, 
                                                  radius=radius,
                                                  image_pixmap=image_pixmap)
            node_graphics_items.append(node_graphics_item)
        # end for
        return node_graphics_items
    # end _make_object_graphics_items

    # Write text into the text output label.
    def write_output_text(self, text_in):
        #existing_text = self.text_output_label.text()
        self.text_output.append(text_in)
    # end WriteOutputText

# end class MainUI

class NodeGraphicsItem(QGraphicsEllipseItem):
    """
    A QGraphics item to handle drawing and interacting with a Node in a 
    knowledge graph.

    Attributes
    ----------
    node : Node
        The knowledge graph Node this graphics item represents.
    center_pos : tuple[float, float]
        The scene coordinates of the center of this node as an x, y tuple.
    radius : float
        The radius of this node.
    image_pixmap : QGraphicsPixmapItem | None
        The QGraphicsPixmapImage object of the image this node is associated 
        with, if any. Default value is None.
    """

    def __init__(self, node: Node, center_pos: tuple[float, float], 
                 radius: float, image_pixmap: QGraphicsPixmapItem=None):
        # Get the coordinates of the node's upper-left hand corner, its width,
        # and its height from the coordinates of its center and its radius.
        super().__init__(center_pos[0] - radius, center_pos[1] - radius, 
                         radius*2, radius*2)
        self.node = node
        self.center_pos = center_pos
        self.radius = radius
        self.image_pixmap = image_pixmap

        # Internal variables
        # The node's child text item.
        self._text_item = None
        # The node's associated bounding box item, which is going to be a child
        # of its image_pixmap item.
        self._bounding_box_item = None

        self.setAcceptHoverEvents(True)
        self.setFlags(QGraphicsItem.ItemIsMovable | 
                      QGraphicsItem.ItemIsSelectable)

        self._initialize_colors()
        self._initialize_text()
        # If this is an Object node with a bounding box and an image pixmap, 
        # initialize a bounding box item.
        if (type(self.node) == Object 
            and not len(self.node.scene_graph_objects) == 0
            and not self.image_pixmap is None):
            bounding_box = self.node.scene_graph_objects[0].bounding_box
            self._initialize_bounding_box(bounding_box)
        # end if

        self._color_default()
    # end __init__

    # Decide the node's colors based on its type. 
    def _initialize_colors(self):
        """
        Initialize the brushes and pens that control this node's colors.
        """
        self._default_brush = QBrush(QColor('transparent'))
        self._default_pen = QPen(QColor('gray'))

        self._highlight_brush = QBrush(QColor('black'))
        self._highlight_pen = QPen(QColor('white'))

        self._text_brush = QBrush(QColor('white'))
        self._text_pen = QPen(QColor('black'))
        #self.text_pen.setWidth(1)
        self._bounding_box_brush = QBrush(QColor('transparent'))
        self._bounding_box_pen = QPen(QColor('white'))
    # end _initialize_colors

    def _initialize_text(self):
        """
        Initialize this node's text item child. 
        """
        # The text's font
        text_font = QFont('Helvetica', pointSize=15)
        # Make a child text object for this node.
        self._text_item = QGraphicsSimpleTextItem(self.node.name, self)
        self._text_item.setFont(text_font)
        self._text_item.setPos(self.scenePos().x() -10, self.scenePos().y() -20)
        # Make sure it's always drawn on top of any other item.
        # A higher Z-value item is always drawn on top of a lower Z-value item.
        self._text_item.setZValue(MAX_Z_VALUE)
        # Adopt the default color.
        self._text_item.setBrush(self._text_brush)
        if not self._text_pen is None:
            self._text_item.setPen(self._text_pen)
        # Hide it initially.
        self._text_item.setVisible(False)
    # end initialize_text

    def _initialize_bounding_box(self, bounding_box: BoundingBox):
        """
        Initialize this node's bounding box item.
        """
        # Make the bounding box and parent it to this node's image pixmap.
        self._bounding_box_item = QGraphicsRectItem(bounding_box.x,
                                                    bounding_box.y,
                                                    bounding_box.w,
                                                    bounding_box.h,
                                                    self.image_pixmap)
        self._bounding_box_item.setVisible(False)

        QGraphicsItem.ItemSceneChange
    # end set_bounding_box_item

    def _color_default(self):
        # Color the node its default color.
        self.setBrush(self._default_brush)
        self.setPen(self._default_pen)

        # Color the text as well.
        if not self._text_item is None:
            self._text_item.setBrush(self._text_brush)
            if not self._text_pen is None:
                self._text_item.setPen(self._text_pen)
            # end if
        # end if
        # Color the bounding box.
        if not self._bounding_box_item is None:
            self._bounding_box_item.setBrush(self._bounding_box_brush)
            self._bounding_box_item.setPen(self._bounding_box_pen)
        # end if
    # end _color_default

    def _color_highlight(self):
        # Color the node its highlight color.
        self.setBrush(self._highlight_brush)
        self.setPen(self._highlight_pen)
    # end _color_highlight

    # Handle the mouse hovering over this node. 
    def hoverEnterEvent(self, event):
        #print("mouse hover enter event: " + str(event))
        # Highlight this node.
        self._color_highlight()
        # Reveal the text and bounding box.
        self._text_item.setVisible(True)
        if not self._bounding_box_item is None:
            self._bounding_box_item.setVisible(True)
    # end hoverEnterEvent

    # Handle the mouse hovering out of this node.
    def hoverLeaveEvent(self, event):
        #print("mouse hover leave event: " + str(event))
        # Unhighlight this node.
        self._color_default()
        # Hide the text and bounding box.
        self._text_item.setVisible(False)
        if not self._bounding_box_item is None:
            self._bounding_box_item.setVisible(False)
    # end hoverLeaveEvent

    # Handle the mouse clicking on this node.
    # Flip this node's focus toggle, which prevents its edges from
    # un-highlighting.
    # It also flips this node's highlight toggle, which prevents itself from
    # un-highlighting.
    # Propagates the highlight toggle and untoggling
    # to all connected edges, which them spread them to all connected nodes.
    def mousePressEvent(self, event):
        print("mouse press event: " + str(event))
    # end mousePressEvent

    # ====== END EVENT HANDLERS ======
        
# end class NodeGraphicsItem

# A class representing the graphical line for a single knowledge graph edge.
class EdgeGraphicsItem(QGraphicsLineItem):

    def __init__(self):
        print('hey :)')

# end class EdgeGraphicsItem