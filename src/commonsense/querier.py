import sqlite3
from sqlite3 import Error
from abc import abstractmethod
from timeit import default_timer as timer

from nltk.corpus import wordnet as wn
import spacy

import constants as const

class CommonSenseQuerier:
    """
    Base class for an object that queries and managing tables in the 
    commonsense_knowledge database.

    Attributes
    ----------
    database_file_path : str
        The file path of the database this database manager manages.

        Default value is the directory of the concepts database, as defined in
        const.DATABASE_FILE_PATH
    nlp : Language
        The nlp model object for spacy. Stored as an attribute so it only has
        to be made once.
    """
    def __init__(self, db_file_path: str=None):
        if db_file_path == None:
            self.database_file_path = const.DATABASE_FILE_PATH
        else:
            self.database_file_path = db_file_path
        # Make an nlp object out of the pipeline package.
        # Download using:
        #   python -m spacy download en_core_web_lg
        # Only have to do once per machine.
        spacy_timer = timer()
        print('CommonsenseQuerier.__init__ : Loading en_core_web_lg...')
        self.nlp = spacy.load('en_core_web_lg')
        print(f'Done! Elapsed time: {timer() - spacy_timer}')
    # end __init__

    @abstractmethod
    def find_nodes(self, search_term: str):
        """
        Finds all CommonSenseNodes that match the search term.
        """
        pass
    # end find_node

    @abstractmethod
    def get_node(self, node_id: int):
        """
        Gets a CommonSenseNode using its id.
        """
        pass
    # end get_node

    @abstractmethod
    def get_edges(self, node_id: int):
        """
        Gets all the CommonSenseEdges where the node with the id passed in is
        either the start or the end node.
        """
        pass
    # end get_edges

    def execute_query(self, query_string: str, query_data=None):
        """
        Execute a sql query in the concept_data database.

        Parameters
        ----------
        query_string : str
            The full string for the query.
        command_data : Any, optional
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
        connection = sqlite3.connect(self.database_file_path)
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

    def execute_query_batch(self, query_string: str, query_data):
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
        connection = sqlite3.connect(self.database_file_path)
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
            print(f'Querier.execute_query : Error executing sql ' +
                  f'query \"{query_string}\": {e}' +
                  f'\ndata:{query_data}')
            return_value = None
        # end try
        # Whether the command was executed successfully or not,
        # close the connection.
        connection.close()
        return return_value
    # end execute_query_batch
        
# end class ConceptNetQuerier

def find_synset(term: str, pos: str):
    """
    Finds a synset for a word or phrase.

    Parameters
    ----------
    term : str
        A word or phrase to find a synset for. 
    pos : str
        A part-of-speech for the synset. Should match one of NLTK WordNet's
        part-of-speech definitions (i.e. wn.VERB, wn.NOUN)
    
    Returns
    -------
    synset : wn.Synset | None
        If a synset was found for the term, returns it. If no synset could
        be found, returns False.
    """
    # First, normalize the term.
    # Replace make it lower-case and replace all spaces with underscores.
    term = term.lower()
    term = term.replace(' ', '_')
    # Split the term up by underscore.
    term_split = term.split('_')
    # If there is more than one word in the term, try adjacent pairs of
    # words until we find a synset.
    synsets = list()
    if len(term_split) > 1:
        # Stop at the second-to-last word in the term.
        for i in range(0, len(term_split) - 2):
            # Try the two-word phrase made of the current word and
            # the next word.
            phrase = (f'{term_split[i]}_{term_split[i+1]}')
            synsets = wn.synsets(phrase, pos)
            if not len(synsets) == 0:
                break
        # end for
        # If we've found synsets from a two-word phrase, return the synset
        # for the most common sense of the word.
        if not len(synsets) == 0:
            return synsets[0]
    # end if
    # In all other cases, try to find a synset for the last word.
    synsets = wn.synsets(term_split[-1], pos)
    if not len(synsets) == 0:
        return synsets[0]
    else:
        return None
# end find_synset

def main():
    # Test some stuff!
    print("hey :) main in database")

    print("Done!")
# end main

if __name__ == '__main__':
    main()
