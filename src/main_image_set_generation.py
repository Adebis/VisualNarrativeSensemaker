from image_set_generation.image_set_generator import ImageSetGenerator
from image_set_generation.data_handler import DataHandler
from image_set_generation.evaluator import Evaluator
from timeit import default_timer as timer

def main():
    print ("hey :) main for ImageSetGenerator")
    images_directory = 'C:/Users/zevsm/Documents/GitHub/VisualNarrativeSensemaker/data/inputs/images'
    annotations_directory = 'C:/Users/zevsm/Documents/GitHub/VisualNarrativeSensemaker/data/inputs/scene_graphs'
    #image_set_generator = ImageSetGenerator(annotations_directory=annotations_directory,
    #                                        images_directory=images_directory,
    #                                        load_caches=True)
    
    #image_set_gen_start = timer()
    #image_sets = image_set_generator.generate_object_linked_image_sets(500)
    #print(f'Image sets generated. Elapsed time: {timer() - image_set_gen_start}s.')

    evaluator = Evaluator()
    evaluator.evaluate()

    print("done :)")
    #data_handler = DataHandler(load_caches = True)

    # Get 500 image sets.

    # throw -> play
    # play -> HasFirstSubevent -> throw
    # 57861 - /c/en/play
    # 150103 - /c/en/throw
    # encoded :)

    # throw -> miss
    # throw -> Causes -> miss
    # 150103 - /c/en/throw
    # 71487 - /c/en/miss
    # encoded :)

    # throw -> hit
    # throw -> Causes -> hit
    # 150103 - /c/en/throw
    # 57237 - /c/en/hit
    # encoded :)

    # go_to_park -> play
    # play -> HasPrerequisite -> go_to_park
    # 57861 - /c/en/play
    # 1072827 - /c/en/go_to_park
    # encoded :)

    # go_to_beach -> walk
    # walk -> HasPrerequisite -> go_to_beach
    # 13831 - /c/en/walk
    # 3525833 - /c/en/go_to_beach
    # encoded :)

    # play -> throw
    # play -> Causes -> throw
    # 57861 - /c/en/play
    # 150103 - /c/en/throw
    # encoded :)

    # throw -> catch
    # throw -> Causes -> catch
    # 150103 - /c/en/throw
    # 80433 - /c/en/catch
    # encoded :)

    #data_handler.write_cs_edge(
    #    start_node_id=150103,
    #    end_node_id=80433,
    #    relation='/r/Causes'
    #)

    # Saving dynamic caches saves the CSKGQuerier's caches.
    #data_handler._save_dynamic_caches()


    # Build database tables
    # Full dataset tok 10897s at about 0.1s per image.
    #image_set_generator._data_handler.generate_database_tables()

    # There are 108,077 images.
    # Parsing 9000 images took about 18 minutes.
    # Parsing 10000 - 20000 took 996 seconds.
    # Parsing 20000 - 30000 took 936 seconds.
    # Full dataset takes about 3 hours.
    # Parsed: 
    #print("Number of images: " + str(len(image_set_generator._get_all_image_ids())))

    #input('Press enter to continue.')
    
    #image_set_generator.generate_image_objects_table()

    #image_set_generator.generate_image_actions_table(
    #    lower_bound=0, 
    #    upper_bound=108077
    #)
    # Of the 7290 distinct concept net nodes connected to actions
    # in the parsed images, 609 had causal edges at all and 6681 did not. 
    # There are 5700 causal links in the causal_links table.
    # There are 505 in the action_to_action_causal_links table.
    #image_set_generator.generate_causal_link_table()
    #image_set_generator._data_handler.generate_causal_links_table()

    # The image links table has 91,815,033 rows. 
    #image_set_generator.generate_image_links_table()

    # Generate an image set from the first number_of_images VGG images.
    #output_file_directory = const.INPUT_DIRECTORY + '/image_sets'
    #image_set_generator.generate_image_sets(number_of_images=1000,
    #                                        output_file_path=output_file_path)
    #image_set_generator.generate_targeted_image_sets(output_file_directory,
    #                                                 target_action='compete',
    #                                                 name='compete_continuity')

    #image_set_generator.count_actions()

    # There are 108,077 images.
    # Parsing 10000 images took 923 seconds.
    # Full dataset took 9913 seconds.
    # 2.75 hours
    # Parsed: 
    #   0 
    # Parsing: 0 
    image_count_start = 0
    image_count_end = 108077
    #image_count_end = 100
    #image_set_generator._data_handler.generate_image_object_action_pairs_table(
    #    image_count_start,
    #    image_count_end
    #)
    # Table has 371118 rows.

    #image_set_generator._generate_multi_causal_links_table()

    

    search_uris = []
    #search_uris.append('/c/en/eat')
    #search_uris.append('/c/en/smile')
    #search_uris.append('/c/en/think')
    #search_uris.append('/c/en/listen')
    #search_uris.append('/c/en/sleep')
    #search_uris.append('/c/en/rest')
    #search_uris.append('/c/en/learn')
    #search_uris.append('/c/en/dance')
    #search_uris.append('/c/en/buy')
    #search_uris.append('/c/en/talk')
    #search_uris.append('/c/en/relax')
    #search_uris.append('/c/en/play')
    #number_of_sets = 10
    #for target_action_uris in all_target_action_uris:
    #    print(f'Calling generate image sets for {target_action_uris[0]}')
    # end for
    
    #search_uri = '/c/en/eat'
    #search_uri = '/c/en/cook'
    # play -> rest, relax, smile, laugh
    #action_terms = ['cook', 'eat']
    #action_terms = ['play', 'rest']
    #action_terms = ['buy', 'pay']
    #action_terms = ['rehearse', 'perform']
    # Some good ones maybe
    #action_terms = ['stretch', 'run', 'rest']
    #action_terms = ['trip', 'fall', 'land']
    #action_terms = ['organize', 'clean', 'relax']
    # 0 image sets
    #action_terms = ['hike', 'sit', 'relax']
    # 30 image sets, not very good. Last image is just a random person talking.
    #action_terms = ['cook', 'eat', 'talk']
    # 31 image sets, not very good. Wash leads to eat is a stronger causal
    # connection than eat leads to wash. 
    #action_terms = ['cook', 'eat', 'wash']
    # 1 image set. Not good.
    #action_terms = ['relax', 'sleep', 'awaken']
    # 8 image sets, not good.
    #action_terms = ['choose', 'buy', 'pay']
    # 3 image sets, not good.
    #action_terms = ['train', 'compete', 'lose']
    # 4 image sets, not good.
    #action_terms = ['train', 'compete', 'win']
    # 1 image set, not good.
    #action_terms = ['practice', 'sing', 'bow']
    # 15 image sets, 1 good.
    #action_terms = ['jump', 'dive', 'swim']
    # 4 image sets. Funny but bad.
    #action_terms = ['prepare', 'cook', 'eat']

    action_terms = ['prepare', 'cook', 'eat']

    #action_terms = ['stretch', 'run', 'rest']
    #image_set_generator.generate_image_sets(action_terms)

    # There are 415 cs nodes with exclusively multi-step causal links with other
    # cs nodes.
    # There are 5209 such multi-step causal links.
    # Done:
    #   0 - 415

    #image_set_generator.print_multi_causal_links(
    #    lower=0,
    #    upper=415
    #)

    #image_set_generator.print_causal_links(lower=0, upper=1000)

    '''
    
    Please look through this text file and tell me which of the lines makes sense 
    logically (not syntactically). Do so without using any python code. Don't bother 
    printing out the lines in this chat, just export your results as a text file. 
    The name of your text file should be the same as the name of the text file I gave you, 
    except with "parsed_" at the start. If you cannot create the file, just print the lines 
    out in chat.

    Please look through these text files and tell me which of the lines makes sense logically (not syntactically). Do so without using any python code. Don't bother printing out the lines in this chat, just export your results as an output text file for each text file passed in. The name of each output text file should be the same as the name of the text file you read to make it, except with "parsed_" at the start. If you cannot create the files, just print the lines out in chat. Take your time.    

    '''

    #image_set_generator.read_multi_causal_links()

    # Have the generator save its caches.
    #image_set_generator.save_caches()

    print('done :)')
# end main

# __name__ will be __main__ if we're running the program
# from this script. If another module calls this script,
# then __name__ is the name of the calling module. 
if __name__ == "__main__":    
    main()