import socket
import time
import threading
import json
from timeit import default_timer as timer

class Server():
    """
    
    """

    ip: str
    port: int
    socket_: socket

    # A dictionary mapping commands to callback functions.
    callback_map: dict

    # Whether the server is running right now.
    running: bool
    # Whether the server is connected to a client right now.
    client_connected: bool

    def __init__(self, callback_functions: list):
        # Build the callback map.
        self.callback_map = dict()
        for callback_function in callback_functions:
            self.callback_map[callback_function.__name__] = callback_function
        print("Socket handler initialized.")
    # end __init__
        
    def start(self, ip: str, port: int):
        """
        
        """
        print("Starting server")
        self.ip = ip
        self.port = port
        self.socket_ = socket.socket()
        self.socket_.bind((ip, port))
        # Queue up as many as 5 connect requests before refusing connections.
        # This is the normal maximum.
        self.socket_.listen(5)

        self.running = True
        self.client_connected = False

        # Start a thread to await a connection from a client.
        # Return the thread so the main app can wait for the thread to end.
        listen_thread = threading.Thread(target=self.listen)
        listen_thread.start()
        return listen_thread

    # end start

    def stop(self):
        self.running = False
        
    def listen(self):
        """
        
        """
        try:
            while self.running:
                print('Server awaiting connection...')
                # Wait until we establish a connection with a client.
                client_socket, address = self.socket_.accept()
                print(f'Connection received from {address}. Listening...')
                self.client_connected = True
                while self.client_connected:
                    print('Checking for data...')
                    received_data = client_socket.recv(4096)
                    if not received_data:
                        continue
                    else:
                        received_str = received_data.decode("UTF-8")
                        print(f'Data received: {received_str}')

                        return_message = self.handle_message(message=received_str)

                        print(f'Sending return message: {return_message}')
                        # Convert string to bytes and send over network.
                        return_message_bytes = return_message.encode("UTF-8")
                        client_socket.sendall(return_message_bytes)
                # end while
                # If we're done running, close connection with client.
                client_socket.shutdown(socket.SHUT_RDWR)
                client_socket.close()
            # end while
        # end try
        except Exception as e:
            print(f'Error in server.listen: {e}. Ending listening loop.')
            dummy = input('Press enter to continue...')
        
    # end listen
                
    def handle_message(self, message: str):
        """
        
        """

        # Split by '?'.
        # First item is the command.
        message_split = message.split('?')
        command = message_split[0]
        if command == 'execute_function':
            # The next item is the function's json.
            command_dict = json.decoder.JSONDecoder().decode(message_split[1])
            # Find and take out the function name, then use the rest of the
            # decoded json dict as keyword args for the function.
            function_name = command_dict['function_name']
            del command_dict['function_name']

            return self.callback_map[function_name](**command_dict)
        # end if
        # Stop the server and close the app.
        elif command == 'stop':
            return self.callback_map[command]()
        # Disconnect the client that sent this message from the server.
        elif command == 'disconnect':
            self.client_connected = False
            return 'disconnecting'
    # end parse_message

    """
    def listen(self, host_ip: str, host_port: int):
        
        Establish a socket connection to a specified host IP and port
        and listen for it in a loop.

        self.host_ip = host_ip
        self.host_port = host_port
        # Open a socket connection.
        self.socket_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_.connect((self.host_ip, self.host_port))

        elapsed_time = 0
        start_time = timer()
        counter = 0
        while True:
            time.sleep(0.5)
            counter += 1
            elapsed_time = timer() - start_time
            # Convert elapsed time to string.
            elapsed_time_str = str(elapsed_time)

            counter_str = str(counter)
            # Convert string to bytes and send over network.
            #self.socket_.sendall(counter_str.encode("UTF-8"))
            # Receive data back from Unity.
            received_data = self.socket_.recv(1024).decode("UTF-8")
            print(received_data)
    # end listen
    """

# end class SocketHandler