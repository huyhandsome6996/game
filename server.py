import socket
import threading
import json
import database

# Configuration
HOST = '127.0.0.1'
PORT = 5555

# Server State
clients = {} # {addr: {"conn": conn, "username": username, "x": 100, "y": 100}}
clients_lock = threading.Lock()

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    authenticated = False
    username = None

    try:
        while True:
            # Receive data
            data = conn.recv(1024)
            if not data:
                break
            
            try:
                msg = json.loads(data.decode('utf-8'))
            except json.JSONDecodeError:
                continue

            action = msg.get('action')

            if action == 'register':
                user = msg.get('username')
                pwd = msg.get('password')
                success = database.register_user(user, pwd)
                conn.sendall(json.dumps({"action": "register_response", "success": success}).encode('utf-8'))
            
            elif action == 'login':
                user = msg.get('username')
                pwd = msg.get('password')
                success = database.login_user(user, pwd)
                if success:
                    authenticated = True
                    username = user
                    with clients_lock:
                        clients[addr] = {"conn": conn, "username": username, "x": 100, "y": 100}
                    print(f"[{addr}] Authenticated as {username}")
                conn.sendall(json.dumps({"action": "login_response", "success": success}).encode('utf-8'))

            elif action == 'move' and authenticated:
                # Update position
                with clients_lock:
                    if addr in clients:
                        clients[addr]['x'] = msg.get('x', clients[addr]['x'])
                        clients[addr]['y'] = msg.get('y', clients[addr]['y'])
                        
                # Broadcast state to all authenticated clients
                broadcast_state()

            elif action == 'disconnect':
                break

    except Exception as e:
        print(f"[ERROR] {addr}: {e}")
    finally:
        print(f"[DISCONNECTED] {addr}")
        with clients_lock:
            if addr in clients:
                del clients[addr]
        conn.close()
        broadcast_state() # Notify others that someone left

def broadcast_state():
    with clients_lock:
        state = {}
        for addr, client_info in clients.items():
            state[client_info['username']] = {
                "x": client_info['x'],
                "y": client_info['y']
            }
        
        state_msg = json.dumps({"action": "game_state", "state": state}).encode('utf-8')
        
        for addr, client_info in clients.items():
            try:
                client_info['conn'].sendall(state_msg)
            except Exception as e:
                print(f"[BROADCAST ERROR] {addr}: {e}")

def start_server():
    database.init_db()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[SERVER STARTED] Listening on {HOST}:{PORT}")

    try:
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()
            print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")
    except KeyboardInterrupt:
        print("[SERVER STOPPING]")
    finally:
        server.close()

if __name__ == "__main__":
    start_server()
