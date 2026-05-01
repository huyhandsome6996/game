import pygame
import socket
import json
import threading
import sys
import math
import os

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        internal_path = os.path.join(exe_dir, '_internal', relative_path)
        if os.path.exists(internal_path):
            return internal_path
        return os.path.join(getattr(sys, '_MEIPASS', exe_dir), relative_path)
    else:
        return os.path.join(os.path.abspath("."), relative_path)

# Configuration
SERVER_HOST = '127.0.0.1' # Default to localhost for the user
SERVER_PORT = 5556

# Resolve config file path
base_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))
config_path = os.path.join(base_dir, "server_info.txt")

if os.path.exists(config_path):
    try:
        with open(config_path, "r") as f:
            data = f.read().strip()
            if ":" in data:
                SERVER_HOST, port_str = data.split(":")
                SERVER_PORT = int(port_str)
            else:
                SERVER_HOST = data
    except:
        pass

WIDTH, HEIGHT = 800, 600
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
MAGENTA = (255, 0, 255)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)

pygame.init()
pygame.font.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Co-op Zombie Shooter")
font = pygame.font.SysFont('Arial', 24)
clock = pygame.time.Clock()

# Network State
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connected = False
authenticated = False
my_username = ""
game_state = {}
zombies = []
bullets = []

def network_thread():
    global authenticated, game_state, zombies, bullets
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
                        authenticated = True
                elif action == 'game_state':
                    game_state = msg.get('state', {})
                    zombies = msg.get('zombies', [])
                    bullets = msg.get('bullets', [])
        except: break

def connect_to_server():
    global connected
    try:
        client_socket.connect((SERVER_HOST, SERVER_PORT))
        connected = True
        threading.Thread(target=network_thread, daemon=True).start()
        return True
    except: return False

def send_msg(msg_dict):
    try: client_socket.sendall(json.dumps(msg_dict).encode('utf-8'))
    except: pass

class InputBox:
    def __init__(self, x, y, w, h, text=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.color_inactive = pygame.Color('lightskyblue3'); self.color_active = pygame.Color('dodgerblue2')
        self.color = self.color_inactive; self.text = text; self.active = False
        self.txt_surface = font.render(text, True, self.color)
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            self.color = self.color_active if self.active else self.color_inactive
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN: return True
            elif event.key == pygame.K_BACKSPACE: self.text = self.text[:-1]
            else: self.text += event.unicode
            self.txt_surface = font.render(self.text, True, self.color)
        return False
    def draw(self, screen):
        screen.blit(self.txt_surface, (self.rect.x+5, self.rect.y+5))
        pygame.draw.rect(screen, self.color, self.rect, 2)

def main():
    global my_username, authenticated
    if not connect_to_server():
        screen.fill(BLACK)
        err = font.render(f"Cannot connect to server at {SERVER_HOST}", True, RED)
        screen.blit(err, (WIDTH//2 - 200, HEIGHT//2)); pygame.display.flip()
        pygame.time.delay(3000); return

    try:
        player_img = pygame.image.load(resource_path('assets/player.png')).convert()
        player_img.set_colorkey(MAGENTA); player_img = pygame.transform.scale(player_img, (50, 50))
        zombie_img = pygame.image.load(resource_path('assets/zombie.png')).convert()
        zombie_img.set_colorkey(MAGENTA); zombie_img = pygame.transform.scale(zombie_img, (50, 50))
        bg_img = pygame.image.load(resource_path('assets/bg.png')).convert()
        bg_img = pygame.transform.scale(bg_img, (800, 600))
    except:
        player_img = pygame.Surface((40, 40)); player_img.fill(BLUE)
        zombie_img = pygame.Surface((40, 40)); zombie_img.fill(RED)
        bg_img = pygame.Surface((800, 600)); bg_img.fill((50, 50, 50))

    username_box = InputBox(WIDTH//2 - 100, HEIGHT//2 - 50, 200, 32, "huy")
    password_box = InputBox(WIDTH//2 - 100, HEIGHT//2 + 10, 200, 32, "123")
    input_boxes = [username_box, password_box]

    state = "LOGIN"; login_status = ""; status_color = BLACK
    my_x, my_y = 400, 300; my_angle = 0; speed = 5
    
    # Auto Test Logic
    auto_timer = 0; auto_done = False

    running = True
    while running:
        screen.fill(WHITE)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False; send_msg({"action": "disconnect"})
            if state == "LOGIN":
                for box in input_boxes: box.handle_event(event)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        user, pwd = username_box.text, password_box.text
                        if user and pwd:
                            my_username = user; send_msg({"action": "login", "username": user, "password": pwd})
                            login_status = "Logging in..."; status_color = BLACK
                    elif event.key == pygame.K_TAB:
                        user, pwd = username_box.text, password_box.text
                        if user and pwd:
                            send_msg({"action": "register", "username": user, "password": pwd})
                            login_status = "Registering..."; status_color = BLACK
            elif state == "PLAYING":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    send_msg({"action": "shoot", "x": my_x, "y": my_y, "angle": my_angle})

        if state == "LOGIN":
            if not auto_done:
                auto_timer += 1
                if auto_timer > 30: # 0.5s delay
                    send_msg({"action": "register", "username": "huy", "password": "123"})
                    my_username = "huy"
                    send_msg({"action": "login", "username": "huy", "password": "123"})
                    auto_done = True; login_status = "Auto testing..."
            if authenticated: state = "PLAYING"
            title = font.render("ZOMBIE SHOOTER", True, BLACK); screen.blit(title, (WIDTH//2 - 100, HEIGHT//2 - 150))
            screen.blit(font.render("Username:", True, BLACK), (WIDTH//2 - 220, HEIGHT//2 - 50))
            screen.blit(font.render("Password:", True, BLACK), (WIDTH//2 - 220, HEIGHT//2 + 10))
            screen.blit(font.render(login_status, True, status_color), (WIDTH//2 - 100, HEIGHT//2 + 60))
            for box in input_boxes: box.draw(screen)

        elif state == "PLAYING":
            mx, my = pygame.mouse.get_pos()
            my_angle = math.degrees(math.atan2(my_y - my, mx - my_x))
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT] or keys[pygame.K_a]: my_x -= speed
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: my_x += speed
            if keys[pygame.K_UP] or keys[pygame.K_w]: my_y -= speed
            if keys[pygame.K_DOWN] or keys[pygame.K_s]: my_y += speed
            my_x = max(0, min(800, my_x)); my_y = max(0, min(600, my_y))
            send_msg({"action": "move", "x": my_x, "y": my_y, "angle": my_angle})
            screen.blit(bg_img, (0, 0))
            for b in bullets: pygame.draw.circle(screen, YELLOW, (int(b['x']), int(b['y'])), 4)
            for z in zombies:
                zx, zy = z['x'], z['y']; screen.blit(zombie_img, zombie_img.get_rect(center=(zx, zy)))
                pygame.draw.rect(screen, RED, (zx-20, zy-30, 40, 5)); pygame.draw.rect(screen, GREEN, (zx-20, zy-30, 40*(z['hp']/50), 5))
            for user, p in game_state.items():
                px, py, angle = p.get('x', 0), p.get('y', 0), p.get('angle', 0)
                rotated_img = pygame.transform.rotate(player_img, angle)
                screen.blit(rotated_img, rotated_img.get_rect(center=(px, py)).topleft)
                screen.blit(font.render(user, True, WHITE), (px-20, py-40))
            my_info = game_state.get(my_username, {}); my_hp = my_info.get('hp', 100); my_score = my_info.get('score', 0)
            screen.blit(font.render(f"HP: {my_hp} | SCORE: {my_score}", True, WHITE), (10, 10))
        pygame.display.flip(); clock.tick(FPS)
    pygame.quit(); sys.exit()

if __name__ == "__main__":
    main()
