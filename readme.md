#Mini rejestr medyczny z interfejsem REST API 

##API
Moduł server.py pełni rolę serwera udostępniającego interfejs REST-API (metody 'GET' oraz 'POST') do 
rejestru medycznego (bazy danych z pacjentami i pomiarami) zdefiniowanego w database.py.

Zaimplementowany interfejs umożliwia:

    >odpytanie serwera o dane pacjenta (GET)
    >rejestrację nowego pacjenta (POST)
    >wprowadzenie do bazy wpisu dotyczącego pomiaru ciśnienia (POST)
    >wprowadzenie do bazy wpisu dotyczącego pomiaru temperatury (POST)

###Składnia requesta
Ścieżka (path) URL musi być:

    '/patient'

Autoryzacja klienta:

    username i password przekazywane są jako 'queries' w URL zapytania, np. dla:
     
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
