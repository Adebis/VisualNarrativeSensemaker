import atexit
import pickle
import os.path
import sqlite3
from sqlite3 import Error
import json
import csv
import re
import hashlib
import random
import itertools
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

    _node_cache: dict[int, CommonSenseNode]
    _node_edge_cache: dict[int, list[CommonSenseEdge]]
    _edge_cache: dict[int, CommonSenseEdge]

    use_caches: bool

    def __init__(self, db_file_path: str = None, use_caches = True):
        super().__init__(db_file_path)
        # Cache a mapping of node ids to CommonSenseNode objects.
        # Try to load it from file. If it doesn't exist yet, this will
        # result in an empty dict.
        self._node_cache = self._try_load_dict_cache('node_cache')
        # Cache a mapping of node ids to lists of CommonSenseEdge objects.
        # Try to load it from file. If the file doesn't exist yet, this will
        # result in an empty dict.
        self._node_edge_cache = self._try_load_dict_cache('node_edge_cache')
        # Cache a mapping of edge ids to CommonSenseEdge objects.
        # Try to load it from file. If it doesn't exist yet, this will result
        # in an empty dict.
        self._edge_cache = self._try_load_dict_cache('edge_cache')
        self.use_caches = True
        self.cache_size_limit = 500000
        self._initialize_database()
    # end __init__

    def save(self):
        """
        Writes the querier's caches to file.
        """
        self._write_dict_cache('node_cache', self._node_cache)
        self._write_dict_cache('node_edge_cache', self._node_edge_cache)
        self._write_dict_cache('edge_cache', self._edge_cache)
    # end on_exit

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

    def get_node(self, node_id: int, force_fetch: bool=False):
        """
        Get a CommonSenseNode using its id.

        If this is the first time getting this CommonSenseNode, fetches from the 
        cskg_nodes table and locally caches the node for subsequent fetches.
        """
        # First, check the cache if we're not forcing a fetch of this node.
        if not force_fetch and node_id in self._node_cache:
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
            print('CSKGQuerier.get_node: Error, none node!')
        # Cache the node.
        #if self.use_caches:
        # Obey the cache size limits.
        if len(self._node_cache) > self.cache_size_limit:
            amount_to_remove = int(self.cache_size_limit / 10)
            self._node_cache = dict(
                itertools.islice(
                    self._node_cache.items(), 
                    self.cache_size_limit - amount_to_remove
                    )
                )
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
    
    def get_node_by_uri(self, node_uri: str):
        '''
        Gets a CommonSenseNode using its URI.

        Slower than getting it using its id.
        '''
        return self.get_node(self.get_node_id(node_uri))
    # end get_node_by_uri

    def get_node_id(self, node_uri: str):
        '''
        Gets the id for a node using its uri.

        Fetches it from the database. 
        '''
        query_string = ('''
                        SELECT * FROM cskg_nodes
                        WHERE uri = ?
                        ''')
        query_data = [node_uri]
        query_result = self.execute_query(query_string, query_data)
        return query_result[0][0]
    # end get_node_id
        
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
        # If there were no results, try removing hyphens and searching again.
        if len(query_results) == 0:
            search_term = search_term.replace('-', ' ')
            query_data = [search_term]
            query_results = self.execute_query(query_string, query_data)
        # end if
        # This gets us a list of node ids.
        node_ids = [result_tuple[1] for result_tuple in query_results]
        # Get these nodes.
        nodes = self.get_nodes(node_ids)

        return nodes
    # end find_nodes

    def _make_nodes_from_query(self, query_results: list[tuple]) -> list[CommonSenseNode]:
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
    def get_edges(self, node_id: int,
                  force_fetch: bool=False) -> list[CommonSenseEdge]:
        """
        Gets all the cskg edges where the node with the id passed in is
        either the start or the end node.

        Caches the edges in _edge_cache and _node_edge_cache.
        """
        #print(f'Querying edges for node {node_id}...')
        # First, check the cache.
        if not force_fetch and node_id in self._node_edge_cache:
            return self._node_edge_cache[node_id]
        timers = dict()
        timers['start'] = timer()
        query_string = ('''
                        SELECT * FROM cskg_edges
                        WHERE start_node_id = ? OR end_node_id = ?
                        ''')
        query_data = [node_id, node_id]
        query_results = self.execute_query(query_string, query_data)
        # If the node had no edges, return an empty list.
        if query_results is None:
            print(f'cskg_querier.get_edges: No edges found for node {node_id}')
            return list()
        edges = self._make_edges_from_query(query_results)
        # Cache the edges.
        # Obey cache size limits.
        for edge in edges:
            if not edge.id in self._edge_cache:
                if len(self._edge_cache) > self.cache_size_limit:
                    amount_to_remove = int(self.cache_size_limit / 10)
                    self._edge_cache = dict(
                        itertools.islice(
                            self._edge_cache.items(), 
                            self.cache_size_limit - amount_to_remove
                            )
                        )
                self._edge_cache[edge.id] = edge
            # end if
        # end for
        # Cache the edges for this node.
        if len(self._node_edge_cache) > self.cache_size_limit:
            amount_to_remove = int(self.cache_size_limit / 10)
            self._node_edge_cache = dict(
                itertools.islice(
                    self._node_edge_cache.items(), 
                    self.cache_size_limit - amount_to_remove
                    )
                )
        self._node_edge_cache[node_id] = edges

        #print(f'Done! Edges Out: {len(start_edges)}' + 
        #      f' Edges In: {len(end_edges)}' +
        #      f' Elapsed time: {timer() - timers["start"]}')
        time_taken = timer() - timers['start']
        CSKGQuerier.timer_sums['get_edges'] += time_taken
        return edges
    # end get_edges

    def get_edge(self, edge_id) -> CommonSenseEdge | None:
        '''
        Gets a CommonSenseEdge by its id.

        If it's not in the cache, fetches from the database and caches it.
        '''
        if edge_id in self._edge_cache:
            return self._edge_cache[edge_id]
        # end if

        query_string = ('''
            SELECT * FROM cskg_edges
            WHERE id = ?
        ''')
        query_data = [edge_id]
        query_results = self.execute_query(query_string, query_data)
        edges = self._make_edges_from_query(query_results)
        # There should only be one edge. Cache it, then return it.
        edge = edges[0]

        # Obey cache size limits.
        if len(self._edge_cache) > self.cache_size_limit:
            amount_to_remove = int(self.cache_size_limit / 10)
            self._edge_cache = dict(
                    itertools.islice(
                        self._edge_cache.items(), 
                        self.cache_size_limit - amount_to_remove
                        )
                    )
            # end for
        # end if
            
        self._edge_cache[edge_id] = edge
        
        return edge
    # end get_edge

    def _make_edges_from_query(self, query_results: list[tuple]) -> list[CommonSenseEdge]:
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

    # A map of relations to labels.
    _relation_label_map = {'/r/HasFirstSubevent': 'has first subevent',
                           '/r/Causes': 'causes',
                           '/r/HasLastSubevent': 'has last subevent',
                           '/r/HasPrerequisite': 'has prerequisite',
                           '/r/CausesDesire': 'causes desire'}
    # A map of relations to dimensions.
    _relation_dimension_map = {'/r/HasFirstSubevent': 'temporal',
                               '/r/Causes': 'temporal',
                               '/r/HasLastSubevent': 'temporal',
                               '/r/HasPrerequisite': 'temporal',
                               '/r/CausesDesire': 'desire'}
    def write_edge(self, start_node_id: int, end_node_id: int, relation: str):
        '''
        Write an edge into the cskg_edges table between two commonsense nodes,
        identified by their ids.

        Relation should be in uri form, i.e. /r/{relation}
        '''
        # First, make the cskg_edges row.
        # Parts of a cskg_edges row:
        # 0 - id
        #   Should start at 6000000 and count up.
        # 1 - uri
        #   '{start_node_uri}-{relation}-{end_node_uri}-0000
        # 2 - relation
        # 3 - start_node_id
        # 4 - end_node_id
        # 5 - start_node_uri
        # 6 - end_node_uri
        # 7 - labels
        #   Grab the label for the relation from the _relation_label_map.
        # 8 - dimension
        #   Grab the dimension from the _relation_dimension_map.
        # 9 - source
        #   'CN'
        # 10 - sentence
        #   ''
        # 11 - weight
        #   1.0f
        
        # Count the number of edges with an id greater than or equal to
        # 6,000,000. Add that to 6,000,000, and that's what the id of this edge
        # should be. 
        query = ('''
            SELECT COUNT(*)
            FROM cskg_edges
            WHERE id >= 6000000
        ''')
        result = self.execute_query(query)
        count = result[0][0]
        id = 6000000 + count
        #id = 6000000

        # Get the start and end nodes so we can get their uris. 
        start_node = self.get_node(start_node_id)
        end_node = self.get_node(end_node_id)

        start_node_uri = start_node.uri
        end_node_uri = end_node.uri
        
        # Make the edge's uri.
        uri = f'{start_node_uri}-{relation}-{end_node_uri}'

        labels = self._relation_label_map[relation]
        dimension = self._relation_dimension_map[relation]
        source = 'CN'
        sentence = ''
        weight = 1.0

        row_data = [
            id,
            uri,
            relation,
            start_node_id,
            end_node_id,
            start_node_uri,
            end_node_uri,
            labels,
            dimension,
            source,
            sentence,
            weight
        ]

        # Write the row into the database.
        query = ('''
            INSERT INTO cskg_edges
            (id, uri, relation, start_node_id, end_node_id, start_node_uri,
             end_node_uri, labels, dimension, source, sentence, weight)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''')
        result = self.execute_query(query, row_data)

        # Next, add the new edge's id to the end of the edge_ids list for
        # the start and end nodes in the cskg_nodes table.
        # If the edge id is already there, don't update it.
        if not id in start_node.edge_ids:
            # First, fetch the node's original row.
            query = ('''
                SELECT * FROM cskg_nodes
                WHERE id=?
            ''')
            start_node_row = self.execute_query(query, [start_node_id])[0]
            # Get the original list of edge ids.
            start_node_edge_list = start_node_row[3]
            # Add '|{new_edge_id} to the end of that list.
            start_node_edge_list += f'|{id}'
            # Update the row's edge_ids column with this modified list.
            query = ('''
                UPDATE cskg_nodes
                SET edge_ids=?
                WHERE id=?
            ''')
            result = self.execute_query(query, [start_node_edge_list, start_node_id])

        if not id in end_node.edge_ids:
            # Do the same for the end node.
            query = ('''
                SELECT * FROM cskg_nodes
                WHERE id=?
            ''')
            end_node_row = self.execute_query(query, [end_node_id])[0]
            # Get the original list of edge ids.
            end_node_edge_list = end_node_row[3]
            # Add '|{new_edge_id} to the end of that list.
            end_node_edge_list += f'|{id}'
            # Update the row's edge_ids column with this modified list.s
            query = ('''
                UPDATE cskg_nodes
                SET edge_ids=?
                WHERE id=?
            ''')
            result = self.execute_query(query, [end_node_edge_list, end_node_id])
        # end if

        # Finally, fetch the start node, end node, and start and end node
        # edges to update the caches.
        start_node = self.get_node(node_id=start_node_id, force_fetch=True)
        end_node = self.get_node(node_id=end_node_id, force_fetch=True)
        start_node_edges = self.get_edges(node_id=start_node_id, force_fetch=True)
        end_node_edges = self.get_edges(node_id=start_node_id, force_fetch=True)
    # end write_edge


    def _try_load_dict_cache(self, dict_name):
        '''
        Try and load one of the dictionary caches from file.
        Returns an empty dict if the file is not found. 
        '''
        # Load from cache if possible.
        cache_dict_file_name = f'{dict_name}.pickle'
        cache_dict_file_directory = const.DATA_DIRECTORY + '/'
        cache_dict_file_path = cache_dict_file_directory + cache_dict_file_name
        cache_dict = dict()
        # Check if the cache file exists before trying to read it.
        if os.path.exists(cache_dict_file_path):
            cache_dict = pickle.load(open(cache_dict_file_path, 'rb'))
            return cache_dict
        # end if
        else:
            return dict()
    # end _try_load_dict_cache

    def _write_dict_cache(self, dict_name, dict_to_cache):
        '''
        Write one of the dictionary caches to file.
        '''
        cache_dict_file_name = f'{dict_name}.pickle'
        cache_dict_file_directory = const.DATA_DIRECTORY + '/'
        cache_dict_file_path = cache_dict_file_directory + cache_dict_file_name
        with open(cache_dict_file_path, 'wb') as output_file:
            pickle.dump(dict_to_cache, output_file)
        # end with
    # end _write_dict_cache

        
# end class CSKGQuerier