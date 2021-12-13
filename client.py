import socket
import sys
import json

username = input("Please enter username: ")
password = input("Please enter password: ")
method = input("GET or POST?: ").strip().upper()

req = f'{method} /patient?username={username}&password={password} HTTP/1/1\r\n'


if method == 'GET':
    # req = req.format(method, '/patient', username, password)
    req += '\r\n'

elif method == 'POST':
    # req = req.format(method, '/patient', username, password)

    while True:
        entry_type = input("Enter entry type (patient/pressure/temperature): ").strip().lower()
        if entry_type == 'pressure' or entry_type == 'temperature' or entry_type == 'patient':
            req += f'entry_type: {entry_type}\r\n'
            break
        print("Wrong entry type! Please select one from (patient/pressure/temperature). Try again")

    req += '\r\n'

    if entry_type == 'patient':
        while True:
            date_time_raw = input("Enter day of birth in format: Year/Month/Day\n").strip()
            date_time_split = date_time_raw.split("/")
            if len(date_time_split) == 3:
                try:
                    if all(map((lambda s: int(s) > 0), date_time_split)):
                        break
                except ValueError:
                    pass

            print("Wrong date of birth! Please enter positive integer values in demanded format. Try again")

        while True:
            last_name = input("Enter your last name: ").strip()
            first_name = input("Enter your first name: ").strip()
            try:
                if last_name.isalpha() and first_name.isalpha():
                    last_name = last_name.capitalize()
                    first_name = first_name.capitalize()
                    break
            except ValueError:
                pass

            print("Wrong last or first name value! Please enter values that contain only letters. Try again")

        pre_json_dict = {'last_name': last_name,
                         'first_name': first_name,
                         'date_of_birth': date_time_raw}

    else:
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
                    if float(systolic) > 0 and float(diastolic) > 0:
                        break
                except ValueError:
                    pass

                print("Wrong pressure values! Please enter positive, floating point values. Try again")

            pre_json_dict = {'systolic': systolic,
                             'diastolic': diastolic,
                             'acquisition': date_time_raw}

        else:
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

    req += json.dumps(pre_json_dict, indent=4)

else:
    print(f"Unimplemented method: {method}\nTry 'GET' or 'POST'")
    req += '\r\n'

SERVER_ADDRESS = 'localhost'
SERVER_PORT = 9000

clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
clientSocket.connect((SERVER_ADDRESS, SERVER_PORT))

clientSocket.send(req.encode())


print(f"\nServer {SERVER_ADDRESS}:{SERVER_PORT} response:\n")
while True:
    receivedData = clientSocket.recv(512)
    if len(receivedData) < 1:
        break
    print(receivedData.decode(), end="")

clientSocket.close()
