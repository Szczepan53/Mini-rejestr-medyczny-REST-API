import json
import socket
import sqlite3
import sys
from urllib import parse
import database as db
import traceback

"""Moduł server.py pełni rolę serwera udostępniającego interfejs REST-API (metody 'GET' oraz 'POST') do 
rejestru medycznego (bazy danych z pacjentami i pomiarami) zdefiniowanego w database.py.

Ścieżka (path) URL musi być:
    '/patient'

Autoryzacja klienta:
    username i password przekazywane jako 'queries' w URL zapytania, np. dla:
     
    username: admin
    password: 12345 
    metoda: GET
    
    GET /patient?username=admin&password=12345 HTTP/1.1

Metoda POST:
    Dla metody 'POST' niezbędne jest przekazanie w nagłówku zapytania atrybutu 'entry_type' określającego typ wpisu, 
    który próbujemy wprowadzić do bazy danych (czy jest to pomiar ciśnienia, temperatury czy może nowy pacjent).
    Możliwe wartości atrybutu:
        > patient
        > pressure
        > temperature
    
    W ciele zapytania należy umieścić również informacje w formacie JSON definiujące przekazywany wpis danego typu.
    Np. dla metody 'POST', username: srubka, password: gwint oraz content_type: pressure
    
    POST /patient?username=srubka&password=gwint HTTP/1.1
    entry_type: pressure
    
    {
        "systolic": "120.0",
        "diastolic": "80.2"
        "acquisition": "2021/12/12/22/10"
    }
    
    podobnie, dla entry_type: temperature w ciele zapytania należy umieścić informacje w formacie JSON:
    
    {
        "value": wartość pomiaru (float)
        "acquisition": chwila pomiaru w formacie YYYY/MM/DD/hh/mm
    }
    
    a dla entry_type: patient
    
    {
        "last_name": nazwisko_pacjenta
        "first_name": imie_pacjenta
        "date_of_birth": data urodzin w formacie YYYY/MM/DD
    }
"""

SERVER_ADDRESS = 'localhost'
SERVER_PORT = 9000

response_dict = {'ok_plain': 'HTTP/1.1 200 OK\r\nContent-type: text/plain\r\n',
                 'ok_json': 'HTTP/1.1 200 OK\r\nContent-Type : application/json\r\n',
                 'access_denied': 'HTTP/1.1 401 Unauthorized\r\nContent-type: text/plain\r\n\r\nAccess denied!\nInvalid username or password\r\n',
                 'already_registered': 'HTTP/1.1 403 Forbidden\r\nContent-type: text/plain\r\n\r\nPatient already registered\r\n',
                 'bad_request_method': 'HTTP/1.1 400 Bad Request\r\nContent-type: text/plain\r\n\r\nBad request method, try GET or POST\r\n',
                 'missing_entry_type': 'HTTP/1.1 400 Bad Request\r\nContent-type: text/plain\r\n\r\nMissing \'entry_type\' header\r\n',
                 'bad_entry_type': 'HTTP/1.1 400 Bad Request\r\nContent-type: text/plain\r\n\r\nBad \'entry_type\' header value\r\n',
                 'missing_entry_value': 'HTTP/1.1 400 Bad Request\r\nContent-type: text/plain\r\n\r\nAt least one of entry values is missing\r\n',
                 'bad_entry_value': 'HTTP/1.1 400 Bad Request\r\nContent-type: text/plain\r\n\r\nAt least one of entry values is bad\r\n',
                 'bad_request_path': 'HTTP/1.1 400 Bad Request\r\nContent-type: text/plain\r\n\r\nBad request url path\r\n',
                 'bad_request': 'HTTP/1.1 400 Bad Request\r\nContent-type: text/plain\r\n\r\nBad request url\r\n'
                 }


class HTTPRequestException(Exception):
    pass


class InvalidRequestPathException(HTTPRequestException):
    pass


class FaviconRequestException(InvalidRequestPathException):
    pass


class UnsupportedMethodException(HTTPRequestException):
    pass


def success_message(message):
    print("SUCCESS", 50 * "-", message, 50 * "-", sep="\n")


def error_message(message):
    print("ERROR", 50 * "^", message, 50 * "v", sep="\n")


def error_shutdown_connection(ex: Exception, connection, response: str):
    error_message(ex)
    connection.sendall(response.encode())
    connection.shutdown(socket.SHUT_WR)


def parse_request(req):
    try:
        headers_raw, body_raw = req.split('\r\n\r\n')
    except ValueError:
        raise HTTPRequestException("Bad request")

    first_line, *headers_rest = headers_raw.split('\r\n')
    first_line_split = first_line.split(" ")

    if len(first_line_split) < 1:
        raise HTTPRequestException("Bad request")

    req_method = first_line_split[0]
    urlParsed = parse.urlparse(first_line_split[1])
    path = urlParsed.path

    if not (req_method == "GET" or req_method == "POST"):
        raise UnsupportedMethodException(f"Unsupported request method: {req_method}")

    if path == '/favicon.ico':
        raise FaviconRequestException()
    #
    if not (path == '/patient'):
        raise InvalidRequestPathException(f"Invalid request path: {path}")

    query = urlParsed.query.split("&")

    try:
        query_dict = {pair.split("=")[0]: pair.split("=")[1] for pair in query}
        if 'username' not in query_dict or 'password' not in query_dict:
            raise HTTPRequestException('Missing username and/or password in request URL queries')
    except IndexError:
        raise HTTPRequestException('Missing username and/or password in request URL queries')

    try:
        headers_tmp = [tuple(map(str.strip, elem.split(':'))) for elem in headers_rest]
        headers = {header[0].lower(): header[1].strip() for header in headers_tmp}
    except IndexError:
        raise HTTPRequestException('Bad request')

    return req_method, path, query_dict, headers, body_raw


def create_server():
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn = db.connect(db.MEDICAL_REGISTRY)
    try:
        serverSocket.bind((SERVER_ADDRESS, SERVER_PORT))
        serverSocket.listen(5)
        while True:
            print('\nready...\n')
            (connection, address) = serverSocket.accept()
            req = connection.recv(4096).decode()
            # print(req)  # DEBUG
            try:
                req_method, path, query_dict, headers, body_raw = parse_request(req)

            except FaviconRequestException:
                connection.shutdown(socket.SHUT_RDWR)  # ignore favicon.ico request from browser
                continue

            except InvalidRequestPathException as ex:
                error_shutdown_connection(ex, connection, response_dict['bad_request_path'])
                continue

            except UnsupportedMethodException as ex:
                error_shutdown_connection(ex, connection, response_dict['bad_request_method'])
                continue

            except HTTPRequestException as ex:
                error_shutdown_connection(ex, connection, response_dict['bad_request'])
                continue

            username = query_dict['username']
            password = query_dict['password']

            try:

                patient_id, fernet = db.validate_user(username, password)

            except db.SecurityError as ex:
                try:
                    if req_method != 'POST' or headers['entry_type'] != 'patient' or not username or not password:
                        error_shutdown_connection(ex, connection, response_dict['access_denied'])
                        continue
                except KeyError as ex:
                    error_shutdown_connection(ex, connection, response_dict['missing_entry_type'])
                    continue

                else:
                    try:
                        entry_dict = json.loads(body_raw.strip())
                        last_name = entry_dict['last_name']
                        first_name = entry_dict['first_name']
                        date_of_birth = {unit: int(value.strip()) for unit, value in
                                         zip(["year", "month", "day"], entry_dict['date_of_birth'].split('/'))}

                        cred_id, fernet = db.register(username, password)
                        db.insert_patient(last_name, first_name, credentials_id=cred_id, fernet=fernet
                                          **date_of_birth)  # if successful commits changes to db

                    except KeyError as ex:
                        error_shutdown_connection(ex, connection, response_dict['missing_entry_value'])
                        continue
                    except ValueError as ex:
                        error_shutdown_connection(ex, connection, response_dict['bad_entry_value'])
                        continue
                    except sqlite3.Error as ex:
                        error_shutdown_connection(ex, connection, response_dict['already_registered'])
                        conn.rollback()  # undo changes to database if something went wrong in insert_patient()
                        continue

                    resp = response_dict['ok_plain']
                    resp += "\r\n"
                    resp += f"User {username}:{password} successfully registered\n"
                    resp += f'Entry: {headers["entry_type"]}\n' + body_raw + "\nsuccessfully added to database!\n"
                    connection.sendall(resp.encode())
                    connection.shutdown(socket.SHUT_WR)
                    success_message(
                        f"Registered new user: {username}\nadded new patient {last_name} {first_name} to database.")
                    continue

            if req_method == 'GET':
                patient_data = db.get(patient_id, fernet)
                resp = response_dict['ok_json']
                resp += '\r\n'
                resp += patient_data + "\n"
                message = f"Retrieved data for user {username} from database"

            else:  # req_method = 'POST'
                try:
                    entry_type = headers['entry_type'].lower()
                except KeyError as ex:
                    error_shutdown_connection(ex, connection, response_dict['missing_entry_type'])
                    continue

                entry_dict = json.loads(body_raw.strip())
                if entry_type == 'pressure' or entry_type == 'temperature':
                    try:
                        timestamp = {unit: int(value.strip()) for unit, value in
                                     zip(["year", "month", "day", "hour", "minute"],
                                         entry_dict['acquisition'].split('/'))}

                        if entry_type == 'pressure':
                            systolic = float(entry_dict['systolic'])
                            diastolic = float(entry_dict['diastolic'])
                            db.insert_pressure(systolic, diastolic, patient_id=patient_id, fernet=fernet, **timestamp)

                        elif entry_type == 'temperature':
                            value = float(entry_dict['value'])
                            db.insert_temperature(value, patient_id=patient_id, fernet=fernet, **timestamp)

                        message = f"Inserted new: {entry_type} entry for user: {username}"

                    except KeyError as ex:
                        error_shutdown_connection(ex, connection, response_dict['missing_entry_value'])
                        continue

                    except ValueError as ex:
                        error_shutdown_connection(ex, connection, response_dict['bad_entry_value'])
                        continue

                    resp = response_dict['ok_plain']
                    resp += '\r\n'
                    resp += f'Entry: {entry_type}\n' + body_raw + "\nsuccessfully added to database!\n"

                elif entry_type == 'patient':
                    error_shutdown_connection(ValueError(f"User {username} already registered!"),
                                              connection, response_dict['already_registered'])
                    continue

                else:
                    error_shutdown_connection(ValueError("Invalid entry_type value!"),
                                              connection, response_dict['bad_entry_type'])
                    continue

            connection.sendall(resp.encode())
            connection.shutdown(socket.SHUT_WR)
            success_message(message)

    except KeyboardInterrupt:
        print("\nShutting down...\n")

    except Exception:
        print("Error:\n")
        traceback.print_exc()
        print("Error:\n")

    finally:
        serverSocket.close()
        conn.close()


if __name__ == '__main__':
    print(f"Access http://{SERVER_ADDRESS}:{SERVER_PORT}")
    create_server()
