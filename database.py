import sqlite3
import json
import sys
import datetime
import hashlib


class SecurityError(Exception):
    pass


conn = sqlite3.connect('medical_registry.sqlite3')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# cur.execute("DROP TABLE IF EXISTS Patient")
# cur.execute("DROP TABLE IF EXISTS Pressure")
# cur.execute("DROP TABLE IF EXISTS Temperature")
# cur.execute("DROP TABLE IF EXISTS Credentials")

cur.execute('''CREATE TABLE IF NOT EXISTS Patient
            (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
             last_name TEXT,
             first_name TEXT,
             date_of_birth DATE,
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
                username TEXT,
                password TEXT,
                UNIQUE (username))''')


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def register(username, password) -> int:
    password = hash_password(password)
    cred_id = None
    try:
        cur.execute('''INSERT INTO Credentials (username, password) VALUES (?, ?)''', (username, password))
        cred_id = cur.lastrowid
        conn.commit()

    except sqlite3.IntegrityError as ex:
        print("User already registered")

    return cred_id


def validate_user(username: str, password: str) -> int:
    password = hash_password(password)
    cred_id = cur.execute('''SELECT id FROM Credentials WHERE username=? and password=?''', (username, password)).fetchone()
    if cred_id is not None:
        cred_id = cred_id[0]
        patient_id = cur.execute('''SELECT id FROM Patient WHERE credentials_id=?''', (cred_id,)).fetchone()[0]
        return patient_id
    else:
        raise SecurityError("Invalid credentials!")


def insert_patient(last_name: str, first_name: str, year: int, month: int, day: int, credentials_id: int) -> int:
    try:
        cur.execute('''INSERT INTO Patient (last_name, first_name, date_of_birth, credentials_id) VALUES (?, ?, ?, ?)''',
                    (last_name, first_name, sqlite3.Date(year, month, day), credentials_id))
        conn.commit()
        patient_id = cur.lastrowid

    except sqlite3.IntegrityError as ex:
        print(f"Patient: {last_name} {first_name} already in register!", file=sys.stderr)
        patient_id = cur.execute('SELECT id FROM Patient WHERE last_name=? and first_name=?',
                        (last_name, first_name)).fetchone()[0]

    return patient_id


def insert_pressure(systolic: float, diastolic: float, year: int, month: int, day: int, hour: int, minute: int,
                    patient_id: int) -> int:
    cur.execute('''INSERT INTO Pressure (systolic, diastolic, press_acquisition, patient_id) VALUES (?, ?, ?, ?)''',
                (systolic, diastolic, sqlite3.Timestamp(year=year, month=month, day=day, hour=hour, minute=minute),
                 patient_id))
    conn.commit()
    return patient_id


def insert_temperature(value: float, year: int, month: int, day: int, hour: int, minute: int, patient_id: int) -> int:
    cur.execute('''INSERT INTO Temperature (value, temp_acquisition, patient_id) VALUES (?, ?, ?)''',
                (value, sqlite3.Timestamp(year=year, month=month, day=day, hour=hour, minute=minute), patient_id))
    conn.commit()
    return patient_id


def fake_fill_db():
    cred_id = register('admin', 'admin')
    last_id = insert_patient('Żelazo', 'Radosław', 1999, 4, 25, cred_id)

    insert_temperature(36.7, year=2021, month=12, day=12, hour=16, minute=31, patient_id=last_id)
    insert_temperature(37.8, year=2021, month=12, day=12, hour=18, minute=14, patient_id=last_id)
    insert_temperature(39.1, year=2021, month=11, day=1, hour=7, minute=11, patient_id=last_id)

    insert_pressure(119.8, 76.6, year=2021, month=12, day=12, hour=16, minute=24, patient_id=last_id)
    insert_pressure(124.5, 81.2, year=2021, month=12, day=12, hour=19, minute=11, patient_id=last_id)
    insert_pressure(122.0, 79.1, year=2021, month=4, day=5, hour=11, minute=11, patient_id=last_id)

    cred_id = register('jan', 'kowalski63')
    last_id = insert_patient('Kowalski', 'Jan', 1963, 10, 2, cred_id)

    insert_temperature(36.7, year=2017, month=2, day=1, hour=13, minute=12, patient_id=last_id)
    insert_temperature(37.8, year=2021, month=12, day=12, hour=18, minute=14, patient_id=last_id)
    insert_temperature(39.1, year=2020, month=9, day=1, hour=10, minute=20, patient_id=last_id)

    insert_pressure(119.8, 76.6, year=2021, month=12, day=12, hour=16, minute=24, patient_id=last_id)
    insert_pressure(124.5, 81.2, year=2021, month=12, day=12, hour=19, minute=11, patient_id=last_id)
    insert_pressure(122.0, 79.1, year=2021, month=4, day=5, hour=11, minute=11, patient_id=last_id)

    cred_id = register('anna', 'nowak81')
    last_id = insert_patient('Nowak', 'Anna', 1981, 2, 28, cred_id)

    insert_temperature(35.5, year=2019, month=4, day=10, hour=4, minute=8, patient_id=last_id)
    insert_temperature(36.6, year=2020, month=12, day=31, hour=23, minute=59, patient_id=last_id)
    insert_temperature(40.2, year=2021, month=3, day=17, hour=7, minute=47, patient_id=last_id)

    insert_pressure(130.0, 91.2, year=2019, month=4, day=10, hour=4, minute=10, patient_id=last_id)
    insert_pressure(124.5, 81.2, year=2021, month=1, day=1, hour=0, minute=3, patient_id=last_id)
    insert_pressure(134.5, 91.0, year=2021, month=3, day=17, hour=7, minute=50, patient_id=last_id)

# fake_fill_db()

def get(patient_id: int):  # NOQA
    cur.execute('''SELECT Patient.id, Patient.last_name, Patient.first_name, Patient.date_of_birth, Patient.registration_timestamp
            FROM Patient WHERE Patient.id=?''', (patient_id,))

    patient_row = cur.fetchone()
    if patient_row is None:
        print(f"Patient: {patient_id} not in register!")
        return None

    patient_dict = {"Patient": {'last_name': patient_row['last_name'],
                                'first_name': patient_row['first_name'],
                                'date_of_birth': patient_row['date_of_birth'],
                                'registration_timestamp': patient_row['registration_timestamp'],
                                'Pressure': [],
                                'Temperature': []}}

    cur.execute('''SELECT press_acquisition, systolic, diastolic, press_entry_timestamp
            FROM Pressure WHERE patient_id=?''', (patient_id,))

    for press_row in cur.fetchall():
        patient_dict["Patient"]['Pressure'].append({'acquisition': press_row['press_acquisition'],
                                                    'systolic': press_row['systolic'],
                                                    'diastolic': press_row['diastolic'],
                                                    'entry_timestamp': press_row['press_entry_timestamp']})

    cur.execute('''SELECT temp_acquisition, value, temp_entry_timestamp
                FROM Temperature WHERE patient_id=?''', (patient_id,))

    for temp_row in cur.fetchall():
        patient_dict["Patient"]['Temperature'].append({'acquisition': temp_row['temp_acquisition'],
                                                       'value': temp_row['value'],
                                                       'entry_timestamp': temp_row['temp_entry_timestamp']})

    return json.dumps(patient_dict, indent=4)


if __name__ == '__main__':
    username = input("Please enter username: ")
    password = input("Please enter password: ")
    print(username, password)
    patient_id = validate_user(username, password)
    result = get(patient_id)
    print(result)
    conn.close()
