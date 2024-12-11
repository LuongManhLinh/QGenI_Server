import socket
import threading
import os
from server_utils import RequestType, ResponseType, Utility
from ids_server import IdsServer
from tfn_server import TfnServer
from server_thread_controller import thread_continous_flags
    

class QGenIServer:
    def __init__(self,
                host='0.0.0.0',
                port=20000, 
                max_client=1
    ) -> None:
        print('Starting server...')
        self.host=host
        self.port=port
        self.max_clent = max_client
        
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.server.bind( (self.host, self.port) )
        except Exception as e:
            self.port += 1
        
        self.track_availability = [True for _ in range(self.max_clent)]

        self.thread_lock = threading.Lock()

        print('Initializing IDS servers...')
        self.ids_servers = [IdsServer() for _ in range(self.max_clent)]

        print('Initializing TFN servers...')
        self.tfn_servers = [TfnServer() for _ in range(self.max_clent)]

    
    def start_server(self,):
        self.server.listen(self.max_clent)
        print(f'Server started on {self.host}:{self.port}')

        while True:
            print('Waiting for client...')
            client_socket, address = self.server.accept()
            print(f'Accepted client {address}')

            try:
                with self.thread_lock:
                    track_idx = -1
                    for idx, available in enumerate(self.track_availability):
                        if available:
                            track_idx = idx
                            break

                if track_idx == -1:
                    print('-' * 10, 'SERVER WENT WRONG', '-' * 10)
                    client_socket.close()
                else:
                    self.track_availability[track_idx] = False
                    thread_continous_flags[address] = True

                    ctrl_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    ctrl_port = self.port + 1 + track_idx
                    client_socket.sendall(Utility.int_to_big_endian(ctrl_port))
                    ctrl_socket.bind((self.host, ctrl_port))
                    ctrl_thread = threading.Thread(
                        target=self.__handle_control_client, args=(track_idx, ctrl_socket, address)
                    )
                    ctrl_thread.start()
                    
                    client_thread = threading.Thread(
                        target=self.__handle_client, args=(track_idx, client_socket, address, ctrl_socket)
                    )
                    client_thread.start()

            except Exception as e:
                print(f"Error accepting client: {e}")
                client_socket.sendall(Utility.int_to_big_endian(ResponseType.SERVER_ERROR))
                client_socket.close()


    def __handle_client(self, track_idx, client_socket, address, ctrl_socket):
        first_4_bytes = client_socket.recv(4)
        request_type = Utility.big_endian_to_int(first_4_bytes)
        try:
            if request_type == RequestType.IMG_FIND_SIMILAR_ONLY:
                self.ids_servers[track_idx].handle_find_similar(client_socket, address)

            elif request_type == RequestType.TFN_CHECK:
                self.tfn_servers[track_idx].handle_tfn_checking(client_socket, address)
  
            else:
                client_socket.sendall(
                    Utility.int_to_big_endian(ResponseType.INVALID_REQUEST)
                )

        except Exception as e:
            client_socket.sendall(
                Utility.int_to_big_endian(ResponseType.SERVER_ERROR)
            )
            print(f"Error handling client {address}: {e}")
        
        finally:
            client_socket.close()
            ctrl_socket.close()
            print(f"Disconnected client {address}")
            with self.thread_lock:
                self.track_availability[track_idx] = True
            
            temp_folder_path = 'img/client'
            for filename in os.listdir(temp_folder_path):
                file_path = os.path.join(temp_folder_path, filename)
                os.remove(file_path)


    def __handle_control_client(self, track_idx, ctrl_socket, transfer_addr):
        ctrl_socket.listen(1)
        client_ctrl_socket, _ = ctrl_socket.accept()
        print(f"Accepted control client {transfer_addr}")

        ctrl_bytes = client_ctrl_socket.recv(4)
        ctrl_type = Utility.big_endian_to_int(ctrl_bytes)
        if ctrl_type == ResponseType.CLIENT_ERROR:
            print(f'Control client error at {transfer_addr}')
            client_ctrl_socket.close()
            ctrl_socket.close()
            thread_continous_flags[transfer_addr] = False
            self.track_availability[track_idx] = True





