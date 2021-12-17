import socket
import sys
import json

"""
Klient łączący się z serwerem (server.py). Przekształca wprowadzone przez użytkownika w terminalu dane na zapytanie
HTTP i wysyła je do serwera, a następnie nasłuchuje odpowiedzi z serwera i wyświetla odpowiedź w terminalu.

1. Klient po uruchomieniu w terminalu zapyta o dane logowanie użytkownika próbującego uzyskać dostęp do bazy danych na 
serwerze:

    > username:password
    można testować uzyskiwanie dostępu do bazy danych na serwerze korzystając z poniższych danych logowania
    (zostają wprowadzone do bazy danych jako Credentials testowych pacjentów w trakcie jej inicjalizacji w database.py):
    
    (Andrzej Mamut) | admin:admin   
    (Jan Kowalski)  | jan:kowalski63
    (Anna Nowak)    | anna:nowak81

2. Następnie zapyta o metodę zapytania które ma sformułować:
    metody dostępne poprzez klienta:
        > 'GET'  - żądanie danych pacjenta zarejestrowanego już w bazie danych, (poprawne żądanie zwraca z serwera dane
        dotyczące pacjenta w formacie JSON)
        
        > 'POST' - wprowadzenie nowego wpisu do bazy przechowywanej na serwerze:
            * patient - rejestracja nowego pacjenta (podany w 1. username nie może być już obecny w bazie danych
                        na serwerze - serwer odmówi ponownej rejestracji pacjenta dla tego samego username)
            
            * pressure - wprowadzenie do bazy danych nowego wpisu pomiaru ciśnienia (pomiar zostanie przypisany 
                         pacjentowi któremu przypisane są podane w 1. dane logowania username:password)
                         
            * temperature - wprowadzenie do bazy danych nowego wpisu pomiaru temperatury (pomiar zostanie przypisany 
                         pacjentowi któremu przypisane są podane w 1. dane logowania username:password)
            
2b. Jeśli wybrana została metoda 'POST' to klient odpytuje użytkownika o dane definiujące wpis danego typu 
(np. dla wpisu pomiaru ciśnienia: wartość pomiaru ciśnienia skurczowego, rozkurczowego, kiedy został wykonany pomiar)

3. Klient na podstawie wprowadzonych danych formułuje zapytanie do serwera i wysyła je, a następnie odbiera odpowiedź
zwrotną i ją wyświetla. 
"""

username = input("Please enter username: ")
password = input("Please enter password: ")
method = input("GET or POST?: ").strip().upper()

req = f'{method} /patient?username={username}&password={password} HTTP/1/1\r\n'


if method == 'GET':
    req += '\r\n'

elif method == 'POST':

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
