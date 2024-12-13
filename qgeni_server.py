import socket
import threading
import os
from server_utils import RequestType, ResponseType, Utility
from ids_server import IdsServer
from tfn_server import TfnServer
from server_thread_controller import thread_continous_flags
from api import EmailAPI
    

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
        
        self.transfer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.transfer_socket.bind( (self.host, self.port) )
        self.control_socket.bind( (self.host, self.port + 1) )
        
        self.num_working = 0

        print('Initializing IDS servers...')
        self.ids_servers = [IdsServer() for _ in range(self.max_clent)]

        print('Initializing TFN servers...')
        self.tfn_servers = [TfnServer() for _ in range(self.max_clent)]

    
    def start_server(self,):
        print(f'Server started on {self.host}:{self.port}')

        control_thread = threading.Thread(target=self.__handle_control_client)
        control_thread.start()

        self.transfer_socket.listen(self.max_clent)
        
        while True:
            print('Waiting for client...')
            client_socket, address = self.transfer_socket.accept()
            print(f'Accepted client {address}')

            try:
                if self.num_working >= self.max_clent:
                    print('-' * 10, 'SERVER IS BUSY', '-' * 10)
                    client_socket.sendall(Utility.int_to_big_endian(ResponseType.SERVER_BUSY))
                    client_socket.close()
                else:
                    self.num_working += 1
                    thread_id = self.port + self.num_working

                    client_socket.sendall(Utility.int_to_big_endian(thread_id))

                    thread_continous_flags[thread_id] = True
                    
                    client_thread = threading.Thread(
                        target=self.__handle_client, args=(self.num_working - 1, client_socket, thread_id)
                    )
                    client_thread.start()

            except Exception as e:
                print(f"Error accepting client: {e}")
                client_socket.sendall(Utility.int_to_big_endian(ResponseType.SERVER_ERROR))
                client_socket.close()


    def __handle_client(self, track_idx, client_socket, thread_id):
        first_4_bytes = client_socket.recv(4)
        request_type = Utility.big_endian_to_int(first_4_bytes)
        try:
            if request_type == RequestType.IMG_FIND_SIMILAR_ONLY:
                self.ids_servers[track_idx].handle_find_similar(client_socket, thread_id)

            elif request_type == RequestType.TFN_CHECK:
                self.tfn_servers[track_idx].handle_tfn_checking(client_socket, thread_id)

            elif request_type == RequestType.VERIFICATION:
                QGenIServer.__handle_verification(client_socket, thread_id)
  
            else:
                client_socket.sendall(
                    Utility.int_to_big_endian(ResponseType.INVALID_REQUEST)
                )

        except Exception as e:
            client_socket.sendall(
                Utility.int_to_big_endian(ResponseType.SERVER_ERROR)
            )
            print(f"Error handling client {thread_id}: {e}")
        
        finally:
            client_socket.close()
            print(f"Disconnected client {thread_id}")
            self.num_working  -= 1
            if (self.num_working < 0):
                self.num_working = 0
            
            temp_folder_path = 'img/client'
            for filename in os.listdir(temp_folder_path):
                file_path = os.path.join(temp_folder_path, filename)
                os.remove(file_path)


    def __handle_control_client(self):
        self.control_socket.listen(self.max_clent)

        while True:
            client_socket, _ = self.control_socket.accept()
            print(f"Accepted control client")

            client_thread = threading.Thread(
                target=self.__handle_control_each_client, args=(client_socket,)
            )

            client_thread.start()
        

    def __handle_control_each_client(self, client_socket):
        id_bytes = client_socket.recv(4)
        thread_id = Utility.big_endian_to_int(id_bytes)

        print(f'Control client error at {thread_id} and will be stopped')

        client_socket.close()
        thread_continous_flags[thread_id] = False
        self.num_working  -= 1
        if (self.num_working < 0):
            self.num_working = 0


    @staticmethod
    def __handle_verification(client_socket, thread_id):
        print(f'{thread_id} Handling verification...')
        email = QGenIServer.__receive_long_string(client_socket)
        print(f"{thread_id} Received email: {email}")
        otp = EmailAPI.send_random_otp(email)
        print(f"{thread_id} Generated OTP: {otp}")
        for each_otp in otp:
            client_socket.sendall(Utility.int_to_big_endian(each_otp))
        print(f'{thread_id} Verification done')


    @staticmethod
    def __receive_long_string(client_socket):
        data_len_bytes = client_socket.recv(4)
        
        data_len = Utility.big_endian_to_int(data_len_bytes)
        recv_len = 0

        buffer = b''
        while recv_len < data_len:
            remains = data_len - recv_len
            if remains < TfnServer.BATCH_DATA_LEN:
                batch_len = remains
            else:
                batch_len = TfnServer.BATCH_DATA_LEN

            data = client_socket.recv(batch_len)
            recv_len += len(data)
            buffer += data
        
        return buffer.decode('utf-8')

        





