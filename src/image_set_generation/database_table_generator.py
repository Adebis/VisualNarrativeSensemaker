import pickle
import os
import sys
import sqlite3
from sqlite3 import Error
from timeit import default_timer as timer

from commonsense.cskg_querier import CSKGQuerier
from commonsense.commonsense_data import CommonSenseNode
from input_handling.scene_graph_reader import SceneGraphReader

from constants import CausalFlowDirection
import constants as const


class DatabaseTableGenerator:
    '''
    Class to encapsulate database table generation functionality.
    '''

    def __init__(self, commonsense_querier: CSKGQuerier, 
        scene_graph_reader: SceneGraphReader, database_file_path: str,
        images_directory: str):
        print('Initializing database table generator')
        self._commonsense_querier = commonsense_querier
        self._scene_graph_reader = scene_graph_reader
        self._database_file_path = database_file_path
        self._images_directory = images_directory
    # end __init__

    # Table generation

    def generate_database_tables(self):
        '''
        Generates image_objects, image_actions, image_action_object_pairs,
        action_cs_nodes, and object_cs_nodes database tables.
        '''
        print('Generating database tables...')

        start_time = timer()

        # Create the tables.
        # image_objects
        query = ('''
            CREATE TABLE IF NOT EXISTS image_objects
            (image_id INTEGER NOT NULL,
             object_instance_id INTEGER,
             object_instance_name TEXT,
             object_concept_id INTEGER,
             object_concept_name TEXT,
             bbox_x INTEGER,
             bbox_y INTEGER,
             bbox_h INTEGER,
             bbox_w INTEGER,
             attributes TEXT)
        ''')
        self._execute_query(query)
        # Index on image_id, object_instance_id, and object_concept_id.
        query = ('''
                 CREATE INDEX IF NOT EXISTS image_objects_image_id_index
                 ON image_objects (image_id)
                 ''')
        self._execute_query(query)
        query = ('''
                 CREATE INDEX IF NOT EXISTS image_objects_object_instance_id_index
                 ON image_objects (object_instance_id)
                 ''')
        self._execute_query(query)
        query = ('''
                 CREATE INDEX IF NOT EXISTS image_objects_object_concept_id_index
                 ON image_objects (object_concept_id)
                 ''')
        self._execute_query(query)

        # image_actions
        query = ('''
            CREATE TABLE IF NOT EXISTS image_actions
            (image_id INTEGER NOT NULL,
             action_instance_id INTEGER,
             action_instance_name TEXT,
             action_concept_id INTEGER,
             action_concept_name TEXT)
        ''')
        self._execute_query(query)
        # Index on image_id, action_instance_id, and action_concept_id.
        query = ('''
                 CREATE INDEX IF NOT EXISTS image_actions_image_id_index
                 ON image_actions (image_id)
                 ''')
        self._execute_query(query)
        query = ('''
                 CREATE INDEX IF NOT EXISTS image_actions_action_instance_id_index
                 ON image_actions (action_instance_id)
                 ''')
        self._execute_query(query)
        query = ('''
                 CREATE INDEX IF NOT EXISTS image_actions_action_concept_id_index
                 ON image_actions (action_concept_id)
                 ''')
        self._execute_query(query)

        # object_cs_nodes
        query = ('''
            CREATE TABLE IF NOT EXISTS object_cs_nodes
            (object_concept_id INTEGER NOT NULL,
             object_concept_name TEXT,
             cs_node_id INTEGER,
             cs_node_uri TEXT)
        ''')
        self._execute_query(query)
        # Index on object_concept_id and cs_node_id.
        query = ('''
                 CREATE INDEX IF NOT EXISTS object_cs_nodes_object_concept_id_index
                 ON object_cs_nodes (object_concept_id)
                 ''')
        self._execute_query(query)
        query = ('''
                 CREATE INDEX IF NOT EXISTS object_cs_nodes_cs_node_id_index
                 ON object_cs_nodes (cs_node_id)
                 ''')
        self._execute_query(query)

        # action_cs_nodes
        query = ('''
            CREATE TABLE IF NOT EXISTS action_cs_nodes
            (action_concept_id INTEGER NOT NULL,
             action_concept_name TEXT,
             cs_node_id INTEGER,
             cs_node_uri TEXT)
        ''')
        self._execute_query(query)
        # Index on action_concept_id and cs_node_id.
        query = ('''
                 CREATE INDEX IF NOT EXISTS action_cs_nodes_action_concept_id_index
                 ON action_cs_nodes (action_concept_id)
                 ''')
        self._execute_query(query)
        query = ('''
                 CREATE INDEX IF NOT EXISTS action_cs_nodes_cs_node_id_index
                 ON action_cs_nodes (cs_node_id)
                 ''')
        self._execute_query(query)

        # image_action_object_pairs
        query = ('''
                 CREATE TABLE IF NOT EXISTS image_action_object_pairs
                 (image_id INTEGER NOT NULL, 
                  action_instance_id INTEGER,
                  action_instance_name TEXT,
                  object_instance_id INTEGER,
                  object_instance_name TEXT,
                  object_role TEXT,
                  action_concept_id INTEGER,
                  object_concept_id INTEGER)
        ''')
        self._execute_query(query)
        # Index on image_id, action_instance_id, object_instance_id, 
        # action_concept_id, and object_concept_id
        query = ('''
                 CREATE INDEX IF NOT EXISTS image_action_object_pairs_image_id_index
                 ON image_action_object_pairs (image_id)
                 ''')
        self._execute_query(query)
        query = ('''
                 CREATE INDEX IF NOT EXISTS image_action_object_pairs_action_instance_id_index
                 ON image_action_object_pairs (action_instance_id)
                 ''')
        self._execute_query(query)
        query = ('''
                 CREATE INDEX IF NOT EXISTS image_object_action_pairs_object_instance_id_index
                 ON image_action_object_pairs (object_instance_id)
                 ''')
        self._execute_query(query)
        query = ('''
                 CREATE INDEX IF NOT EXISTS image_object_action_pairs_action_concept_id_index
                 ON image_action_object_pairs (action_concept_id)
                 ''')
        self._execute_query(query)
        query = ('''
                 CREATE INDEX IF NOT EXISTS image_object_action_pairs_object_concept_id_index
                 ON image_action_object_pairs (object_concept_id)
                 ''')
        self._execute_query(query)

        # object_cs_nodes
        query = ('''
                 CREATE TABLE IF NOT EXISTS object_cs_nodes
                 (object_concept_id INTEGER, 
                  object_concept_name TEXT,
                  cs_node_id INTEGER,
                  cs_node_uri TEXT)
                 ''')
        self._execute_query(query)
        # Index on object concept id and cs node id.
        query = ('''
                 CREATE INDEX IF NOT EXISTS object_cs_nodes_object_concept_id_index
                 ON object_cs_nodes (object_concept_id)
                 ''')
        self._execute_query(query)
        query = ('''
                 CREATE INDEX IF NOT EXISTS object_cs_nodes_cs_node_id_index
                 ON object_cs_nodes (cs_node_id)
                 ''')
        self._execute_query(query)

        # action_cs_nodes
        query = ('''
                 CREATE TABLE IF NOT EXISTS action_cs_nodes
                 (action_concept_id INTEGER, 
                  action_concept_name TEXT,
                  cs_node_id INTEGER,
                  cs_node_uri TEXT)
                 ''')
        self._execute_query(query)
        # Index on action concept id and cs node id.
        query = ('''
                 CREATE INDEX IF NOT EXISTS action_cs_nodes_action_concept_id_index
                 ON action_cs_nodes (action_concept_id)
                 ''')
        self._execute_query(query)
        query = ('''
                 CREATE INDEX IF NOT EXISTS action_cs_nodes_cs_node_id_index
                 ON action_cs_nodes (cs_node_id)
                 ''')
        self._execute_query(query)

        # For each image, get its actions and its objects.
        # self._get_image_action_object_pairs()
        image_ids = self._get_all_image_ids()
        #image_ids = image_ids[image_count_start:image_count_end]

        # Batch the writes according to this batch size.
        batch_size = 1000
        # Every batch for the same table will use the same query string.
        image_objects_query_string = ('''
            INSERT INTO image_objects
            (image_id, object_instance_id, object_instance_name, 
             object_concept_id, object_concept_name, bbox_x, bbox_y, 
             bbox_h, bbox_w, attributes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''')
        image_actions_query_string = ('''
            INSERT INTO image_actions
            (image_id, action_instance_id, action_instance_name,
             action_concept_id, action_concept_name)
            VALUES(?, ?, ?, ?, ?)
        ''')
        image_action_object_pairs_query_string = ('''
            INSERT INTO image_action_object_pairs 
            (image_id, action_instance_id, action_instance_name, 
             object_instance_id, object_instance_name, object_role,
             action_concept_id, object_concept_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''')
        object_cs_nodes_query_string = ('''
            INSERT INTO object_cs_nodes 
            (object_concept_id, object_concept_name, cs_node_id, cs_node_uri)
            VALUES (?, ?, ?, ?)
            ''')
        action_cs_nodes_query_string = ('''
            INSERT INTO action_cs_nodes 
            (action_concept_id, action_concept_name, cs_node_id, cs_node_uri)
            VALUES (?, ?, ?, ?)
            ''')
        # Keep separate batch data for each table.
        image_objects_batch_data = list()
        image_actions_batch_data = list()
        image_action_object_pairs_batch_data = list()
        object_cs_nodes_batch_data = list()
        action_cs_nodes_batch_data = list()

        print('Reading scene graphs...')
        # Keep overall dictionaries of:
        #   action_concept_names to action_concept_ids
        #   action_concept_ids to lists of cs nodes
        #   object_concept_names to object_concept_ids
        #   object_concept_ids to lists of cs nodes
        action_concept_names_to_ids = dict()
        object_concept_names_to_ids = dict()
        image_counter = 1

        # Use these counters to give object and action concepts unique ids.
        object_concept_counter = 0
        action_concept_counter = 0

        # Use these counters to give object and action instances unique ids.
        object_instance_counter = 0
        action_instance_counter = 0

        # Use these counters for execution info.
        action_object_pairs_counter = 0
        image_objects_write_counter = 0
        image_actions_write_counter = 0
        image_action_object_pairs_write_counter = 0
        object_cs_nodes_write_counter = 0
        action_cs_nodes_write_counter = 0

        # DEBUG
        #image_ids = [2358324, 2413182]

        # Go through every image.
        # For each image, get its actions and objects.
        # For each action or object, get its concept name by taking its node
        # label.
        # Try to get an id for that concept.
        for image_id in image_ids:
            # For this image, keep dictionaries of:
            #   node_ids to object_instance_ids
            #   node_ids to action_instance_ids
            node_ids_to_object_instance_ids = dict()
            node_ids_to_action_instance_ids = dict()

            # Get all of the image's actions and objects.
            knowledge_graph = self._scene_graph_reader.read_scene_graphs([image_id])
            objects = knowledge_graph.objects
            actions = knowledge_graph.actions

            # Build batch data for each table.

            # image_objects
            # The data we need for a single image_objects row is:
            #   image_id, object_instance_id, object_instance_name,
            #   object_concept_id, object_concept_name, bbox_x, bbox_y,
            #   bbox_h, bbox_w, attributes.
            for node_id, object_ in objects.items():
                # Get the object concept name and id.
                # The concept_name is the label of the node.
                object_concept_name = object_.label
                # See if this concept already exists. If not, give it an
                # id and gather its cs nodes.
                if not object_concept_name in object_concept_names_to_ids:
                    object_concept_names_to_ids[object_concept_name] = object_concept_counter
                    object_concept_counter += 1
                    # Since this is a new object concept, gather its cs nodes
                    # and make batch data for the object_cs_nodes table.
                    object_cs_nodes: list[CommonSenseNode] = list()
                    for concept in object_.concepts:
                        for cs_node in concept.commonsense_nodes.values():
                            object_cs_nodes.append(cs_node)
                        # end for
                    # end for
                    for cs_node in object_cs_nodes:
                        # The order of the data is:
                        #   object_concept_id, object_concept_name, cs_node_id, cs_node_uri
                        object_cs_nodes_query_data = [
                            object_concept_names_to_ids[object_concept_name], 
                            object_concept_name,
                            cs_node.id, cs_node.uri
                        ]
                        object_cs_nodes_batch_data.append(object_cs_nodes_query_data)
                # end if
                object_concept_id = object_concept_names_to_ids[object_concept_name]

                # Get the object instance name and id. 
                # Check if there's already an instance id for this node.
                # If there isn't, make one.
                if not node_id in node_ids_to_object_instance_ids:
                    node_ids_to_object_instance_ids[node_id] = object_instance_counter
                    object_instance_counter += 1
                # end if
                object_instance_id = node_ids_to_object_instance_ids[node_id]
                # The name should be {object_concept_name}_{object_instance_id}
                object_instance_name = f'{object_concept_name}_{object_instance_id}'

                # Get the object's bbox_x, y, h, and w.
                # Get them from the first scene graph object's bounding box.
                bbox = object_.scene_graph_objects[0].bounding_box
                bbox_x = bbox.x
                bbox_y = bbox.y
                bbox_h = bbox.h
                bbox_w = bbox.w

                # Get the object's attributes into a string separated by '|'
                attributes = object_.attributes
                attribute_str = ''
                for attribute in attributes:
                    attribute_str += attribute + '|'
                # end for
                attribute_str = attribute_str.rstrip('|')
                
                # The order of the data is:
                #   image_id, object_instance_id, object_instance_name,
                #   object_concept_id, object_concept_name, bbox_x, bbox_y,
                #   bbox_h, bbox_w, attributes.
                image_objects_query_data = [
                    image_id, object_instance_id, object_instance_name, 
                    object_concept_id, object_concept_name, bbox_x, bbox_y,
                    bbox_h, bbox_w, attribute_str
                ]
                image_objects_batch_data.append(image_objects_query_data)
            # end for object_
            # See if we're at or over the batch size.
            # If so, write the data into the image_objects table.
            if len(image_objects_batch_data) >= batch_size:
                elapsed_time = timer() - start_time
                image_objects_write_counter += 1
                print(f'Image {image_id} ({image_counter}/{len(image_ids)}).')
                print(f'Writing image_objects batch.' 
                      + f' Number of writes: {image_objects_write_counter}.'
                      + f' \nNumber of object concepts: {object_concept_counter}'
                      + f' Number of object instances: {object_instance_counter}'
                      + f' \nElapsed time: {elapsed_time}s.'
                      + f' Average time per image:'
                      + f' {elapsed_time/image_counter}s.')
                self._execute_query_batch(
                    query_string=image_objects_query_string, 
                    query_data=image_objects_batch_data
                )
                image_objects_batch_data = list()
            # end if
            # Check for object cs nodes as well.
            if len(object_cs_nodes_batch_data) >= batch_size:
                elapsed_time = timer() - start_time
                object_cs_nodes_write_counter += 1
                print(f'Image {image_id} ({image_counter}/{len(image_ids)}).')
                print(f'Writing object_cs_nodes batch.' 
                      + f' Number of writes: {object_cs_nodes_write_counter}'
                      + f' \nElapsed time: {elapsed_time}s.'
                      + f' Average time per image:'
                      + f' {elapsed_time/image_counter}s.')
                self._execute_query_batch(
                    query_string=object_cs_nodes_query_string, 
                    query_data=object_cs_nodes_batch_data
                )
                object_cs_nodes_batch_data = list()
            # end if

            # image_actions
            # The data we need for a single image_actions row is:
            #   image_id, action_instance_id, action_instance_name,
            #   action_concept_id, action_concept_name.
            for node_id, action in actions.items():
                # Get the action concept name and id.
                # The concept_name is the label of the node.
                action_concept_name = action.label
                # See if this concept already exists. If not, give it an
                # id and gather its cs nodes.
                if not action_concept_name in action_concept_names_to_ids:
                    action_concept_names_to_ids[action_concept_name] = action_concept_counter
                    action_concept_counter += 1
                    # Since this is a new action concept, gather its cs nodes
                    # and make batch data for the action_cs_nodes table.
                    action_cs_nodes: list[CommonSenseNode] = list()
                    for concept in action.concepts:
                        for cs_node in concept.commonsense_nodes.values():
                            action_cs_nodes.append(cs_node)
                        # end for
                    # end for
                    for cs_node in action_cs_nodes:
                        # The order of the data is:
                        #   action_concept_id, action_concept_name, cs_node_id, cs_node_uri
                        action_cs_nodes_query_data = [
                            action_concept_names_to_ids[action_concept_name], 
                            action_concept_name,
                            cs_node.id, cs_node.uri
                        ]
                        action_cs_nodes_batch_data.append(action_cs_nodes_query_data)
                    # end for
                # end if
                action_concept_id = action_concept_names_to_ids[action_concept_name]

                # Get the action instance name and id. 
                # Check if there's already an instance id for this node.
                # If there isn't, make one.
                if not node_id in node_ids_to_action_instance_ids:
                    node_ids_to_action_instance_ids[node_id] = action_instance_counter
                    action_instance_counter += 1
                # end if
                action_instance_id = node_ids_to_action_instance_ids[node_id]
                # The name should be {action_concept_name}_{action_instance_id}
                action_instance_name = f'{action_concept_name}_{action_instance_id}'
                
                # The order of the data is:
                #   image_id, action_instance_id, action_instance_name,
                #   action_concept_id, action_concept_name.
                image_actions_query_data = [
                    image_id, action_instance_id, action_instance_name, 
                    action_concept_id, action_concept_name
                ]
                image_actions_batch_data.append(image_actions_query_data)
            # end for action
            # See if we're at or over the batch size.
            # If so, write the data into the image_actions table.
            if len(image_actions_batch_data) >= batch_size:
                elapsed_time = timer() - start_time
                image_actions_write_counter += 1
                print(f'Image {image_id} ({image_counter}/{len(image_ids)}).')
                print(f'Writing image_actions batch.' 
                      + f' Number of writes: {image_actions_write_counter}.'
                      + f' \nNumber of action concepts: {action_concept_counter}'
                      + f' Number of action instances: {action_instance_counter}'
                      + f' \nElapsed time: {elapsed_time}s.'
                      + f' Average time per image:'
                      + f' {elapsed_time/image_counter}s.')
                self._execute_query_batch(
                    query_string=image_actions_query_string, 
                    query_data=image_actions_batch_data
                )
                image_actions_batch_data = list()
            # end if
            # Check for action cs nodes as well.
            if len(action_cs_nodes_batch_data) >= batch_size:
                elapsed_time = timer() - start_time
                action_cs_nodes_write_counter += 1
                print(f'Image {image_id} ({image_counter}/{len(image_ids)}).')
                print(f'Writing action_cs_nodes batch.' 
                      + f' Number of writes {action_cs_nodes_write_counter}.'
                      + f' \nElapsed time: {elapsed_time}s.'
                      + f' Average time per image:'
                      + f' {elapsed_time/image_counter}s.')
                self._execute_query_batch(
                    query_string=action_cs_nodes_query_string, 
                    query_data=action_cs_nodes_batch_data
                )
                action_cs_nodes_batch_data = list()
            # end if

            # image_action_object_pairs
            # The data we need for a single image_action_object_pairs row is:
            #   image_id, action_instance_id, action_instance_name, 
            #   object_instance_id, object_instance_name, object_role
            for action in actions.values():
                # This action's instance should have been made already.
                # Look up its instance id from this node's id.
                # Get its concept_name from its label.
                # Then, make its instance_name from {concept_name}_{instance_id}
                action_instance_id = node_ids_to_action_instance_ids[action.id]
                action_concept_name = action.label
                action_concept_id = action_concept_names_to_ids[action_concept_name]
                action_instance_name = f'{action_concept_name}_{action_instance_id}'
                for object_ in action.objects.values():
                    object_instance_id = node_ids_to_object_instance_ids[object_.id]
                    object_concept_name = object_.label
                    object_concept_id = object_concept_names_to_ids[object_concept_name]
                    object_instance_name = f'{object_concept_name}_{object_instance_id}'
                    object_role = ''
                    if action.is_subject(object_):
                        object_role = 'subject'
                    elif action.is_object(object_):
                        object_role = 'object'
                    else:
                        print('DataHandler.generate_database_tables : Error!'
                            + ' object is neither the subject nor object of'
                            + ' its action.')
                    # end else
                    # The order of the data is:
                    #   image_id, action_instance_id, action_instance_name, 
                    #   object_instance_id, object_instance_name, object_role,
                    #   action_concept_id, object_concept_id
                    image_action_object_pairs_query_data = [
                        image_id, action_instance_id, action_instance_name,
                        object_instance_id, object_instance_name, object_role,
                        action_concept_id, object_concept_id
                    ]
                    image_action_object_pairs_batch_data.append(
                        image_action_object_pairs_query_data
                    )
                    action_object_pairs_counter += 1
                # end for
            # end for action
            # See if we're at or over the batch size.
            # If so, write the data into the image_actions table.
            if len(image_action_object_pairs_batch_data) >= batch_size:
                elapsed_time = timer() - start_time
                image_action_object_pairs_write_counter += 1
                print(f'Image {image_id} ({image_counter}/{len(image_ids)}).')
                print(f'Writing image_action_object_pairs batch.' 
                      + f' Number of writes: {image_action_object_pairs_write_counter}.'
                      + f' \nNumber of action-object pairs: {action_object_pairs_counter}.'
                      + f' \nElapsed time: {elapsed_time}s.'
                      + f' Average time per image:'
                      + f' {elapsed_time/image_counter}s.')
                self._execute_query_batch(
                    query_string=image_action_object_pairs_query_string, 
                    query_data=image_action_object_pairs_batch_data
                )
                image_action_object_pairs_batch_data = list()
            # end if
            image_counter += 1
        # end for image_id

        # If there's any batch data left over by the end all the loops,
        # write them now.
        if len(image_objects_batch_data) > 0:
            print(f'Writing remaining image objects batch data.')
            self._execute_query_batch(
                query_string=image_objects_query_string,
                query_data=image_objects_batch_data)
        # end if
        if len(image_actions_batch_data) > 0:
            print(f'Writing remaining image actions batch data.')
            self._execute_query_batch(
                query_string=image_actions_query_string,
                query_data=image_actions_batch_data)
        # end if
        if len(image_action_object_pairs_batch_data) > 0:
            print(f'Writing remaining image action-object pairs batch data.')
            self._execute_query_batch(
                query_string=image_action_object_pairs_query_string,
                query_data=image_action_object_pairs_batch_data)
        # end if
        if len(object_cs_nodes_batch_data) > 0:
            print(f'Writing remaining object cs node batch data.')
            self._execute_query_batch(
                query_string=object_cs_nodes_query_string,
                query_data=object_cs_nodes_batch_data
            )
        # end if
        if len(action_cs_nodes_batch_data) > 0:
            print(f'Writing remaining action cs node batch data.')
            self._execute_query_batch(
                query_string=action_cs_nodes_query_string,
                query_data=action_cs_nodes_batch_data
            )
        # end if

        elapsed_time = timer() - start_time
        print('Done generating database tables.'
              + f' Total time taken: {elapsed_time}s.'
              + f' Average time per image: {elapsed_time/image_counter}s.')
    # end generate_database_tables

    def generate_causal_links_table(self):
        """

        Table Name: causal_links
        Columns:
            causal_link_id (int, index)
            source_node_id (int, index)
            source_node_uri (text)
            edge_id (int)
            edge_uri (text)
            weight (real)
            target_node_id (int, index)
            target_node_uri (text)
            is_forward (bool)
        """
        print("Generating causal link table...")

        start_timer = timer()

        # Make the causal_links table if it doesn't exist
        # Connecting to the database will make the database file if it doesn't 
        # exist, so we just have to execute one query. 
        query = ('''
                 CREATE TABLE IF NOT EXISTS causal_links
                 (causal_link_id INTEGER,
                  source_node_id INTEGER, 
                  source_node_uri TEXT,
                  edge_id INTEGER,
                  edge_uri TEXT,
                  weight REAL,
                  target_node_id INTEGER,
                  target_node_uri TEXT,
                  is_forward BOOLEAN)
                 ''')
        self._execute_query(query)
        # Index on causal_link_id, source_node_id, edge_id, and target_node_id.
        query = ('''
                 CREATE INDEX IF NOT EXISTS causal_links_causal_link_id_index
                 ON causal_links (causal_link_id)
                 ''')
        self._execute_query(query)
        query = ('''
                 CREATE INDEX IF NOT EXISTS causal_links_source_node_id_index
                 ON causal_links (source_node_id)
                 ''')
        self._execute_query(query)
        query = ('''
                 CREATE INDEX IF NOT EXISTS causal_links_target_node_id_index
                 ON causal_links (target_node_id)
                 ''')
        self._execute_query(query)
        query = ('''
                 CREATE INDEX IF NOT EXISTS causal_links_edge_id_index
                 ON causal_links (edge_id)
                 ''')
        self._execute_query(query)

        # Get a list of all distinct cs node IDs in the action_cs_nodes table.
        query_string = "SELECT DISTINCT cs_node_id FROM action_cs_nodes"
        rows = self._execute_query(query_string)
        # All items in the return list are tuples with a single item.
        # Unpack the tuples to get the ids.
        cs_node_ids = [row[0] for row in rows]

        print(f'{len(cs_node_ids)} distinct cs node ids. ' + 
              f'Time taken to fetch: {timer() - start_timer}')

        # Go through each cs node's causal edges and add an entry to the causal
        # link table for each one. 
        batch_query_string = ('''
            INSERT INTO causal_links 
            (source_node_id, source_node_uri, edge_id, edge_uri, weight, 
             target_node_id, target_node_uri, is_forward)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''')
        batch_query_data = list()
        batch_size = 1000
        node_counter = 0
        causal_counter = 0
        no_causal_counter = 0
        for cs_node_id in cs_node_ids:
            node_counter += 1
            cs_edges = self._commonsense_querier.get_edges(cs_node_id)
            causal_edge_found = False
            for cs_edge in cs_edges:
                if cs_edge.get_relationship() in const.COHERENCE_TO_RELATIONSHIP['causal']:
                    source_node_id = cs_edge.start_node_id
                    source_node_uri = cs_edge.start_node_uri
                    edge_id = cs_edge.id
                    edge_uri = cs_edge.uri
                    weight = cs_edge.weight
                    target_node_id = cs_edge.end_node_id
                    target_node_uri = cs_edge.end_node_uri
                    direction = const.CAUSAL_RELATIONSHIP_DIRECTION[cs_edge.get_relationship()]
                    is_forward = True if direction == const.CausalFlowDirection.FORWARD else False

                    query_data = list()
                    query_data.append(source_node_id)
                    query_data.append(source_node_uri)
                    query_data.append(edge_id)
                    query_data.append(edge_uri)
                    query_data.append(weight)
                    query_data.append(target_node_id)
                    query_data.append(target_node_uri)
                    query_data.append(is_forward)

                    batch_query_data.append(query_data)
                    causal_edge_found = True
                # end if
            # end for cs_edge
            if causal_edge_found:
                causal_counter += 1
            else:
                no_causal_counter += 1
            if len(batch_query_data) >= batch_size:
                print('Writing batch')
                print(f'Node {cs_node_id} ({node_counter}/{len(cs_node_ids)})')
                print(f'Nodes with causal edges: {causal_counter}')
                print(f'Nodes without causal edges: {no_causal_counter}')
                self._execute_query_batch(query_string=batch_query_string,
                                         query_data=batch_query_data)
                batch_query_data = list()
            # end if
        # end for cs_node_id

        if len(batch_query_data) > 0:
            print('Writing final batch.')
            self._execute_query_batch(query_string=batch_query_string,
                                        query_data=batch_query_data)
        # end if
        
        print(f'Nodes with causal edges: {causal_counter}')
        print(f'Nodes without causal edges: {no_causal_counter}')

        # Make the action_to_action_causal_links table as well.
        query = ('''
                CREATE TABLE IF NOT EXISTS action_to_action_causal_links AS
                    SELECT *
                    FROM causal_links
                    WHERE
                        EXISTS (
                            SELECT 1
                            FROM image_actions
                            WHERE causal_links.source_node_id = cs_node_id
                            )
                        AND EXISTS (
                            SELECT 1
                            FROM image_actions
                            WHERE causal_links.target_node_id = cs_node_id
                            )
                ''')
        self._execute_query(query, [])

    # end generate_causal_link_table

    def _generate_multi_causal_links_table(self):
        """
        Generates the multi_causal_links database table.

        Very old function, do not use?
        """

        timers = dict()
        timers['start'] = timer()

        # Get every action and their cs_nodes
        query = ('''
            SELECT * FROM action_cs_nodes
        ''')
        query_results = self._execute_query(query)

        # A dictionary of actions and their cs nodes, keyed by action label id.
        # Key: action_label_id
        # Value: dict with
        #   'action_label_id, int
        #   'action_label', str
        #   'cs_nodes', list
        #   'connections', list
        actions = dict()
        # A dictionary of all the cs nodes that appear in at least one action.
        # Nested dict
        # Key 1: action_label_id
        # Key 2: cs_node_id for one of the action's cs nodes
        # Value: the cs node itself.
        all_action_cs_nodes = dict()
        # A dictionary of all actions that a cs node appears in.
        # Key: cs_node_id
        # Value: list of action_label_ids.
        cs_node_actions = dict()
        timers['get_action_cs_nodes_start'] = timer()
        print('Getting actions and cs nodes.')
        for query_result in query_results:
            action_label_id = query_result[0]
            action_label = query_result[1]
            cs_node_id = query_result[2]
            cs_node_uri = query_result[3]
            # Filter out any cs nodes that aren't from ConceptNet
            # ConceptNet nodes start with '/c'
            if not cs_node_uri[:2] == '/c':
                continue

            if not action_label_id in actions:
                action = {'action_label_id': action_label_id,
                          'action_label': action_label,
                          'cs_nodes': list(),
                          'connections': list()}
                actions[action_label_id] = action
            # end if
            cs_node = self._commonsense_querier.get_node(cs_node_id)

            actions[action_label_id]['cs_nodes'].append(cs_node)
            all_action_cs_nodes[cs_node_id] = cs_node

            if not cs_node.id in cs_node_actions:
                cs_node_actions[cs_node.id] = list()
            cs_node_actions[cs_node.id].append(action_label_id)
        # end for
        elapsed_time = timer() - timers['get_action_cs_nodes_start']
        print(f'Done getting actions and cs nodes. Elapsed time: {elapsed_time}s.')
        print(f'Number of query results: {len(query_results)}. ' +
              f'Average time per query resut: {elapsed_time/len(query_results)}s.')
        print(f'Number of actions: {len(actions)}. ' + 
              f'Number of cs nodes: {len(self._commonsense_querier._node_cache)}.')
        
        # Get all the cs node connections with each cs node that appear in
        # an action.
        # This takes about 5 minutes, so cache it.
        print('Getting action cs node connections.')
        timers['get_cs_node_connections_start'] = timer()
        # Key: cs node id.
        # Value: A list of connections.
        cs_node_connections = self._try_load_dict_cache('cs_node_connections')
        # Organize a dict of connections by middle node and direction as well.
        # Key 1: middle cs node id (the target_cs_node in a connection)
        # Key 2: CausalFlowDirection (FORWARD or BACKWARD)
        # Value: A list of connnections 
        middle_node_connections = self._try_load_dict_cache('middle_node_connections')
        if (len(cs_node_connections) == 0
            or len(middle_node_connections) == 0):
            cs_node_counter = 0
            for cs_node_id, cs_node in all_action_cs_nodes.items():
                connections = self._get_cs_node_connections(cs_node)
                cs_node_connections[cs_node_id] = connections
                cs_node_counter += 1

                # Populate middle_node_connections
                for connection in connections:
                    middle_node = connection['target_cs_node']
                    direction = connection['connection_causal_direction']
                    if not middle_node.id in middle_node_connections:
                        middle_node_connections[middle_node.id] = dict()
                    if not direction in middle_node_connections[middle_node.id]:
                        middle_node_connections[middle_node.id][direction] = list()
                    middle_node_connections[middle_node.id][direction].append(connection)
                # end for

                if cs_node_counter % 500 == 1:
                    elapsed_time = timer() - timers['get_cs_node_connections_start']
                    print(f'cs node {cs_node_counter}/{len(all_action_cs_nodes)}. ' +
                        f'Elapsed time: {elapsed_time}s.')
                    print(f'Average time per cs node: {elapsed_time/cs_node_counter}s.')
                # end if
            # end for
            # Takes 333 seconds for 7391 cs nodes
            self._write_dict_cache('cs_node_connections', cs_node_connections)
            self._write_dict_cache('middle_node_connections', middle_node_connections)
        # end if
        elapsed_time = timer() - timers['get_cs_node_connections_start']
        print(f'Done getting cs node connections. Elapsed time: {elapsed_time}s.')
        print(f'Number of cs nodes: {len(cs_node_connections)}. ' +
              f'Average time per cs node: {elapsed_time/len(cs_node_connections)}s.')
        print(f'Number of middle nodes: {len(middle_node_connections)}.')

        # Now that we have all the connections for every cs node, we can see
        # which cs nodes have connections that go to the same middle nodes and
        # go in the opposite connection_causal_direction.
        # Because connection_causal_direction is relative to the middle node,
        # pairs of connections that go in the same direction will look like this:
        #   cs node -> middle_cs_node <- cs node
        # or
        #   cs node <- middle_cs_node -> cs node
        # Instead, we want pairs of connections go in opposite directions, which 
        # look like this:
        #   cs node -> middle cs node -> cs node
        # or
        #   cs node -> middle cs node -> cs node

        # Gather all such pairs of connections for every cs node.
        # Key_1: source cs_node_id
        # Key_2: target cs_node_id
        # Value: list of dicts of connection pairs, where each pair
        # is a dict with:
        #   'source_cs_node'
        #   'middle_cs_node'
        #   'target_cs_node'
        #   'source_middle_connection'
        #   'middle_target_connection'
        #   'direction', overall direction treating the source as the start and
        #       the target as the end. 
        cs_node_connection_pairs = dict()
        connection_pair_counter = 0
        timers['start_cs_node_connection_pairs'] = timer()
        print('Gathering cs node connection pairs.')
        # Go through all the connections for every middle cs node. 
        for middle_node_id in middle_node_connections.keys():
            # If this middle node doesn't have both forward and backward
            # connections, skip it.
            if (not CausalFlowDirection.FORWARD in middle_node_connections[middle_node_id]
                or not CausalFlowDirection.BACKWARD in middle_node_connections[middle_node_id]):
                continue
            # end if
            middle_cs_node = self._commonsense_querier.get_node(middle_node_id)
            forward_connections = middle_node_connections[middle_node_id][CausalFlowDirection.FORWARD]
            backward_connections = middle_node_connections[middle_node_id][CausalFlowDirection.BACKWARD]
            for forward_connection in forward_connections:
                for backward_connection in backward_connections:
                    # Treat the source of the forward connection as the source
                    # cs node and the source of the backward connection as the
                    # target cs node.
                    source_cs_node = forward_connection['source_cs_node']
                    source_id = source_cs_node.id
                    target_cs_node = backward_connection['source_cs_node']
                    target_id = target_cs_node.id
                    # The forward connection is the source_middle connection
                    # and the backward connection is the middle_target
                    # connection.
                    # The direction is forward from the source cs node to the
                    # target cs node.
                    direction = CausalFlowDirection.FORWARD
                    pair_dict = {
                        'source_cs_node': source_cs_node,
                        'target_cs_node': target_cs_node,
                        'middle_cs_node': middle_cs_node,
                        'source_middle_connection': forward_connection,
                        'middle_target_connection': backward_connection,
                        'direction': direction
                    }
                    if not source_id in cs_node_connection_pairs:
                        cs_node_connection_pairs[source_id] = dict()
                    if not target_id in cs_node_connection_pairs[source_id]:
                        cs_node_connection_pairs[source_id][target_id] = list()
                    cs_node_connection_pairs[source_id][target_id].append(pair_dict)

                    # Now switch the source and target cs nodes and add a pair
                    # dict in that direction.
                    # Also have to switch the source_middle and middle_target
                    # connections.
                    # The direction will be backwards.
                    direction = CausalFlowDirection.BACKWARD
                    pair_dict_backwards = {
                        'source_cs_node': target_cs_node,
                        'target_cs_node': source_cs_node,
                        'middle_cs_node': middle_cs_node,
                        'source_middle_connection': backward_connection,
                        'middle_target_connection': forward_connection,
                        'direction': direction
                    }
                    if not target_id in cs_node_connection_pairs:
                        cs_node_connection_pairs[target_id] = dict()
                    if not source_id in cs_node_connection_pairs[target_id]:
                        cs_node_connection_pairs[target_id][source_id] = list()
                    cs_node_connection_pairs[target_id][source_id].append(pair_dict_backwards)

                    connection_pair_counter += 2
                # end for backward_connection
            # end for forward_connection
        # end for
        elapsed_time = timer() - timers['start_cs_node_connection_pairs']
        print(f'Done gathering cs node connection pairs. Elapsed time: ' + 
              f'{elapsed_time}s.')
        print(f'Connection pairs: {connection_pair_counter}. ' +
              f'Number of cs nodes with connection pairs: {len(cs_node_connection_pairs)}')

        # Key: action_label_id
        # Value: list of action pair dicts with:
        #   'source_action_label'
        #   'source_action_label_id'
        #   'target_action_label'
        #   'target_action_label_id'
        #   'source_cs_node'
        #   'middle_cs_node'
        #   'target_cs_node'
        #   'source_middle_connection'
        #   'middle_target_connection'
        #   'direction', overall direction treating the source as the start and
        #       the target as the end. 
        timers['start_action_pairs'] = timer()
        print(f'Gathering action pairs.')
        action_connection_pairs = self._try_load_dict_cache('action_connection_pairs')
        if len(action_connection_pairs) == 0:
            pair_counter = 0
            action_counter = 0
            # For each action
            for action_label_id, action_dict in actions.items():
                # Get all its cs nodes
                action_cs_nodes = action_dict['cs_nodes']

                # For each cs node, get all the other cs nodes it has a connection 
                # pair with.
                for cs_node in action_cs_nodes:
                    # If the cs node has no connection pairs, skip it.
                    if not cs_node.id in cs_node_connection_pairs:
                        continue
                    for connected_cs_node_id, connection_pairs in cs_node_connection_pairs[cs_node.id].items():
                        connected_cs_node = self._commonsense_querier.get_node(connected_cs_node_id)
                        # For each other cs node and its connection pair, get all the unique 
                        # actions that contain the cs node. 
                        connected_action_ids = cs_node_actions[connected_cs_node_id]

                        for connection_pair in connection_pairs:
                            # This action has a multi causal link with each other action 
                            # according to this connection pair.
                            for connected_action_id in connected_action_ids:
                                connected_action_dict = actions[connected_action_id]
                                # The source action should be the action that contains
                                # the source cs node of this connection pair.
                                # The target action should be the action that contains
                                # teh target cs node of this connection pair.
                                source_action_dict = None
                                target_action_dict = None

                                if (cs_node == connection_pair['source_cs_node']
                                    and connected_cs_node == connection_pair['target_cs_node']):
                                    source_action_dict = action_dict
                                    target_action_dict = connected_action_dict
                                elif (cs_node == connection_pair['target_cs_node']
                                    and connected_cs_node == connection_pair['source_cs_node']):
                                    source_action_dict = connected_action_dict
                                    target_action_dict = action_dict
                                else:
                                    print('Error! source and target cs nodes do not line up with connection pair!')
                                # end if else
                                
                                source_action_label = source_action_dict['action_label']
                                source_action_label_id = source_action_dict['action_label_id']
                                target_action_label = target_action_dict['action_label']
                                target_action_label_id = target_action_dict['action_label_id']

                                action_pair_dict = {
                                    'source_action_label': source_action_label,
                                    'source_action_label_id': source_action_label_id,
                                    'target_action_label': target_action_label,
                                    'target_action_label_id': target_action_label_id
                                }
                                action_pair_dict.update(connection_pair)
                                if not action_label_id in action_connection_pairs:
                                    action_connection_pairs[action_label_id] = list()
                                action_connection_pairs[action_label_id].append(action_pair_dict)
                                pair_counter += 1
                            # end for connected_action_id
                        # end for connection_pair
                    # end for connected_cs_node_id
                # end for cs_node

                action_counter += 1
                if action_counter % 100 == 1:
                    elapsed_time = timer() - timers['start_action_pairs']
                    print(f'Action {action_counter}/{len(actions)}. Elapsed time: {elapsed_time}s.')
                    print(f'Actions with pairs: {len(action_connection_pairs)}.')
                    print(f'Number of action pairs: {pair_counter}')
            # end for action_label_id
            print('Writing action_connection_pairs to file.')
            self._write_dict_cache('action_connection_pairs', action_connection_pairs)
            elapsed_time = timer() - timers['start_action_pairs']
            print(f'Done gathering action pairs. Elapsed time: {elapsed_time}s.')
            print(f'Actions with pairs: {len(action_connection_pairs)}.')
            print(f'Number of action pairs: {pair_counter}')
        # end if

        # Generate multi causal links table.
        # This table has the multi-step causal links between CommonSenseNodes.
        generate_multi_causal_links_table = False
        if generate_multi_causal_links_table:
            print('Generating multi_causal_links table.')
            timers['start_multi_causal_links_table'] = timer()
            # Make the table.
            query = ('''
                CREATE TABLE IF NOT EXISTS multi_causal_links
                ([source_cs_node_id] INTEGER,
                [source_cs_node_uri] TEXT,
                [middle_cs_node_id] INTEGER,
                [middle_cs_node_uri] TEXT,
                [target_cs_node_id] INTEGER,
                [target_cs_node_uri] TEXT,
                [source_middle_edge_id] INTEGER,
                [source_middle_edge_uri] TEXT,
                [source_middle_edge_weight] REAL,
                [middle_target_edge_id] INTEGER,
                [middle_target_edge_uri] TEXT,
                [middle_target_edge_weight] REAL,
                [direction] TEXT)
            ''')
            self._execute_query(query)
            # Index of source cs node id and
            # target cs node id.
            query = ('''
                CREATE INDEX IF NOT EXISTS multi_causal_links_source_cs_node_id
                ON multi_action_links (source_cs_node_id)
            ''')
            self._execute_query(query)
            query = ('''
                CREATE INDEX IF NOT EXISTS multi_action_links_target_cs_node_id
                ON multi_action_links (target_cs_node_id)
            ''')
            self._execute_query(query)

            # Insert rows into the table.
            query = ('''
                INSERT INTO multi_causal_links
                (source_cs_node_id, source_cs_node_uri,
                 middle_cs_node_id, middle_cs_node_uri, target_cs_node_id, 
                 target_cs_node_uri, source_middle_edge_id, source_middle_edge_uri,
                 source_middle_edge_weight, middle_target_edge_id, 
                 middle_target_edge_uri, middle_target_edge_weight, direction)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''')
            batch_data = list()

            # Insert rows into the table in batches.
            cs_node_counter = 0
            for source_cs_node_id in cs_node_connection_pairs.keys():
                for target_cs_node_id, connection_pairs in cs_node_connection_pairs[source_cs_node_id].items():
                    for pair in connection_pairs:
                        source_middle_edge = pair['source_middle_connection']['cs_edge']
                        middle_target_edge = pair['middle_target_connection']['cs_edge']
                        direction = ''
                        if pair['direction'] == CausalFlowDirection.FORWARD:
                            direction = 'forward'
                        else:
                            direction = 'backward'
                        query_data = [
                            pair['source_cs_node'].id,
                            pair['source_cs_node'].uri,
                            pair['middle_cs_node'].id,
                            pair['middle_cs_node'].uri,
                            pair['target_cs_node'].id,
                            pair['target_cs_node'].uri,
                            source_middle_edge.id,
                            source_middle_edge.uri,
                            source_middle_edge.weight,
                            middle_target_edge.id,
                            middle_target_edge.uri,
                            middle_target_edge.weight,
                            direction
                        ]
                        batch_data.append(query_data)
                    # end for
                    if len(batch_data) > 1000:
                        elapsed_time = timer() - timers['start_multi_causal_links_table']
                        print(f'Executing query batch.')
                        print(f'cs node {cs_node_counter}/{len(cs_node_connection_pairs)}.'
                            + f' Elapsed time: {elapsed_time}s.')
                        print(f'Average time per cs node: {elapsed_time/cs_node_counter}s.')
                        self._execute_query_batch(query, batch_data)
                        batch_data = list()
                    # end if
                    cs_node_counter += 1
                # end for pair
            # end for
            # table has 12024 rows
        # end if
        
        generate_multi_action_links_table = False
        if generate_multi_action_links_table:
            print('Generating multi_action_links table.')
            timers['start_multi_action_links_table'] = timer()
            # Make the table.
            query = ('''
                CREATE TABLE IF NOT EXISTS multi_action_links
                ([source_action_label] TEXT, 
                [source_action_label_id] INTEGER,
                [target_action_label] TEXT,
                [target_action_label_id] INTEGER,
                [source_cs_node_id] INTEGER,
                [source_cs_node_uri] TEXT,
                [middle_cs_node_id] INTEGER,
                [middle_cs_node_uri] TEXT,
                [target_cs_node_id] INTEGER,
                [target_cs_node_uri] TEXT,
                [source_middle_edge_id] INTEGER,
                [source_middle_edge_uri] TEXT,
                [source_middle_edge_weight] REAL,
                [middle_target_edge_id] INTEGER,
                [middle_target_edge_uri] TEXT,
                [middle_target_edge_weight] REAL,
                [direction] TEXT)
            ''')
            self._execute_query(query)
            # Index of source action label id and
            # target action label id.
            query = ('''
                CREATE INDEX IF NOT EXISTS multi_action_links_source_action_label_id
                ON multi_action_links (source_action_label_id)
            ''')
            self._execute_query(query)
            query = ('''
                CREATE INDEX IF NOT EXISTS multi_action_links_target_action_label_id
                ON multi_action_links (target_action_label_id)
            ''')
            self._execute_query(query)

            # Insert rows into the table.
            query = ('''
                INSERT INTO multi_action_links
                (source_action_label, source_action_label_id, target_action_label,
                target_action_label_id, source_cs_node_id, source_cs_node_uri,
                middle_cs_node_id, middle_cs_node_uri, target_cs_node_id, 
                target_cs_node_uri, source_middle_edge_id, source_middle_edge_uri,
                source_middle_edge_weight, middle_target_edge_id, 
                middle_target_edge_uri, middle_target_edge_weight, direction)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''')
            batch_data = list()

            # Insert rows into the table in batches.
            action_counter = 0
            for action_label_id, action_pairs in action_connection_pairs.items():
                for action_pair in action_pairs:
                    source_middle_edge = action_pair['source_middle_connection']['cs_edge']
                    middle_target_edge = action_pair['middle_target_connection']['cs_edge']
                    direction = ''
                    if action_pair['direction'] == CausalFlowDirection.FORWARD:
                        direction = 'forward'
                    else:
                        direction = 'backward'
                    query_data = [
                        action_pair['source_action_label'],
                        action_pair['source_action_label_id'],
                        action_pair['target_action_label'],
                        action_pair['target_action_label_id'],
                        action_pair['source_cs_node'].id,
                        action_pair['source_cs_node'].uri,
                        action_pair['middle_cs_node'].id,
                        action_pair['middle_cs_node'].uri,
                        action_pair['target_cs_node'].id,
                        action_pair['target_cs_node'].uri,
                        source_middle_edge.id,
                        source_middle_edge.uri,
                        source_middle_edge.weight,
                        middle_target_edge.id,
                        middle_target_edge.uri,
                        middle_target_edge.weight,
                        direction
                    ]
                    batch_data.append(query_data)
                # end for
                if len(batch_data) > 1000:
                    elapsed_time = timer() - timers['start_multi_action_links_table']
                    print(f'Executing query batch.')
                    print(f'Action {action_counter}/{len(action_connection_pairs)}.'
                        + f' Elapsed time: {elapsed_time}s.')
                    print(f'Average time per action: {elapsed_time/action_counter}s.')
                    self._execute_query_batch(query, batch_data)
                    batch_data = list()
                # end if
                action_counter += 1
            # end for
            # Ended up with 343343 rows.
        # end if

        print('Done generating multi causal links and multi_action_links tables :)')
        elapsed_time = timer() - timers['start']
        print(f'Elapsed time: {elapsed_time}s.')

        print('')
    # _generate_multi_causal_links_table



    # Helper functions

    def _get_all_image_ids(self) -> list[int]:
        """
        Reads the filenames of all the json files in the scene_graphs folder in 
        inputs and makes a list of image IDs out of them.
        """
        image_id_list = list()
        directory = self._images_directory
        for filename in os.listdir(directory):
            image_id_list.append(int(filename.split('.')[0]))
        return image_id_list
    # end _get_all_image_ids

    def _get_cs_node_connections(self, cs_node):
        '''
        Gets all the CommonSenseNodes connected to a CommonSenseNodes,
        as well as the edges connecting them and in which direction they
        are connected. 

        Each connection is a dict with:
          'source_cs_node', the cs_node passed in.

          'target_cs_node', the cs_node connected to the source node.

          'cs_edge', the edge connecting the source and target cs nodes.

          'edge_direction', which way the edge is pointing relative to this
              connection's source and target cs nodes.

              If edge direction is FORWARD, the edge's source_node is
              this connection's source node.

              If edge direction is BACKWARD, the edge's end_node is
              this connection's source node.

          'edge_causal_direction', which way the causal relationship in the 
              edge is pointing relative to the edge's source and end cs nodes.

          'connection_causal_direction', which way the causal relationship in 
              the edge is pointing relative to the connection's source and 
              target cs nodes.
        '''
        connections = list()

        source_cs_node = cs_node
        cs_edges = self._commonsense_querier.get_edges(source_cs_node.id)
        for cs_edge in cs_edges:
            relationship = cs_edge.get_relationship()
            # Skip non-causal edges.
            if not relationship in const.CAUSAL_RELATIONSHIP_DIRECTION:
                continue

            target_cs_node_id = None
            edge_direction = None
            if source_cs_node.id == cs_edge.start_node_id:
                target_cs_node_id = cs_edge.end_node_id
                edge_direction = CausalFlowDirection.FORWARD
            # end if
            elif source_cs_node.id == cs_edge.end_node_id:
                target_cs_node_id = cs_edge.start_node_id
                edge_direction = CausalFlowDirection.BACKWARD
            # end elif
            else:
                print('_get_cs_node_connections: Error! cs node is ' + 
                        'neither start or end node of cs edge!')
            # end else
            target_cs_node = self._commonsense_querier.get_node(target_cs_node_id)
            
            edge_causal_direction = const.CAUSAL_RELATIONSHIP_DIRECTION[relationship]

            # The connection's causal direction is the edge's causal direction,
            # inverted if the edge is backwards.
            connection_causal_direction = edge_causal_direction
            if edge_direction == CausalFlowDirection.BACKWARD:
                connection_causal_direction = CausalFlowDirection.reverse(
                    connection_causal_direction
                )
                # end elif
            # end if

            connection = {
                'source_cs_node': source_cs_node,
                'target_cs_node': target_cs_node,
                'cs_edge': cs_edge,
                'edge_direction': edge_direction,
                'edge_causal_direction': edge_causal_direction,
                'connection_causal_direction': connection_causal_direction
            }
            connections.append(connection)
        # end for cs_edge

        return connections
    # end _get_cs_node_connections

    def _execute_query(self, query_string: str, query_data=None):
        """
        Execute a sql query in the concept_data database.

        Parameters
        ----------
        query_string : str
            The full string for the query.
        query_data : List, optional
            Any data used in the query. Default value is None.

            e.g., data to be inserted into a row.
        
        Returns
        -------
        list[tuple] | None
            The return values of the query as a list of tuples. If the operation 
            failed, returns None.
        """
        return_value = None
        # Open a connection to the database
        connection = sqlite3.connect(self._database_file_path)
        try:
            # Get a cursor to the database
            cursor = connection.cursor()
            # Execute the given sql command.
            if query_data == None:
                cursor.execute(query_string)
            else:
                cursor.execute(query_string, query_data)
            return_value = cursor.fetchall()
            # end if
            # Commit the changes to the database
            connection.commit()
        except Error as e:
            print(f'database_manager.execute_query : Error executing sql ' +
                f'query \"{query_string}\": {e}' +
                f'\ndata:{query_data}')
            return_value = None
        # end try
        # Whether the command was executed successfully or not,
        # close the connection.
        connection.close()
        return return_value
    # end execute_query

    def _execute_query_batch(self, query_string: str, query_data):
        """
        Execute a batch of queries. 

        Parameters
        ----------
        query_string : str
            The string for the query. Each query has to use the same string.
        
        query_data : list[list]
            A list of lists of data. Each entry is a single list of query data.
        
        Returns
        -------
        list[tuple] | None
            The return values of the as a list of tuples. If the operation 
            failed, returns None.
        """
        return_value = None
        # Open a connection to the database
        connection = sqlite3.connect(self._database_file_path)
        try:
            # Get a cursor to the database
            cursor = connection.cursor()
            # Execute the given sql command.
            if query_data == None:
                cursor.executemany(query_string)
            else:
                cursor.executemany(query_string, query_data)
            return_value = cursor.fetchall()
            # end if
            # Commit the changes to the database
            connection.commit()
        except Error as e:
            #print(f'Querier.execute_query_batch : Error executing sql ' +
            #      f'query \"{query_string}\": {e}' +
            #      f'\ndata:{query_data}')
            print(f'Querier.execute_query_batch : Error executing sql ' +
                  f'query \"{query_string}\": {e}')
            return_value = None
        # end try
        # Whether the command was executed successfully or not,
        # close the connection.
        connection.close()
        return return_value
    # end execute_query_batch

# end class DatabaseTableGenerator