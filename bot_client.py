import pygame
import socket
import json
import threading
import sys
import random
import time

# Configuration
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5555
WIDTH, HEIGHT = 600, 450
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)

pygame.init()
pygame.font.init()

font = pygame.font.SysFont('Arial', 24)

def network_thread(client_socket, state_dict):
    while True:
        try:
            data = client_socket.recv(4096)
            if not data:
                break
            
            messages = data.decode('utf-8').replace('}{', '}\n{').split('\n')
            for msg_str in messages:
                if not msg_str: continue
                msg = json.loads(msg_str)
                
                action = msg.get('action')
                if action == 'login_response':
                    if msg.get('success'):
                        state_dict['authenticated'] = True
                elif action == 'game_state':
                    state_dict['game_state'] = msg.get('state', {})
        except Exception as e:
            break

def run_bot(bot_num):
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(f"Auto Bot {bot_num}")
    clock = pygame.time.Clock()

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((SERVER_HOST, SERVER_PORT))
    except:
        print(f"Bot {bot_num} failed to connect")
        return

    state_dict = {'authenticated': False, 'game_state': {}}
    thread = threading.Thread(target=network_thread, args=(client_socket, state_dict), daemon=True)
    thread.start()

    def send_msg(msg_dict):
        try:
            client_socket.sendall(json.dumps(msg_dict).encode('utf-8'))
        except:
            pass

    username = f"AutoBot_{bot_num}"
    password = "bot_password"

    # Register and Login
    send_msg({"action": "register", "username": username, "password": password})
    time.sleep(0.5)
    send_msg({"action": "login", "username": username, "password": password})

    my_x, my_y = random.randint(50, WIDTH-50), random.randint(50, HEIGHT-100)
    speed = 4

    # AI Random Movement State
    target_x, target_y = my_x, my_y

    running = True
    while running:
        screen.fill(WHITE)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        if state_dict['authenticated']:
            # Bot AI Logic
            if abs(my_x - target_x) < speed and abs(my_y - target_y) < speed:
                target_x = random.randint(50, WIDTH-50)
                target_y = random.randint(50, HEIGHT-100)
            
            moved = False
            if my_x < target_x: my_x += speed; moved = True
            elif my_x > target_x: my_x -= speed; moved = True
            
            if my_y < target_y: my_y += speed; moved = True
            elif my_y > target_y: my_y -= speed; moved = True

            if moved:
                send_msg({"action": "move", "x": my_x, "y": my_y})

            # Rendering
            pygame.draw.rect(screen, GRAY, (0, HEIGHT - 50, WIDTH, 50))
            
            for user, pos in state_dict['game_state'].items():
                px, py = pos.get('x', 0), pos.get('y', 0)
                color = GREEN if user == username else RED
                
                pygame.draw.rect(screen, color, (px, py, 40, 40))
                name_lbl = font.render(user, True, BLACK)
                screen.blit(name_lbl, (px, py - 25))
        else:
            txt = font.render(f"Bot {bot_num} is Logging in...", True, BLACK)
            screen.blit(txt, (WIDTH//2 - 100, HEIGHT//2))

        pygame.display.flip()
        clock.tick(FPS)

    send_msg({"action": "disconnect"})
    pygame.quit()

if __name__ == "__main__":
    bot_num = sys.argv[1] if len(sys.argv) > 1 else str(random.randint(100, 999))
    run_bot(bot_num)
