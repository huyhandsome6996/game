import sqlite3
import hashlib

DB_NAME = 'game_data.db'

def init_db():
    """Tạo bảng users nếu chưa tồn tại."""
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
    """Băm mật khẩu bằng SHA-256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def register_user(username, password):
    """Đăng ký người dùng mới. Trả về True nếu thành công, False nếu user đã tồn tại."""
    try:
        conn = sqlite3.connect(DB_NAME)
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

def login_user(username, password):
    """Đăng nhập. Trả về True nếu thành công, False nếu sai mật khẩu hoặc không tồn tại."""
    conn = sqlite3.connect(DB_NAME)
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

if __name__ == '__main__':
    # Test script
    init_db()
    print("Database initialized.")
