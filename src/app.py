import socket
import time
from timeit import default_timer as timer

from network_handling.server import Server
from parameters import ParameterSet
from sensemaker import SenseMaker

class SensemakerApp:

    server: Server
    sensemaker: SenseMaker

    def __init__(self):
        print("Initializing sensemaker app.")
        callback_functions = list()
        callback_functions.append(self.run_sensemaker)
        callback_functions.append(self.stop)
        self.sensemaker = SenseMaker()
        self.server = Server(callback_functions=callback_functions)
    # end __init__

    def start(self):
        print("Starting sensemaker app.")
        host_ip = "127.0.0.1"
        host_port = 25001
        listen_thread = self.server.start(ip=host_ip, port=host_port)
        return listen_thread
    # end run

    def stop(self):
        print("Stopping sensemaker app.")
        # Tell the server to stop.
        self.server.stop()
        return "App stopped"
    # end stop
        
    def run_sensemaker(self, **kwargs):
        '''
        **kwargs:
            image_set_ids - a list of the ids of the images for the set to run
                sensemaking over.
            parameter_sets - a list of parameter sets, where each parameter
                set is a dictionary with parameter names as keys and parameter
                values as values. 
        '''

        image_set_ids = [int(image_id) for image_id in kwargs['image_set_ids']]
        # Can enter a test set number instead of 3 image ids.
        if len(image_set_ids) == 1 and image_set_ids[0] == 13:
            # Set 13 - kitchen, bike ride, picnic
            image_set_ids = [2402873, 2391830, 2406899]
        elif len(image_set_ids) == 1 and image_set_ids[0] == 14:
            # Set 14 - Field bike ride, bike stop, road bike ride (all with dogs)
            image_set_ids = [2384081, 2361867, 2329428]
        elif len(image_set_ids) == 1 and image_set_ids[0] == -1:
            image_set_ids = [225, 1324, 621]
        print(f'Image set ids: {image_set_ids}')

        # Script has to be called while current working directory is wherever VisualNarrativeSensemaker,
        # the folder that contains data and src, is.
        #cwd = os.getcwd()
        #print(f'Current working directory: {cwd}')

        # Make a sensemaker and run sensemaking.
        #sensemaker = SenseMaker()
        # Parameters
        parameter_sets = list()
        for pset_dict in kwargs['parameter_sets']:
            pset = ParameterSet(**pset_dict)
            parameter_sets.append(pset)
        '''
        pset_default = ParameterSet(name='default',
                                    visual_sim_ev_weight=1.0,
                                    attribute_sim_ev_weight=1.0,
                                    causal_path_ev_weight=1.0,
                                    continuity_ev_weight=1.0,)
        '''
        #parameter_sets.append(pset_make_relationships)
        #parameter_sets.append(pset_choose_carefully)
        #parameter_sets.append(pset_default)
        knowledge_graph, hypotheses = self.sensemaker.perform_sensemaking(
            parameter_sets=parameter_sets, image_ids=image_set_ids)

        print("done!")
        return "Sensemaking complete"
    # end run_sensemaker

# end class SensemakerApp


def main():
    print ("hey :)")
    app = SensemakerApp()
    listen_thread = app.start()
    # Wait for the listen thread to end here. 
    listen_thread.join()

    print("Program stopped.")
    #dummy = input("Press any key to exit...")

    # Send test message "run_sensemaker 14" to server here.
    '''
    test_message = "run_sensemaker 14"
    print(f'Test message: {test_message}')
    #app.server.handle_message("run_sensemaker 14")
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host_ip = app.server.ip
    host_port = app.server.port
    client_socket.connect((host_ip, host_port))
    client_socket.sendall(test_message.encode("UTF-8"))
    return_data = client_socket.recv(1024)
    return_message = return_data.decode("UTF-8")
    print(f'Return message: {return_message}')
    '''
# end main

# __name__ will be __main__ if we're running the program
# from this script. If another module calls this script,
# then __name__ is the name of the calling module. 
if __name__ == "__main__":    
    main()