import pygame
import socket
import json
import threading
import sys

# Configuration
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5555
WIDTH, HEIGHT = 800, 600
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
BLUE = (0, 0, 255)
RED = (255, 0, 0)

# Initialize Pygame
pygame.init()
pygame.font.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Co-op Game - Login")
font = pygame.font.SysFont('Arial', 24)
clock = pygame.time.Clock()

# Network State
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connected = False
authenticated = False
my_username = ""
game_state = {}

def network_thread():
    global authenticated, game_state
    while True:
        try:
            data = client_socket.recv(4096)
            if not data:
                break
            
            # Split by json objects in case multiple arrived at once
            messages = data.decode('utf-8').replace('}{', '}\n{').split('\n')
            for msg_str in messages:
                if not msg_str: continue
                msg = json.loads(msg_str)
                
                action = msg.get('action')
                if action == 'login_response':
                    if msg.get('success'):
                        authenticated = True
                        print("[LOGIN SUCCESS]")
                    else:
                        print("[LOGIN FAILED]")
                elif action == 'register_response':
                    if msg.get('success'):
                        print("[REGISTER SUCCESS] Now you can login.")
                    else:
                        print("[REGISTER FAILED] Username may exist.")
                elif action == 'game_state':
                    game_state = msg.get('state', {})
        except Exception as e:
            print(f"[NETWORK ERROR] {e}")
            break
    print("[DISCONNECTED FROM SERVER]")

def connect_to_server():
    global connected
    try:
        client_socket.connect((SERVER_HOST, SERVER_PORT))
        connected = True
        thread = threading.Thread(target=network_thread, daemon=True)
        thread.start()
        return True
    except Exception as e:
        print(f"[CONNECTION FAILED] {e}")
        return False

def send_msg(msg_dict):
    try:
        client_socket.sendall(json.dumps(msg_dict).encode('utf-8'))
    except Exception as e:
        print(f"[SEND ERROR] {e}")

# --- UI Elements for Login ---
class InputBox:
    def __init__(self, x, y, w, h, text=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.color_inactive = pygame.Color('lightskyblue3')
        self.color_active = pygame.Color('dodgerblue2')
        self.color = self.color_inactive
        self.text = text
        self.txt_surface = font.render(text, True, self.color)
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = not self.active
            else:
                self.active = False
            self.color = self.color_active if self.active else self.color_inactive
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    return True
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    self.text += event.unicode
                self.txt_surface = font.render(self.text, True, self.color)
        return False

    def draw(self, screen):
        screen.blit(self.txt_surface, (self.rect.x+5, self.rect.y+5))
        pygame.draw.rect(screen, self.color, self.rect, 2)

def main():
    global my_username, authenticated
    
    if not connect_to_server():
        return

    # Login UI
    username_box = InputBox(WIDTH//2 - 100, HEIGHT//2 - 50, 200, 32)
    password_box = InputBox(WIDTH//2 - 100, HEIGHT//2 + 10, 200, 32)
    input_boxes = [username_box, password_box]

    state = "LOGIN" # LOGIN, PLAYING
    
    # Player logical state (client-side prediction)
    my_x, my_y = 100, 100
    speed = 5

    running = True
    while running:
        screen.fill(WHITE)

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
                send_msg({"action": "disconnect"})
                
            if state == "LOGIN":
                for box in input_boxes:
                    box.handle_event(event)
                
                # Button Logic (Simple key press for now)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        # Press Enter to Login
                        user = username_box.text
                        pwd = password_box.text
                        if user and pwd:
                            my_username = user
                            send_msg({"action": "login", "username": user, "password": pwd})
                    elif event.key == pygame.K_r:
                        # Press R to Register
                        user = username_box.text
                        pwd = password_box.text
                        if user and pwd:
                            send_msg({"action": "register", "username": user, "password": pwd})

        if state == "LOGIN":
            if authenticated:
                state = "PLAYING"
                pygame.display.set_caption(f"Co-op Game - Playing as {my_username}")
            else:
                # Draw Login Screen
                title = font.render("Login (Enter) / Register (R)", True, BLACK)
                u_label = font.render("User:", True, BLACK)
                p_label = font.render("Pass:", True, BLACK)
                
                screen.blit(title, (WIDTH//2 - 120, HEIGHT//2 - 100))
                screen.blit(u_label, (WIDTH//2 - 170, HEIGHT//2 - 45))
                screen.blit(p_label, (WIDTH//2 - 170, HEIGHT//2 + 15))
                
                for box in input_boxes:
                    box.draw(screen)

        elif state == "PLAYING":
            # Handle Movement
            keys = pygame.key.get_pressed()
            moved = False
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                my_x -= speed
                moved = True
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                my_x += speed
                moved = True
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                my_y -= speed
                moved = True
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                my_y += speed
                moved = True

            # Send position if moved
            if moved:
                send_msg({"action": "move", "x": my_x, "y": my_y})

            # Render Game State
            # Draw ground / simple environment
            pygame.draw.rect(screen, GRAY, (0, HEIGHT - 50, WIDTH, 50))
            
            # Draw other players
            for user, pos in game_state.items():
                px, py = pos.get('x', 0), pos.get('y', 0)
                color = BLUE if user == my_username else RED
                
                # Draw player square
                pygame.draw.rect(screen, color, (px, py, 40, 40))
                
                # Draw nametag
                name_lbl = font.render(user, True, BLACK)
                screen.blit(name_lbl, (px, py - 25))

            # Sync local visual position with server state to avoid jitter, 
            # or just draw using game_state. Here we trust local my_x/my_y for smoothness.

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
