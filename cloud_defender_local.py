import pygame
import sys
import requests
import json
import time
import random

# Initialize pygame
pygame.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)

# Set up the display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Cloud Defender")

# Load fonts
font = pygame.font.SysFont(None, 36)
small_font = pygame.font.SysFont(None, 24)

# Game variables
player_x = SCREEN_WIDTH // 2
player_y = SCREEN_HEIGHT - 50
player_speed = 5
player_health = 100
bullets = []
enemies = []
score = 0
level = 1
game_over = False

# Server URL - local testing
SERVER_URL = "http://localhost:8080"

# Function to draw text
def draw_text(text, font, color, x, y):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    text_rect.center = (x, y)
    screen.blit(text_surface, text_rect)

# Function to draw the player
def draw_player():
    pygame.draw.polygon(screen, BLUE, [
        (player_x, player_y - 20),
        (player_x - 20, player_y + 10),
        (player_x + 20, player_y + 10)
    ])

# Function to draw bullets
def draw_bullets():
    for bullet in bullets:
        pygame.draw.rect(screen, YELLOW, (bullet[0] - 2, bullet[1] - 10, 4, 10))

# Function to draw enemies
def draw_enemies():
    for enemy in enemies:
        if enemy[2] == 'ec2':
            color = RED
        elif enemy[2] == 's3':
            color = GREEN
        else:  # lambda
            color = ORANGE
        
        pygame.draw.circle(screen, color, (enemy[0], enemy[1]), 15)
        text = small_font.render(enemy[2], True, WHITE)
        screen.blit(text, (enemy[0] - 15, enemy[1] - 8))

# Function to draw the HUD
def draw_hud():
    # Health bar
    pygame.draw.rect(screen, RED, (20, 20, 200, 20))
    pygame.draw.rect(screen, GREEN, (20, 20, player_health * 2, 20))
    draw_text(f"Health: {player_health}", small_font, WHITE, 120, 30)
    
    # Score and level
    draw_text(f"Score: {score}", font, WHITE, SCREEN_WIDTH - 100, 30)
    draw_text(f"Level: {level}", font, WHITE, SCREEN_WIDTH - 100, 60)

# Main game loop
def main():
    global player_x, player_y, player_health, bullets, enemies, score, level, game_over
    
    clock = pygame.time.Clock()
    
    # Try to connect to server
    try:
        print(f"Connecting to server at {SERVER_URL}...")
        response = requests.get(f"{SERVER_URL}/health")
        if response.status_code == 200:
            print("Server connection successful!")
        else:
            print(f"Server connection failed: {response.status_code}")
    except Exception as e:
        print(f"Error connecting to server: {e}")
        print("Running in offline mode")
    
    # Start a new game on the server
    try:
        requests.post(f"{SERVER_URL}/game/start")
        print("Game started on server")
    except Exception as e:
        print(f"Error starting game on server: {e}")
    
    # Game loop
    running = True
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and not game_over:
                    bullets.append([player_x, player_y])
                    # Try to send shoot action to server
                    try:
                        requests.post(f"{SERVER_URL}/game/shoot")
                    except:
                        pass
        
        if not game_over:
            # Handle player movement
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT] and player_x > 20:
                player_x -= player_speed
                # Try to send move action to server
                try:
                    requests.post(f"{SERVER_URL}/game/move", json={"direction": "left"})
                except:
                    pass
            if keys[pygame.K_RIGHT] and player_x < SCREEN_WIDTH - 20:
                player_x += player_speed
                # Try to send move action to server
                try:
                    requests.post(f"{SERVER_URL}/game/move", json={"direction": "right"})
                except:
                    pass
            
            # Move bullets
            new_bullets = []
            for bullet in bullets:
                bullet[1] -= 10  # Bullet speed
                if bullet[1] > 0:
                    new_bullets.append(bullet)
            bullets = new_bullets
            
            # Move enemies
            new_enemies = []
            for enemy in enemies:
                enemy[1] += 3  # Enemy speed
                
                # Check if enemy hit player
                if (abs(enemy[0] - player_x) < 30 and 
                    abs(enemy[1] - player_y) < 30):
                    player_health -= 10
                    if player_health <= 0:
                        game_over = True
                    continue
                    
                # Check if enemy reached bottom
                if enemy[1] < SCREEN_HEIGHT:
                    new_enemies.append(enemy)
            enemies = new_enemies
            
            # Check bullet-enemy collisions
            for bullet in bullets[:]:
                for enemy in enemies[:]:
                    if (abs(bullet[0] - enemy[0]) < 20 and 
                        abs(bullet[1] - enemy[1]) < 20):
                        if bullet in bullets:
                            bullets.remove(bullet)
                        if enemy in enemies:
                            enemies.remove(enemy)
                        score += 10 * level
                        break
            
            # Spawn new enemies
            if len(enemies) < 10 and random.random() < 0.05:
                enemy_x = random.randint(50, SCREEN_WIDTH - 50)
                enemy_y = 0
                enemy_type = random.choice(['ec2', 's3', 'lambda'])
                enemies.append([enemy_x, enemy_y, enemy_type])
                
            # Level up
            if score > level * 500:
                level += 1
        
        # Draw everything
        screen.fill(BLACK)
        draw_player()
        draw_bullets()
        draw_enemies()
        draw_hud()
        
        if game_over:
            draw_text("GAME OVER", font, RED, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
            draw_text(f"Final Score: {score}", font, WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40)
            draw_text("Press Q to Quit or R to Restart", font, WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 80)
            
            # Handle game over input
            keys = pygame.key.get_pressed()
            if keys[pygame.K_q]:
                running = False
            elif keys[pygame.K_r]:
                # Reset game
                player_x = SCREEN_WIDTH // 2
                player_y = SCREEN_HEIGHT - 50
                player_health = 100
                bullets = []
                enemies = []
                score = 0
                level = 1
                game_over = False
                
                # Try to submit score to server
                try:
                    player_name = f"Player_{random.randint(1000, 9999)}"
                    print(f"Submitting score as {player_name}: {score}")
                    requests.post(f"{SERVER_URL}/scores", json={
                        "player_name": player_name,
                        "score": score,
                        "level": level
                    })
                except Exception as e:
                    print(f"Error submitting score: {e}")
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
