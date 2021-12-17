import base64
import os
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet

"""Moduł użytkowy encryption.py udostępnia modułowi database.py funkcje wykonujące szyfrowanie danych pacjenta. 
Do generacji klucza wykorzystywanego do szyfrowania i deszyfrowania danych wykorzystywane jest hasło pacjenta."""


salt = b'\xc8\tp\xcd\x11r3\x1f\x0c\xb92\x96)\xcc\xd9\xa3'


def make_kdf():
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return kdf


def make_key(password: str) -> bytes:
    kdf = make_kdf()
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key


def make_Fernet(password: str):
    return Fernet(make_key(password))
