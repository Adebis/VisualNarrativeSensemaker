import atexit
import pickle
import os.path
import sqlite3
from sqlite3 import Error
import json
import csv
import re
import hashlib
from dataclasses import dataclass, field
from timeit import default_timer as timer

from nltk.corpus import wordnet as wn
import spacy

import constants as const

from commonsense.querier import CommonSenseQuerier
from commonsense.commonsense_data import (CommonSenseEdge, CommonSenseNode,
                                          ConceptNetNode, AtomicNode, 
                                          FrameNetNode, WordNetNode)

class CSKGQuerier(CommonSenseQuerier):
    """
    A class to handle querying and managing the CSKG tables of the
    commonsense_knowledge database.
    """
    def __init__(self, db_file_path: str = None):
        super().__init__(db_file_path)
        # Cache a mapping of node ids to CommonSenseNode objects.
        self._node_cache = dict()
        # Cache a mapping of node ids to lists of CommonSenseEdge objects.
        self._node_edge_cache = dict()
        self._initialize_database()
    # end __init__

    def _initialize_database(self):
        """
        Initialization function for the database.

        Creates the database at database_file_path if it does not already exist.
        
        Creates the cskg_edges and cskg_nodes tables if they don't already 
        exist.
        """
        # Connecting to the database will make the database file if it doesn't 
        # exist, so we just have to execute one query. 
        # Make the cskg_edges table if it doesn't exist.
        query = ('''
                 CREATE TABLE IF NOT EXISTS cskg_edges
                 ([id] INTEGER PRIMARY KEY, 
                  [uri] TEXT,
                  [relation] TEXT,
                  [start_node_id] INTEGER,
                  [end_node_id] INTEGER,
                  [start_node_uri] TEXT,
                  [end_node_uri] TEXT,
                  [labels] TEXT,
                  [dimension] TEXT,
                  [source] TEXT,
                  [sentence] TEXT,
                  [weight] REAL)
                 ''')
        self.execute_query(query)
        # Index on start and end node ids, since we'll be searching for edges
        # using node ids.
        query = ('''
                 CREATE INDEX IF NOT EXISTS cskg_start_node_id_index
                 ON cskg_edges (start_node_id)
                 ''')
        self.execute_query(query)
        query = ('''
                 CREATE INDEX IF NOT EXISTS cskg_end_node_id_index
                 ON cskg_edges (end_node_id)
                 ''')
        self.execute_query(query)
        # Index on the uri, since we'll be finding edge IDs based on it.
        query = ('''
                 CREATE INDEX IF NOT EXISTS cskg_edge_uri_index
                 ON cskg_edges (uri)
                 ''')
        self.execute_query(query)
        # Make the cskg_nodes table if it doesn't exist.
        query = ('''
                 CREATE TABLE IF NOT EXISTS cskg_nodes
                 ([id] INTEGER PRIMARY KEY, 
                  [uri] TEXT,
                  [labels] TEXT,
                  [edge_ids] TEXT)
                 ''')
        self.execute_query(query)
        # Index on the uri, since we might be searching for node IDs for uris
        # based on it. 
        query = ('''
                 CREATE INDEX IF NOT EXISTS cskg_nodes_uri_index
                 ON cskg_nodes (uri)
                 ''')
        self.execute_query(query)
        # Make a cskg_node_labels table mapping node ids to labels.
        query = ('''
                 CREATE TABLE IF NOT EXISTS cskg_node_labels
                 ([id_label_key] TEXT PRIMARY KEY,
                  [node_id] INTEGER,
                  [label] TEXT)
                  ''')
        self.execute_query(query)
        # Index on the label, since we'll be searching for node IDs for search
        # terms by matching them to the nodes' labels.
        query = ('''
                 CREATE INDEX IF NOT EXISTS cskg_node_label_index
                 ON cskg_node_labels (label)
                 ''')
        self.execute_query(query)
        # Populate the cskg and nodes and edges tables if they aren't already 
        # populated.
        query = ('''
                 SELECT COUNT(*) FROM cskg_edges
                 ''')
        number_of_rows = self.execute_query(query)[0][0]
        if number_of_rows == 0:
            # Populate the tables if there are no rows in the edges table.
            print(f'CSKGQuerier._initialize_database : ' +
                  f'cskg_edges table empty. Populating...')
            self._populate_overall_tables()
            self._populate_weights()
            print("Done!")
        # end if
    # end _initialize_database

    def _populate_overall_tables(self):
        """
        Function to populate the overall cskg_edges and cskg_nodes 
        tables.

        Reads cskg edges from cskg/cskg.tsv and writes them into the
        cskg_edges table. Every unique start or end node URI is written into the 
        cskg_nodes table.

        cskg.tsv is a tab-separated value file with a header.
        """
        # Header is:
        # ['id', 'node1', 'relation', 'node2', 'node1;label', 'node2;label', 
        # 'relation;label', 'relation;dimension', 'source', 'sentence']
        timers = dict()
        timers['start'] = timer()
        timers['last_row_check'] = timer()
        # Batch the writes according to this batch size.
        batch_size = 10000
        # Every batch will use the same query strings
        edge_query_string = ('''
                             INSERT INTO cskg_edges 
                             (id, uri, relation, start_node_id, end_node_id, 
                             start_node_uri, end_node_uri, labels, dimension,
                             source, sentence, weight)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                             ''')
        node_query_string = ('''
                             INSERT OR IGNORE INTO cskg_nodes 
                             (id, uri, labels, edge_ids)
                             VALUES (?, ?, ?, ?)
                             ''')
        label_query_string = ('''
                              INSERT OR IGNORE INTO cskg_node_labels
                              (id_label_key, node_id, label)
                              VALUES (?, ?, ?)
                              ''')
        edge_batch_data = list()
        node_batch_data = list()
        label_batch_data = list()
        # Keep a map of node URIs to node IDs.
        node_uri_id_map = dict()
        # Keep a map of node IDs to edge IDs incident on the node.
        node_edge_id_map = dict()
        node_count = -1
        edge_count = -1
        row_count = -1
        # Read the cskg.tsv file.
        with (open(f'{const.DATA_DIRECTORY}/cskg/cskg_dim.tsv', encoding='utf8') 
              as cskg_file):
            # Embedded single or double quotes could lead to a field size limit
            # error, so we have to include the quoting=QUOTE_NONE parameter.
            reader = csv.reader(cskg_file, delimiter='\t', 
                                quoting=csv.QUOTE_NONE)
            for row in reader:
                row_count += 1
                edge_count += 1
                # Skip the header.
                if row_count == 0:
                    continue
                # Build the edge data
                edge_query_data = list()
                # id = number of edge = edge_count
                edge_query_data.append(edge_count)
                # uri = id = row[0]
                edge_query_data.append(row[0])
                # relation = relation = row[2]
                edge_query_data.append(row[2])
                # start_node_id = id of node1 = id of row[1] or node_count
                node_count += 1
                start_node_id = node_count
                if row[1] in node_uri_id_map:
                    start_node_id = node_uri_id_map[row[1]]
                else:
                    # Build the start node data and insert new rows for it
                    # if it isn't already accounted for.
                    node_uri_id_map[row[1]] = start_node_id
                    node_edge_id_map[start_node_id] = list()

                    start_node_query_data = list()
                    # id = id of node1 = id of row[1]
                    start_node_query_data.append(start_node_id)
                    # uri = node1 = row[1]
                    start_node_query_data.append(row[1])
                    # labels = node1;label = row[4]
                    start_node_query_data.append(row[4])
                    # Provide an empty edge ids list for now.
                    start_node_query_data.append('')
                    node_batch_data.append(start_node_query_data)
                    # Build the node labels data.
                    for label in row[4].split('|'):
                        id_label_key = (f'{start_node_id}_{label}')
                        label_batch_data.append([id_label_key, start_node_id, 
                                                label])
                    # end for
                # end else
                node_edge_id_map[start_node_id].append(edge_count)

                edge_query_data.append(start_node_id)

                # end_node_id = id of node2 = id of row[3] or node_count
                node_count += 1
                end_node_id = node_count
                if row[3] in node_uri_id_map:
                    end_node_id = node_uri_id_map[row[3]]
                else:
                    # Build the end node data and insert new rows for it
                    # if it isn't already accounted for.
                    node_uri_id_map[row[3]] = end_node_id
                    node_edge_id_map[end_node_id] = list()

                    end_node_query_data = list()
                    # id = id of node2 = id of row[3]
                    end_node_query_data.append(end_node_id)
                    # uri = node2 = row[3]
                    end_node_query_data.append(row[3])
                    # labels = node2;label = row[5]
                    end_node_query_data.append(row[5])
                    # Provide an empty edge ids list for now. 
                    end_node_query_data.append('')
                    node_batch_data.append(end_node_query_data)
                    # Build the node labels data.
                    for label in row[5].split('|'):
                        id_label_key = (f'{end_node_id}_{label}')
                        label_batch_data.append([id_label_key, end_node_id, 
                                                 label])
                    # end for
                # end else
                node_edge_id_map[end_node_id].append(edge_count)

                edge_query_data.append(end_node_id)
                # start_node_uri = node1 = row[1]
                edge_query_data.append(row[1])
                # end_node_uri = node2 = row[3]
                edge_query_data.append(row[3])
                # labels = relation;label = row[6]
                edge_query_data.append(row[6])
                # dimension = relation;dimension = row[7]
                edge_query_data.append(row[7])
                # source = source = row[8]
                edge_query_data.append(row[8])
                # sentence = sentence = row[9]
                edge_query_data.append(row[9])
                # Leave the weight 0 for now.
                edge_query_data.append(0)
                edge_batch_data.append(edge_query_data)

                # If we've hit the batch size, write the rows into the table.
                if row_count > 0 and len(edge_batch_data) % batch_size == 0:
                    # Insert the rows into the edges table.
                    self.execute_query_batch(edge_query_string, edge_batch_data)
                    # Insert the rows into the nodes table.
                    self.execute_query_batch(node_query_string, node_batch_data)
                    # Insert the rows into the labels table.
                    self.execute_query_batch(label_query_string, 
                                             label_batch_data)
                    # Empty the batch data.
                    edge_batch_data = list()
                    node_batch_data = list()
                    label_batch_data = list()

                    time_since_last = timer() - timers['last_row_check']
                    time_elapsed = timer() - timers['start']
                    print(f'Row {row_count}. Time since last batch: ' +
                          f'{time_since_last}. ' +
                          f'Total elapsed time: {time_elapsed}.')
                    timers['last_row_check'] = timer()
                # end if
            # end for
            # If we've reached the end of the tsv and there's some batch data
            # left, make sure to insert it.
            if len(edge_batch_data) > 0:
                print(f'Row {row_count}, end of tsv. Writing final batch...')
                # Insert the rows into the edges table.
                self.execute_query_batch(edge_query_string, edge_batch_data)
                # Insert the rows into the nodes table.
                self.execute_query_batch(node_query_string, node_batch_data)
                # Insert the rows into the labels table.
                self.execute_query_batch(label_query_string, label_batch_data)
            # end if
        # end with
        # Make sure to assign nodes their lists of incident edge ids.
        self._populate_node_edge_ids(node_edge_id_map=node_edge_id_map)
        elapsed_time = timer() - timers['start']
        print(f'Done populating cskg tables. Elapsed time: {elapsed_time}')
    # end _populate_overall_tables

    def _populate_node_edge_ids(self, node_edge_id_map: dict[int, list[int]]):
        """
        Populates the edge_ids column in the cskg_nodes table.

        Takes a mapping of node ids to lists of edge ids incident on that node.
        """
        print(f'Updating cskg_nodes edge_ids...')
        batch_data = list()
        batch_size = 10000
        query_string = ('''
                        UPDATE cskg_nodes
                        SET edge_ids = ?
                        WHERE id = ?
                        ''')
        batch_counter = 0
        for node_id, edge_ids in node_edge_id_map.items():
            edge_id_text = ''
            # Make a text version of the list of ids by separating the edge ids
            # by '|'.
            for edge_id in edge_ids:
                edge_id_text += (f'{edge_id}|')
            edge_id_text = edge_id_text.rstrip('|')
            batch_data.append([edge_id_text, node_id])
            batch_counter += 1
            # If we've hit the batch size, write the rows into the table.
            if batch_counter % batch_size == 0:
                # Update the rows in the nodes table.
                self.execute_query_batch(query_string, batch_data)
                # Empty the batch data.
                batch_data = list()
            # end if
        # end for
        # If we're at the end and there's any batch data left, write it into
        # the table.
        if len(batch_data) > 0:
            self.execute_query_batch(query_string, batch_data)
        # end if
        print(f'Done updating cskg_nodes edge_ids.')
    # end _populate_node_edge_ids

    def _populate_weights(self):
        """
        Populates the weights column in the cskg_edges table.
        """
        print(f'Updating cskg_edges weights...')
        timers = dict()
        timers['start'] = timer()
        timers['last_row_check'] = timer()
        # Read the weights.tsv file.
        with (open(f'{const.DATA_DIRECTORY}/cskg/weights.tsv', encoding='utf8') 
              as weights_file):
            reader = csv.reader(weights_file, delimiter='\t', 
                                quoting=csv.QUOTE_NONE)
            row_count = -1
            query_string = ('''
                            UPDATE cskg_edges
                            SET weight = ?
                            WHERE uri = ?
                            ''')
            batch_data = list()
            batch_size = 10000
            for row in reader:
                # row[0] is the edge uri. Row[2] is the weight as a string.
                row_count += 1
                # Skip the header.
                if row_count == 0:
                    continue
                # weight = weight as float = row[2] as float
                # uri = edge uri = row[0]
                batch_data.append([float(row[2]), row[0]])
                # If we've hit the batch size, write the rows into the table.
                if row_count > 0 and len(batch_data) % batch_size == 0:
                    # Update the rows in the edges table.
                    self.execute_query_batch(query_string, batch_data)
                    # Empty the batch data.
                    batch_data = list()
                    time_since_last = timer() - timers['last_row_check']
                    time_elapsed = timer() - timers['start']
                    print(f'Row {row_count}. Time since last batch: ' +
                          f'{time_since_last}. ' +
                          f'Total elapsed time: {time_elapsed}.')
                    timers['last_row_check'] = timer()
                # end if
            # end for
            # If we've reached the end of the tsv and there's some batch data
            # left, make sure to insert it.
            if len(batch_data) > 0:
                print(f'Row {row_count}, end of tsv. Writing final batch...')
                # Update the rows in the edges table.
                self.execute_query_batch(query_string, batch_data)
            # end if
        # end with
        elapsed_time = timer() - timers['start']
        print(f'Done updating cskg_edges weights. Elapsed time: {elapsed_time}')
    # end _populate_weights

    def get_node(self, node_id: int):
        """
        Get a node from the cskg_nodes table using its id.

        If the node is not in the cache and had to be fetched, also gets all
        the edges incident on the node and gives them to the node. 
        """
        # First, check the cache.
        if node_id in self._node_cache:
            return self._node_cache[node_id]
        # If it's not there, fetch it from the cskg_nodes table.
        query_string = ('''
                        SELECT * FROM cskg_nodes
                        WHERE id = ?
                        ''')
        query_data = [node_id]
        query_result = self.execute_query(query_string, query_data)
        node = self._make_nodes_from_query(query_result)[0]
        #DEBUG
        if node is None:
            print('none node!')
        # Cache the node.
        self._node_cache[node_id] = node
        return node
    # end get_node
    def get_nodes(self, node_ids: list[int]):
        """
        Get a list of nodes from the cskg_nodes table using their ids.
        """
        # Can't use executemany on a SELECT statement, so just have to do them
        # one by one.
        return [self.get_node(node_id) for node_id in node_ids]
    # end get_nodes
        
    def find_nodes(self, search_term: str):
        """
        Finds all cskg nodes that match the search term.

        Returns them as a list of CSKGNode objects.
        """
        timers = dict()
        # First, make sure to match the format of cskg node terms.
        # All lower-case, spaces between the words.
        search_term = search_term.lower()
        search_term = search_term.replace('_', ' ')

        # DEBUG
        if search_term == 'man':
            print('searching for man')

        timers['query_start'] = timer()
        #print(f'Querying concept_net_nodes for {search_term}...')
        # Search for any node whose label matches the search term
        query_data = [search_term]
        query_string = ('''
                        SELECT *
                        FROM cskg_node_labels
                        WHERE label = ?
                        ''')
        query_results = self.execute_query(query_string, query_data)
        # This gets us a list of node ids.
        node_ids = [result_tuple[1] for result_tuple in query_results]
        # Get these nodes.
        nodes = self.get_nodes(node_ids)

        return nodes
    # end find_nodes

    def _make_nodes_from_query(self, query_results: list[tuple]):
        """
        Helper function to make a list of CommonSenseNodes from a list of
        cskg_nodes table query result tuples.
        """
        nodes = list()
        for query_result in query_results:
            node = None
            id = query_result[0]
            uri = query_result[1]
            # Labels are separated by '|'
            labels = query_result[2].split('|')
            # Edge ids are separated by '|'
            edge_ids = query_result[3].split('|')
            # Edge ids are stored as strings. Convert them into integers.
            edge_ids = [int(edge_id) for edge_id in edge_ids]
            # Check for specific knowledge source node types.
            # ConceptNet nodes have uris that are split by '/'
            if len(uri.split('/')) > 1:
                node = ConceptNetNode(id=id,
                                      uri=uri,
                                      labels=labels,
                                      edge_ids=edge_ids)
            # ATOMIC nodes and FrameNetNodes have uris that are split by ':'
            elif len(uri.split(':')) > 1: 
                # ATOMIC nodes have 'at' as the first item in the split.
                if uri.split(':')[0] == 'at':
                    node = AtomicNode(id=id,
                                      uri=uri,
                                      labels=labels,
                                      edge_ids=edge_ids)
                # FrameNet nodes have 'fn' as the first item in the split.
                elif uri.split(':')[0] == 'fn':
                    node = FrameNetNode(id=id,
                                        uri=uri,
                                        labels=labels,
                                        edge_ids=edge_ids)
                # WordNet nodes have 'wn' as the first item in the split.
                elif uri.split(':')[0] == 'wn':
                    node = WordNetNode(id=id,
                                       uri=uri,
                                       labels=labels,
                                       edge_ids=edge_ids)
                else:
                    node = CommonSenseNode(id=id,
                                           uri=uri,
                                           labels=labels,
                                           edge_ids=edge_ids)
                # end else
            else:
                node = CommonSenseNode(id=id,
                                       uri=uri,
                                       labels=labels,
                                       edge_ids=edge_ids)
            # end if else
            nodes.append(node)
        # end for
        return nodes
    # end _make_nodes_from_query

    # DEBUG:
    timer_sums = {'get_edges': 0}
    def get_edges(self, node_id: int):
        """
        Gets all the cskg edges where the node with the id passed in is
        either the start or the end node.
        """
        #print(f'Querying edges for node {node_id}...')
        # First, check the cache.
        if node_id in self._node_edge_cache:
            return self._node_edge_cache[node_id]
        timers = dict()
        timers['start'] = timer()
        query_string = ('''
                        SELECT * FROM cskg_edges
                        WHERE start_node_id = ? OR end_node_id = ?
                        ''')
        query_data = [node_id, node_id]
        query_results = self.execute_query(query_string, query_data)
        edges = self._make_edges_from_query(query_results)
        # Cache the edges for this node.
        self._node_edge_cache[node_id] = edges

        #print(f'Done! Edges Out: {len(start_edges)}' + 
        #      f' Edges In: {len(end_edges)}' +
        #      f' Elapsed time: {timer() - timers["start"]}')
        time_taken = timer() - timers['start']
        CSKGQuerier.timer_sums['get_edges'] += time_taken
        return edges
    # end get_edges

    def get_node_edges(self, node: CommonSenseNode):
        """
        Gets a list of all the CommonSenseEdges for the CommonSenseNode passed 
        in.
        """
        query_string = ('''
                        SELECT * FROM cskg_edges
                        WHERE id = ?
                        ''')
        edges = list()
        for edge_id in node.edge_ids:
            query_results = self.execute_query(query_string, [edge_id])
            edges_made = self._make_edges_from_query(query_results)
            # It's possible all the edges were filtered out of the results,
            # so check for that here.
            if len(edges_made) == 0:
                continue
            edges.append(edges_made[0])
        # end for
        return edges
    # end get_node_edges

    def _make_edges_from_query(self, query_results: list[tuple]):
        """
        Helper function to get a list of CommonSenseEdges from a query result
        from the cskg_edges table.
        """
        # cskg_edges has columns:
        #   0: id | 1: uri | 2: relation | 3: start_node_id | 4: end_node_id
        #   5: start_node_uri | 6: end_node_uri | 7: labels | 8: dimension
        #   9: source | 10: sentence | 11: weight
        # For the label, grab the last word in the uri.
        edges = list()
        for query_result in query_results:
            # Filter out any edges we don't want to use.
            # VisualGenome edges have source='VG'
            if query_result[9] == 'VG':
                continue
            edge = CommonSenseEdge(id=query_result[0], 
                                   uri=query_result[1], 
                                   labels=query_result[7].split('|'),
                                   relation=query_result[2],
                                   start_node_id=query_result[3], 
                                   end_node_id=query_result[4], 
                                   start_node_uri=query_result[5], 
                                   end_node_uri=query_result[6], 
                                   weight=query_result[11], 
                                   dimension=query_result[8],
                                   source=query_result[9],
                                   sentence=query_result[10])
            edges.append(edge)
        # end for
        return edges
    # end _make_edges_from_query
        
# end class CSKGQuerier