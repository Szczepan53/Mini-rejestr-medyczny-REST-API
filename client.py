import socket
import sys
import json

username = input("Please enter username: ")
password = input("Please enter password: ")
operation = input("GET or POST?: ").strip().upper()

if operation == 'GET':
    req = 'GET /patient HTTP/1.1\r\n'
    req += f'username: {username}\r\n'
    req += f'password: {password}\r\n'
    req += '\r\n'

elif operation == 'POST':
    req = 'POST /entry HTTP/1.1\r\n'
    req += f'username: {username}\r\n'
    req += f'password: {password}\r\n'

    while True:
        entry_type = input("Enter entry type (patient/pressure/temperature): ").strip().lower()
        if entry_type == 'pressure' or entry_type == 'temperature':
            req += f'entry_type: {entry_type}\r\n'
            break
        print("Wrong entry type! Please select one from (patient/pressure/temperature). Try again")
    req += '\r\n'

    while True:
        date_time_raw = input("Enter acquisition timestamp in format: Year/Month/Day/Hour/Minute\n").strip()
        date_time_split = date_time_raw.split("/")
        if len(date_time_split) == 5:
            try:
                if all(map((lambda s: int(s) > 0), date_time_split)):
                    break
            except ValueError:
                pass

        print("Wrong acquisition timestamp! Please enter positive integer values in demanded format. Try again")

    if entry_type == 'pressure':
        while True:
            systolic = input("Enter systolic pressure value: ")
            diastolic = input("Enter diastolic pressure value: ")
            try:
                if float(systolic) > 0 and float(systolic) > 0:
                    break
            except ValueError:
                pass

            print("Wrong pressure values! Please enter positive, floating point values. Try again")

        pre_json_dict = {'systolic': systolic,
                         'diastolic': diastolic,
                         'acquisition': date_time_raw}

    elif entry_type == 'temperature':
        while True:
            value = input("Enter temperature value: ")
            try:
                if float(value) > 0:
                    break
            except ValueError:
                pass

            print("Wrong temperature value! Please enter positive, floating point value. Try again")

        pre_json_dict = {'value': value,
                         'acquisition': date_time_raw}

    else:
        raise AssertionError('Patient not implemented')

    req += json.dumps(pre_json_dict, indent=4)

SERVER_ADDRESS = 'localhost'
SERVER_PORT = 9000

clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
clientSocket.connect((SERVER_ADDRESS, SERVER_PORT))

clientSocket.send(req.encode())

while True:
    receivedData = clientSocket.recv(512)
    if len(receivedData) < 1:
        break
    print(receivedData.decode(), end="")

clientSocket.close()
