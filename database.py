import hashlib
import threading
from tinydb import TinyDB, Query

db_lock = threading.Lock()
db = TinyDB('game_users.json')
UserQuery = Query()

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def register_user(username, password):
    with db_lock:
        if db.search(UserQuery.username == username):
            return False # User already exists
        db.insert({'username': username, 'password_hash': hash_password(password)})
        return True

def login_user(username, password):
    with db_lock:
        result = db.search(UserQuery.username == username)
        if result:
            stored_hash = result[0]['password_hash']
            if stored_hash == hash_password(password):
                return True
        return False
