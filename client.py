import socket

SERVER_ADDRESS = 'localhost'
SERVER_PORT = 9000

clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
clientSocket.connect((SERVER_ADDRESS, SERVER_PORT))
req = 'GET /patient HTTP/1.1\r\n'
req += 'username: admin\r\n'
req += 'password: admin\r\n'
req += '\r\n'
clientSocket.send(req.encode())

clientSocket.close()
