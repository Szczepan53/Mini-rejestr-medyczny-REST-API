import socket
import database as db
import hashlib

SERVER_ADDRESS = 'localhost'
SERVER_PORT = 9000


def create_server():
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        serverSocket.bind((SERVER_ADDRESS, SERVER_PORT))
        serverSocket.listen(5)
        while True:
            (connection, address) = serverSocket.accept()
            req = connection.recv(4096).decode()
            req_pieces = [s for s in req.split("\r\n") if s]
            headers_tmp = [tuple(map(str.strip, elem.split(':'))) for elem in req_pieces[1:]]
            headers = {header[0].lower(): header[1].strip() for header in headers_tmp}
            username = headers['username']
            password = headers['password']

            # req_pieces = req.split("\n")
            # if len(req_pieces) > 0:
            #     print(req_pieces[0])
            #
            # response = "HTTP/1.1 200 OK\r\n"
            # response += "Content-Type: text/plain; charset=utf-8\r\n"
            # response += "\r\n"
            # response += "Pacjent : Radosław\r\n\r\n"
            #
            # clientSocket.sendall(response.encode())
            connection.shutdown(socket.SHUT_WR)

    except KeyboardInterrupt:
        print("\nShutting down...\n")

    except Exception as ex:
        print("Error:\n")
        print(ex)

    serverSocket.close()


if __name__ == '__main__':
    print(f"Access http://{SERVER_ADDRESS}:{SERVER_PORT}")
    create_server()

