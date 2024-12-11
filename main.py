from qgeni_server import QGenIServer

if __name__ == '__main__':
    server = QGenIServer(max_client=3)
    server.start_server()