import sqlite3
import hashlib
import threading

DB_NAME = 'game_data.db'
db_lock = threading.Lock()

def init_db():
    with db_lock:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def register_user(username, password):
    with db_lock:
        try:
            conn = sqlite3.connect(DB_NAME, timeout=10)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                (username, hash_password(password))
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            print(f"DB Error: {e}")
            return False

def login_user(username, password):
    with db_lock:
        try:
            conn = sqlite3.connect(DB_NAME, timeout=10)
            cursor = conn.cursor()
            cursor.execute(
                'SELECT password_hash FROM users WHERE username = ?',
                (username,)
            )
            result = cursor.fetchone()
            conn.close()
            
            if result:
                stored_hash = result[0]
                if stored_hash == hash_password(password):
                    return True
            return False
        except Exception as e:
            print(f"DB Error: {e}")
            return False

if __name__ == '__main__':
    init_db()
