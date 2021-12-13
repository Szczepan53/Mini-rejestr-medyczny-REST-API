import json
import socket
import sys

import database as db
import hashlib

SERVER_ADDRESS = 'localhost'
SERVER_PORT = 9000

response_dict = {'ok_plain': 'HTTP/1.1 200 OK\r\nContent-type: text/plain\r\n',
                 'ok_json': 'HTTP/1.1 200 OK\r\nContent-Type : application/json\r\n',
                 'access_denied': "HTTP/1.1 403 Forbidden\r\nContent-type: text/plain\r\n\r\nAccess denied!\nInvalid username or password\r\n",
                 'missing_entry_type': "HTTP/1.1 400 Bad Request\r\nContent-type: text/plain\r\n\r\nMissing 'entry_type' header\r\n",
                 'missing_entry_value': "HTTP/1.1 400 Bad Request\r\nContent-type: text/plain\r\n\r\nAt least one of entry values is missing\r\n",
                 'bad_entry_value': "HTTP/1.1 400 Bad Request\r\nContent-type: text/plain\r\n\r\nAt least one of entry values is bad\r\n"
                 }


def error_shutdown_connection(ex: Exception, conn, response: str):
    print(ex, file=sys.stderr)
    conn.sendall(response.encode())
    conn.shutdown(socket.SHUT_WR)


def create_server():
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        serverSocket.bind((SERVER_ADDRESS, SERVER_PORT))
        serverSocket.listen(5)
        while True:
            (connection, address) = serverSocket.accept()
            req = connection.recv(4096).decode()
            print(req)  # DEBUG
            headers_raw, body_raw = req.split('\r\n\r\n')
            headers_pieces = [s for s in headers_raw.split("\r\n") if s]
            headers_tmp = [tuple(map(str.strip, elem.split(':'))) for elem in headers_pieces[1:]]
            headers = {header[0].lower(): header[1].strip() for header in headers_tmp}
            username = headers['username']
            password = headers['password']
            try:
                patient_id = db.validate_user(username, password)

            except db.SecurityError as ex:
                error_shutdown_connection(ex, connection, response_dict['access_denied'])
                continue

            if headers_pieces[0].startswith('GET'):
                patient_data = db.get(patient_id)
                resp = response_dict['ok_json']
                resp += '\r\n'
                resp += patient_data

            elif headers_pieces[0].startswith("POST"):
                try:
                    entry_type = headers['entry_type'].lower()
                except KeyError as ex:
                    error_shutdown_connection(ex, connection, response_dict['missing_entry_type'])
                    continue

                entry_dict = json.loads(body_raw.strip())
                if entry_type == 'pressure' or entry_type == 'temperature':
                    try:
                        timestamp = entry_dict['acquisition']
                        timestamp = {unit: int(value.strip()) for unit, value in zip(["year", "month", "day", "hour", "minute"], timestamp.split('/'))}

                        if entry_type == 'pressure':
                            systolic = float(entry_dict['systolic'])
                            diastolic = float(entry_dict['diastolic'])
                            db.insert_pressure(systolic, diastolic, patient_id=patient_id, **timestamp)

                        elif entry_type == 'temperature':
                            value = float(entry_dict['value'])
                            db.insert_temperature(value, patient_id=patient_id, **timestamp)

                    except KeyError as ex:
                        error_shutdown_connection(ex, connection, response_dict['missing_entry_value'])
                        continue

                    except ValueError as ex:
                        error_shutdown_connection(ex, connection, response_dict['bad_entry_value'])
                        continue

                    resp = response_dict['ok_plain']
                    resp += '\r\n'
                    resp += f'Entry: {entry_type}\n' + body_raw + "\nsuccessfully added to database!"

            connection.sendall(resp.encode())
            connection.shutdown(socket.SHUT_WR)

    except KeyboardInterrupt:
        print("\nShutting down...\n")

    except Exception as ex:
        print("Error:\n")
        print(ex, file=sys.stderr)

    serverSocket.close()


if __name__ == '__main__':
    print(f"Access http://{SERVER_ADDRESS}:{SERVER_PORT}")
    create_server()

