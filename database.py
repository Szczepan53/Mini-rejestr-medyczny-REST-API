import sqlite3
import json
import sys
import datetime
import cryptography.fernet
import encryption as enc

"""
Moduł inicjalizujący bazę danych w SQLite i zarządzający nią. Fukcje zdefiniowane w module udostępniają 
serwerowi (server.py) interfejs do komunikacji z bazą danych.
Zdefiniowana baza danych zawiera następujące tablice: 
    >Patient - zawiera dane o zarejestrowanych pacjentach (nazwisko, imię, data urodzenia itp.), 
    każdy pacjent przypisany jest do dokładnie jednego rekordu w Credentials i każdy rekord w Credentials odpowiada
    tylko jednemu pacjentowi (1:1).
    Rekordy zawarte w Patient podlegają szyfrowaniu hasłem pacjenta.
     
    >Pressure - zawiera dane o wprowadzonych pomiarach ciśnienia, każdy rekord w Pressure przypisany jest do dokładnie
    jednego pacjenta, ale wiele różnych rekordów może byc przypisanych do tego samego pacjenta (1:n).
    Rekordy zawarte w Pressure nie podlegają szyfrowaniu.
    
    >Temperature - zawiera dane o wprowadzonych pomiarach temperatury, każdy rekord w Temperature przypisany jest do
    dokładnie jednego rekordu w Patient (1:n).
    Rekordy zawarte w Temperature nie podlegają szyfrowaniu.

    
    >Credentials - zawiera dane logowania pacjenta (login, hasło).
     Rekordy zawarte w Credentials podlegają szyfrowaniu hasłem pacjenta.
    
Inicjalizacja zachodzi podczas importu tego modułu w module server.py, jeżeli tablica Credentials jest pusta, to
wywołana zostaje funkcja fake_fill_db() wprowadzająca do bazy danych dane 3 testowych pacjentów:

    > Andrzej Mamut (username=admin, password=admin)
    > Jan Kowalski (username=jan, password=kowalski63)
    > Anna Nowak (username=anna, password=nowak81)
"""


class SecurityError(Exception):
    pass


MEDICAL_REGISTRY = 'medical_registry.sqlite3'
conn = sqlite3.connect(MEDICAL_REGISTRY)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# cur.execute("DROP TABLE IF EXISTS Patient")
# cur.execute("DROP TABLE IF EXISTS Pressure")
# cur.execute("DROP TABLE IF EXISTS Temperature")
# cur.execute("DROP TABLE IF EXISTS Credentials")

cur.execute('''CREATE TABLE IF NOT EXISTS Patient
            (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
             last_name BLOB,
             first_name BLOB,
             date_of_birth BLOB,
             registration_timestamp DATETIME DEFAULT (datetime('now', 'localtime')),
             credentials_id INTEGER,
             UNIQUE (last_name, first_name),
             UNIQUE (credentials_id))''')

cur.execute('''CREATE TABLE IF NOT EXISTS Pressure
                (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                systolic FLOAT,
                diastolic FLOAT,
                press_acquisition DATETIME,
                press_entry_timestamp DATETIME DEFAULT (datetime('now', 'localtime')),
                patient_id INTEGER
                )''')

cur.execute('''CREATE TABLE IF NOT EXISTS Temperature(
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                value FLOAT,
                temp_acquisition DATETIME,
                temp_entry_timestamp DATETIME DEFAULT (datetime('now', 'localtime')),
                patient_id INTEGER)''')

cur.execute('''CREATE TABLE IF NOT EXISTS Credentials(
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                username BLOB,
                password BLOB,
                UNIQUE (username))''')


def validate_date(date):
    if (datetime.datetime.now().date() - date).days < 0:
        raise ValueError("The date is from the future")


def validate_timestamp(timestamp, patient_id, fernet):
    if (datetime.datetime.now() - timestamp).total_seconds() < 0:
        raise ValueError("The timestamp is from the future")
    date_of_birth = sqlite3.Date(*map(int, fernet.decrypt(cur.execute("SELECT date_of_birth FROM Patient WHERE id=?",
                                                                      (patient_id,)).fetchone()[0]).decode().split('-')))
    if (timestamp.date() - date_of_birth).days < 0:
        raise ValueError("The timestamp is from before the day of birth of the patient")


def register(username, password) -> int:
    """Need to call conn.commit() after or conn.rollback() if something went wrong"""
    fernet = enc.make_Fernet(password)

    cur.execute('''SELECT id, username, password FROM Credentials''')
    for row in cur:
        try:
            if fernet.decrypt(row['username']).decode() == username:
                raise sqlite3.IntegrityError('User already registered!')
        except (cryptography.fernet.InvalidToken, TypeError):
            pass
    else:
        username = fernet.encrypt(username.encode())
        password = fernet.encrypt(password.encode())
        cur.execute('''INSERT INTO Credentials (username, password) VALUES (?, ?)''', (username, password))
        cred_id = cur.lastrowid
        return cred_id, fernet


def validate_user(username: str, password: str) -> int:
    fernet = enc.make_Fernet(password)

    cur.execute('''SELECT id, username, password FROM Credentials''')
    for row in cur:
        try:
            if fernet.decrypt(row['username']).decode() == username and fernet.decrypt(
                    row['password']).decode() == password:
                cred_id = row['id']
                break
        except cryptography.fernet.InvalidToken:
            pass
    else:
        cred_id = None

    if cred_id is not None:
        patient_id = cur.execute('''SELECT id FROM Patient WHERE credentials_id=?''', (cred_id,)).fetchone()[0]
        return patient_id, fernet
    else:
        raise SecurityError("Invalid credentials!")


def insert_patient(last_name: str, first_name: str, year: int, month: int, day: int, credentials_id: int,
                   fernet) -> int:
    try:
        day_of_birth = sqlite3.Date(year, month, day)
        validate_date(day_of_birth)  # raises ValueError if day_of_birth is from the future

        last_name = fernet.encrypt(last_name.encode())
        first_name = fernet.encrypt(first_name.encode())
        day_of_birth = fernet.encrypt(str(day_of_birth).encode())

        cur.execute(
            '''INSERT INTO Patient (last_name, first_name, date_of_birth, credentials_id) VALUES (?, ?, ?, ?)''',
            (last_name, first_name, day_of_birth, credentials_id))
        conn.commit()
        patient_id = cur.lastrowid

    except sqlite3.IntegrityError:
        print(f"Patient: {last_name} {first_name} already in register!", file=sys.stderr)
        patient_id = cur.execute('SELECT id FROM Patient WHERE last_name=? and first_name=?',
                                 (last_name, first_name)).fetchone()[0]

    return patient_id


def insert_pressure(systolic: float, diastolic: float, year: int, month: int, day: int, hour: int, minute: int,
                    patient_id: int, fernet) -> int:
    timestamp = sqlite3.Timestamp(year=year, month=month, day=day, hour=hour, minute=minute)
    validate_timestamp(timestamp,
                       patient_id,
                       fernet)  # raises ValueError if timestamp is from the future or from before patient's birth

    cur.execute('''INSERT INTO Pressure (systolic, diastolic, press_acquisition, patient_id) VALUES (?, ?, ?, ?)''',
                (systolic, diastolic, timestamp, patient_id))
    conn.commit()
    return patient_id


def insert_temperature(value: float, year: int, month: int, day: int, hour: int, minute: int, patient_id: int,
                       fernet) -> int:
    timestamp = sqlite3.Timestamp(year=year, month=month, day=day, hour=hour, minute=minute)
    validate_timestamp(timestamp,
                       patient_id,
                       fernet)  # raises ValueError if timestamp is from the future or from before patient's birth

    cur.execute('''INSERT INTO Temperature (value, temp_acquisition, patient_id) VALUES (?, ?, ?)''',
                (value, timestamp, patient_id))
    conn.commit()
    return patient_id


def fake_fill_db():
    cred_id, fernet = register('admin', 'admin')
    last_id = insert_patient('Mamut', 'Andrzej', 1985, 9, 4, cred_id, fernet)

    insert_temperature(36.7, year=2021, month=12, day=12, hour=16, minute=31, patient_id=last_id, fernet=fernet)
    insert_temperature(37.8, year=2021, month=12, day=12, hour=18, minute=14, patient_id=last_id, fernet=fernet)
    insert_temperature(39.1, year=2021, month=11, day=1, hour=7, minute=11, patient_id=last_id, fernet=fernet)

    insert_pressure(119.8, 76.6, year=2021, month=12, day=12, hour=16, minute=24, patient_id=last_id, fernet=fernet)
    insert_pressure(124.5, 81.2, year=2021, month=12, day=12, hour=19, minute=11, patient_id=last_id, fernet=fernet)
    insert_pressure(122.0, 79.1, year=2021, month=4, day=5, hour=11, minute=11, patient_id=last_id, fernet=fernet)

    cred_id, fernet = register('jan', 'kowalski63')
    last_id = insert_patient('Kowalski', 'Jan', 1963, 10, 2, cred_id, fernet)

    insert_temperature(36.7, year=2017, month=2, day=1, hour=13, minute=12, patient_id=last_id, fernet=fernet)
    insert_temperature(37.8, year=2021, month=12, day=12, hour=18, minute=14, patient_id=last_id, fernet=fernet)
    insert_temperature(39.1, year=2020, month=9, day=1, hour=10, minute=20, patient_id=last_id, fernet=fernet)

    insert_pressure(119.8, 76.6, year=2021, month=12, day=12, hour=16, minute=24, patient_id=last_id, fernet=fernet)
    insert_pressure(124.5, 81.2, year=2021, month=12, day=12, hour=19, minute=11, patient_id=last_id, fernet=fernet)
    insert_pressure(122.0, 79.1, year=2021, month=4, day=5, hour=11, minute=11, patient_id=last_id, fernet=fernet)

    cred_id, fernet = register('anna', 'nowak81')
    last_id = insert_patient('Nowak', 'Anna', 1981, 2, 28, cred_id, fernet)

    insert_temperature(35.5, year=2019, month=4, day=10, hour=4, minute=8, patient_id=last_id, fernet=fernet)
    insert_temperature(36.6, year=2020, month=12, day=31, hour=23, minute=59, patient_id=last_id, fernet=fernet)
    insert_temperature(40.2, year=2021, month=3, day=17, hour=7, minute=47, patient_id=last_id, fernet=fernet)

    insert_pressure(130.0, 91.2, year=2019, month=4, day=10, hour=4, minute=10, patient_id=last_id, fernet=fernet)
    insert_pressure(124.5, 81.2, year=2021, month=1, day=1, hour=0, minute=3, patient_id=last_id, fernet=fernet)
    insert_pressure(134.5, 91.0, year=2021, month=3, day=17, hour=7, minute=50, patient_id=last_id, fernet=fernet)

    conn.commit()


def get(patient_id: int, fernet):  # NOQA
    cur.execute('''SELECT Patient.id, Patient.last_name, Patient.first_name, Patient.date_of_birth, Patient.registration_timestamp
            FROM Patient WHERE Patient.id=?''', (patient_id,))

    patient_row = cur.fetchone()
    if patient_row is None:
        print(f"Patient: {patient_id} not in register!")
        return None

    patient_dict = {"Patient": {'last_name': fernet.decrypt(patient_row['last_name']).decode(),
                                'first_name': fernet.decrypt(patient_row['first_name']).decode(),
                                'date_of_birth': fernet.decrypt(patient_row['date_of_birth']).decode(),
                                'registration_timestamp': patient_row['registration_timestamp'],
                                'Pressure': [],
                                'Temperature': []}}

    cur.execute('''SELECT press_acquisition, systolic, diastolic, press_entry_timestamp
            FROM Pressure WHERE patient_id=? ORDER BY press_acquisition DESC ''', (patient_id,))

    for press_row in cur.fetchall():
        patient_dict["Patient"]['Pressure'].append({'acquisition': press_row['press_acquisition'],
                                                    'systolic': press_row['systolic'],
                                                    'diastolic': press_row['diastolic'],
                                                    'entry_timestamp': press_row['press_entry_timestamp']})

    cur.execute('''SELECT temp_acquisition, value, temp_entry_timestamp
                FROM Temperature WHERE patient_id=? ORDER BY temp_acquisition DESC''', (patient_id,))

    for temp_row in cur.fetchall():
        patient_dict["Patient"]['Temperature'].append({'acquisition': temp_row['temp_acquisition'],
                                                       'value': temp_row['value'],
                                                       'entry_timestamp': temp_row['temp_entry_timestamp']})

    return json.dumps(patient_dict, indent=4)


def connect(db_path):
    global conn, cur
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.row_factory = sqlite3.Row
    return conn


def disconnect():
    conn.close()


if cur.execute("SELECT COUNT(*) FROM Credentials").fetchone()[0] == 0:
    fake_fill_db()
    print("Database set up")

conn.close()

# if __name__ == '__main__':
#     try:
#         conn = sqlite3.connect(MEDICAL_REGISTRY)
#         username = input("Please enter username: ")
#         password = input("Please enter password: ")
#         print(username, password)
#         patient_id = validate_user(username, password)
#         result = get(patient_id)
#         print(result)
#     finally:
#         conn.close()
