import pygame
import socket
import json
import threading
import sys
import random
import time
import math
import os

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5556

WIDTH, HEIGHT = 800, 600
FPS = 60

MAGENTA = (255, 0, 255)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLACK = (0, 0, 0)

pygame.init()
pygame.font.init()
font = pygame.font.SysFont('Arial', 24)

def network_thread(client_socket, state_dict):
    while True:
        try:
            data = client_socket.recv(8192)
            if not data: break
            
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
                    state_dict['zombies'] = msg.get('zombies', [])
                    state_dict['bullets'] = msg.get('bullets', [])
        except Exception as e:
            break

def run_bot(bot_num):
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(f"Auto Bot {bot_num}")
    clock = pygame.time.Clock()

    try:
        player_img = pygame.image.load(resource_path('assets/player.png')).convert()
        player_img.set_colorkey(MAGENTA)
        player_img = pygame.transform.scale(player_img, (50, 50))
        zombie_img = pygame.image.load(resource_path('assets/zombie.png')).convert()
        zombie_img.set_colorkey(MAGENTA)
        zombie_img = pygame.transform.scale(zombie_img, (50, 50))
        bg_img = pygame.image.load(resource_path('assets/bg.png')).convert()
        bg_img = pygame.transform.scale(bg_img, (800, 600))
    except:
        player_img = pygame.Surface((40, 40)); player_img.fill(GREEN)
        zombie_img = pygame.Surface((40, 40)); zombie_img.fill(RED)
        bg_img = pygame.Surface((800, 600)); bg_img.fill((50, 50, 50))

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try: client_socket.connect((SERVER_HOST, SERVER_PORT))
    except: return

    state_dict = {'authenticated': False, 'game_state': {}, 'zombies': [], 'bullets': []}
    threading.Thread(target=network_thread, args=(client_socket, state_dict), daemon=True).start()

    def send_msg(msg_dict):
        try: client_socket.sendall(json.dumps(msg_dict).encode('utf-8'))
        except: pass

    username = f"AutoBot_{bot_num}"
    password = "bot_pwd"

    send_msg({"action": "register", "username": username, "password": password})
    time.sleep(0.5)
    send_msg({"action": "login", "username": username, "password": password})

    my_x, my_y = random.randint(50, 750), random.randint(50, 550)
    target_x, target_y = my_x, my_y
    speed = 4

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False

        if state_dict['authenticated']:
            if abs(my_x - target_x) < speed and abs(my_y - target_y) < speed:
                target_x = random.randint(50, 750)
                target_y = random.randint(50, 550)
            
            moved = False
            if my_x < target_x: my_x += speed; moved = True
            elif my_x > target_x: my_x -= speed; moved = True
            if my_y < target_y: my_y += speed; moved = True
            elif my_y > target_y: my_y -= speed; moved = True

            my_angle = 0
            if state_dict['zombies']:
                nearest_z = min(state_dict['zombies'], key=lambda z: math.hypot(my_x - z['x'], my_y - z['y']))
                my_angle = math.degrees(math.atan2(my_y - nearest_z['y'], nearest_z['x'] - my_x))
                if random.random() < 0.1:
                    send_msg({"action": "shoot", "x": my_x, "y": my_y, "angle": my_angle})

            send_msg({"action": "move", "x": my_x, "y": my_y, "angle": my_angle})

            screen.blit(bg_img, (0, 0))
            for b in state_dict['bullets']:
                pygame.draw.circle(screen, YELLOW, (int(b['x']), int(b['y'])), 4)
            for z in state_dict['zombies']:
                screen.blit(zombie_img, zombie_img.get_rect(center=(z['x'], z['y'])))
            for user, p in state_dict['game_state'].items():
                rotated_img = pygame.transform.rotate(player_img, p.get('angle', 0))
                screen.blit(rotated_img, rotated_img.get_rect(center=(p.get('x',0), p.get('y',0))).topleft)
        else:
            screen.fill(WHITE)
            txt = font.render(f"Bot {bot_num} is connecting to server...", True, BLACK)
            screen.blit(txt, (WIDTH//2 - 150, HEIGHT//2))

        pygame.display.flip()
        clock.tick(FPS)

    send_msg({"action": "disconnect"})
    pygame.quit()

if __name__ == "__main__":
    bot_num = sys.argv[1] if len(sys.argv) > 1 else str(random.randint(100, 999))
    run_bot(bot_num)
