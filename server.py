import socket
import threading
import json
import database
import time
import random
import math

# Configuration
HOST = '127.0.0.1'
PORT = 5556

# Server State
clients = {} # {addr: {"conn": conn, "username": username, "x": 100, "y": 100, "hp": 100, "score": 0, "angle": 0}}
clients_lock = threading.Lock()

zombies = {}
zombie_id_counter = 0

bullets = []
bullet_id_counter = 0

state_lock = threading.Lock()

def game_loop():
    global zombie_id_counter
    while True:
        time.sleep(0.05) # 20 ticks per second
        
        with state_lock:
            with clients_lock:
                active_players = [c for c in clients.values()]
            
            # Spawn Zombies occasionally
            if len(zombies) < 10 and random.random() < 0.05:
                # Spawn at edges
                zx = random.choice([0, 800])
                zy = random.randint(0, 600)
                zombies[zombie_id_counter] = {"x": zx, "y": zy, "hp": 50, "speed": 2}
                zombie_id_counter += 1

            # Move Zombies towards nearest player
            if active_players:
                for zid, z in zombies.items():
                    nearest = min(active_players, key=lambda p: math.hypot(p['x'] - z['x'], p['y'] - z['y']))
                    dist = math.hypot(nearest['x'] - z['x'], nearest['y'] - z['y'])
                    if dist > 0:
                        z['x'] += (nearest['x'] - z['x']) / dist * z['speed']
                        z['y'] += (nearest['y'] - z['y']) / dist * z['speed']
                    
                    # Zombie hits player
                    if dist < 30:
                        nearest['hp'] -= 5
                        if nearest['hp'] <= 0:
                            nearest['hp'] = 100 # Respawn/Heal for simplicity
                            nearest['score'] -= 10
                            nearest['x'], nearest['y'] = 400, 300

            # Move Bullets
            for b in bullets[:]:
                b['x'] += b['dx'] * 15
                b['y'] += b['dy'] * 15
                
                # Check collision with zombies
                hit = False
                for zid, z in list(zombies.items()):
                    if math.hypot(b['x'] - z['x'], b['y'] - z['y']) < 30:
                        z['hp'] -= 25
                        hit = True
                        if z['hp'] <= 0:
                            del zombies[zid]
                            # Add score to owner
                            with clients_lock:
                                for c in clients.values():
                                    if c['username'] == b['owner']:
                                        c['score'] += 10
                        break
                
                if hit or b['x'] < 0 or b['x'] > 800 or b['y'] < 0 or b['y'] > 600:
                    bullets.remove(b)

        broadcast_state()

def handle_client(conn, addr):
    global bullet_id_counter
    print(f"[NEW CONNECTION] {addr} connected.")
    authenticated = False
    username = None

    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            
            try:
                # Handle possible merged JSONs
                msgs = data.decode('utf-8').replace('}{', '}\n{').split('\n')
                for msg_str in msgs:
                    if not msg_str: continue
                    msg = json.loads(msg_str)
                    
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
                                clients[addr] = {"conn": conn, "username": username, "x": 400, "y": 300, "hp": 100, "score": 0, "angle": 0}
                            print(f"[{addr}] Authenticated as {username}")
                        conn.sendall(json.dumps({"action": "login_response", "success": success}).encode('utf-8'))

                    elif action == 'move' and authenticated:
                        with clients_lock:
                            if addr in clients:
                                clients[addr]['x'] = msg.get('x', clients[addr]['x'])
                                clients[addr]['y'] = msg.get('y', clients[addr]['y'])
                                clients[addr]['angle'] = msg.get('angle', clients[addr]['angle'])

                    elif action == 'shoot' and authenticated:
                        with state_lock:
                            bx = msg.get('x')
                            by = msg.get('y')
                            angle = msg.get('angle')
                            dx = math.cos(math.radians(angle))
                            dy = -math.sin(math.radians(angle)) # negative because y is down in pygame
                            bullets.append({"id": bullet_id_counter, "x": bx, "y": by, "dx": dx, "dy": dy, "owner": username})
                            bullet_id_counter += 1

                    elif action == 'disconnect':
                        return
                        
            except json.JSONDecodeError:
                continue

    except Exception as e:
        print(f"[ERROR] {addr}: {e}")
    finally:
        print(f"[DISCONNECTED] {addr}")
        with clients_lock:
            if addr in clients:
                del clients[addr]
        conn.close()

def broadcast_state():
    with clients_lock:
        with state_lock:
            state = {}
            for addr, client_info in clients.items():
                state[client_info['username']] = {
                    "x": client_info['x'],
                    "y": client_info['y'],
                    "hp": client_info['hp'],
                    "score": client_info['score'],
                    "angle": client_info['angle']
                }
            
            z_state = [{"id": zid, "x": z['x'], "y": z['y'], "hp": z['hp']} for zid, z in zombies.items()]
            b_state = [{"x": b['x'], "y": b['y']} for b in bullets]
            
            state_msg = json.dumps({
                "action": "game_state", 
                "state": state,
                "zombies": z_state,
                "bullets": b_state
            }).encode('utf-8')
            
            for addr, client_info in clients.items():
                try:
                    client_info['conn'].sendall(state_msg)
                except Exception as e:
                    pass

def start_server():
    database.init_db()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[SERVER STARTED] Listening on {HOST}:{PORT}")
    
    # Start game loop thread
    game_thread = threading.Thread(target=game_loop, daemon=True)
    game_thread.start()

    try:
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()
    except KeyboardInterrupt:
        print("[SERVER STOPPING]")
    finally:
        server.close()

if __name__ == "__main__":
    start_server()
