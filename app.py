import os
import logging
import json
import time
import numpy as np
from flask import Flask, request, jsonify, render_template, send_from_directory
import io

# Configure environment for headless pygame
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

# Initialize logging before any pygame import
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Flask app
app = Flask(__name__)

# Only configure AWS services if not in local development mode
if os.environ.get('ENVIRONMENT') != 'local':
    try:
        import boto3
        from aws_xray_sdk.core import xray_recorder
        from aws_xray_sdk.ext.flask.middleware import XRayMiddleware
        import watchtower
        from pythonjsonlogger import jsonlogger
        
        # Configure AWS X-Ray with Fargate-compatible settings
        plugins = ('EC2Plugin', 'ECSPlugin')
        xray_recorder.configure(
            service='cloud-defender-game',
            plugins=plugins,
            context_missing='LOG_ERROR'
        )
        XRayMiddleware(app, xray_recorder)
        logger.info("X-Ray configured successfully")
        
        # Add CloudWatch logging handler if running in production
        if os.environ.get('ENVIRONMENT') == 'production':
            cwl_handler = watchtower.CloudWatchLogHandler(
                log_group=os.environ.get('LOG_GROUP_NAME', 'cloud-defender-logs'),
                stream_name=os.environ.get('TASK_ID', 'unknown'),
                create_log_group=True
            )
            log_formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
            cwl_handler.setFormatter(log_formatter)
            logger.addHandler(cwl_handler)
            logger.info("CloudWatch logging configured")
        
        # Initialize DynamoDB client
        dynamodb = boto3.resource('dynamodb')
        table_name = os.environ.get('DYNAMODB_TABLE', 'GameScores')
        table = dynamodb.Table(table_name)
        logger.info(f"DynamoDB table initialized: {table_name}")
        use_dynamodb = True
    except Exception as e:
        logger.error(f"Error initializing AWS services: {str(e)}")
        use_dynamodb = False
else:
    logger.info("Running in local mode - AWS services disabled")
    use_dynamodb = False

# Create a fallback in-memory storage for scores
memory_scores = []

try:
    # Import PIL separately to avoid conflicts
    from PIL import Image
    logger.info("PIL imported successfully")
except Exception as e:
    logger.error(f"Error importing PIL: {str(e)}")

# Try importing pygame with error handling
try:
    import pygame
    logger.info("Pygame imported successfully")
except Exception as e:
    logger.error(f"Error importing pygame: {str(e)}")
    # Continue without pygame as it's only needed for the client

# Initialize Flask app
app = Flask(__name__)

# Configure AWS X-Ray with Fargate-compatible settings
plugins = ('EC2Plugin', 'ECSPlugin')
try:
    xray_recorder.configure(
        service='cloud-defender-game',
        plugins=plugins,
        context_missing='LOG_ERROR'
    )
    XRayMiddleware(app, xray_recorder)
    logger.info("X-Ray configured successfully")
except Exception as e:
    logger.error(f"Error configuring X-Ray: {str(e)}")

# Add CloudWatch logging handler if running in production
if os.environ.get('ENVIRONMENT') == 'production':
    try:
        cwl_handler = watchtower.CloudWatchLogHandler(
            log_group=os.environ.get('LOG_GROUP_NAME', 'cloud-defender-logs'),
            stream_name=os.environ.get('TASK_ID', 'unknown'),
            create_log_group=True
        )
        log_formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
        cwl_handler.setFormatter(log_formatter)
        logger.addHandler(cwl_handler)
        logger.info("CloudWatch logging configured")
    except Exception as e:
        logger.error(f"Error configuring CloudWatch logging: {str(e)}")

# Initialize DynamoDB client
try:
    dynamodb = boto3.resource('dynamodb')
    table_name = os.environ.get('DYNAMODB_TABLE', 'GameScores')
    table = dynamodb.Table(table_name)
    logger.info(f"DynamoDB table initialized: {table_name}")
except Exception as e:
    logger.error(f"Error initializing DynamoDB: {str(e)}")
    # Create a fallback in-memory storage for scores
    memory_scores = []

# Game constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PLAYER_SPEED = 5
BULLET_SPEED = 10
ENEMY_SPEED = 3
MAX_ENEMIES = 10

# Game state (headless mode for server)
class GameState:
    def __init__(self):
        self.player_x = SCREEN_WIDTH // 2
        self.player_y = SCREEN_HEIGHT - 50
        self.player_health = 100
        self.score = 0
        self.bullets = []  # List of [x, y] positions
        self.enemies = []  # List of [x, y, type] positions
        self.game_over = False
        self.level = 1
        logger.info("New game state initialized")
        
    def update(self):
        try:
            # Move bullets
            new_bullets = []
            for bullet in self.bullets:
                bullet[1] -= BULLET_SPEED
                if bullet[1] > 0:
                    new_bullets.append(bullet)
            self.bullets = new_bullets
            
            # Move enemies
            new_enemies = []
            for enemy in self.enemies:
                enemy[1] += ENEMY_SPEED
                
                # Check if enemy hit player
                if (abs(enemy[0] - self.player_x) < 30 and 
                    abs(enemy[1] - self.player_y) < 30):
                    self.player_health -= 10
                    if self.player_health <= 0:
                        self.game_over = True
                        logger.info(f"Game over. Final score: {self.score}")
                    continue
                    
                # Check if enemy reached bottom
                if enemy[1] < SCREEN_HEIGHT:
                    new_enemies.append(enemy)
            self.enemies = new_enemies
            
            # Check bullet-enemy collisions with more generous hit detection
            for bullet in self.bullets[:]:
                for enemy in self.enemies[:]:
                    # Use a more generous hit radius for better hit detection
                    dx = bullet[0] - enemy[0]
                    dy = bullet[1] - enemy[1]
                    distance = (dx * dx + dy * dy) ** 0.5  # Square root for distance
                    
                    # Increased hit radius (25 pixels)
                    if distance < 25:
                        if bullet in self.bullets:
                            self.bullets.remove(bullet)
                        if enemy in self.enemies:
                            self.enemies.remove(enemy)
                        self.score += 10 * self.level
                        break
            
            # Spawn new enemies
            if len(self.enemies) < MAX_ENEMIES and np.random.random() < 0.05:
                enemy_x = np.random.randint(50, SCREEN_WIDTH - 50)
                enemy_y = 0
                enemy_type = np.random.choice(['ec2', 's3', 'lambda'])
                self.enemies.append([enemy_x, enemy_y, enemy_type])
                
            # Level up
            if self.score > self.level * 500:
                self.level += 1
                logger.info(f"Level up: {self.level}")
        except Exception as e:
            logger.error(f"Error in game state update: {str(e)}")
            
    def to_dict(self):
        return {
            'player': {
                'x': self.player_x,
                'y': self.player_y,
                'health': self.player_health
            },
            'bullets': self.bullets,
            'enemies': self.enemies,
            'score': self.score,
            'level': self.level,
            'game_over': self.game_over
        }

# Create a global game state
try:
    game_state = GameState()
    logger.info("Global game state created successfully")
except Exception as e:
    logger.error(f"Error creating game state: {str(e)}")
    # Create a simplified game state if GameState fails
    class SimpleGameState:
        def __init__(self):
            self.player_x = SCREEN_WIDTH // 2
            self.player_y = SCREEN_HEIGHT - 50
            self.player_health = 100
            self.score = 0
            self.bullets = []
            self.enemies = []
            self.game_over = False
            self.level = 1
            
        def update(self):
            pass
            
        def to_dict(self):
            return {
                'player': {
                    'x': self.player_x,
                    'y': self.player_y,
                    'health': self.player_health
                },
                'bullets': self.bullets,
                'enemies': self.enemies,
                'score': self.score,
                'level': self.level,
                'game_over': self.game_over
            }
    
    game_state = SimpleGameState()
    logger.info("Simplified game state created as fallback")

@app.route('/assets/<path:filename>')
def serve_asset(filename):
    """Serve assets"""
    return send_from_directory('assets', filename)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the load balancer"""
    logger.info("Health check requested")
    return jsonify({'status': 'healthy'}), 200

@app.route('/', methods=['GET'])
def index():
    """Serve the game interface"""
    logger.info("Serving main game interface")
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cloud Defender</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                text-align: center;
                background-color: #232f3e;
                color: white;
                margin: 0;
                padding: 0;
            }
            h1 { color: #ff9900; margin-top: 20px; }
            .container {
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            .game-container {
                width: 800px;
                height: 600px;
                margin: 0 auto;
                background-color: #000;
                background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600"><rect width="800" height="600" fill="%23000033"/><circle cx="50" cy="50" r="1" fill="%23fff" opacity="0.3"/><circle cx="150" cy="80" r="0.8" fill="%23fff" opacity="0.4"/><circle cx="250" cy="150" r="0.6" fill="%23fff" opacity="0.3"/><circle cx="350" cy="220" r="1.2" fill="%23fff" opacity="0.5"/><circle cx="450" cy="280" r="0.7" fill="%23fff" opacity="0.3"/><circle cx="550" cy="350" r="0.9" fill="%23fff" opacity="0.4"/><circle cx="650" cy="420" r="1.1" fill="%23fff" opacity="0.5"/><circle cx="750" cy="480" r="0.8" fill="%23fff" opacity="0.3"/><circle cx="100" cy="520" r="1" fill="%23fff" opacity="0.4"/><circle cx="200" cy="100" r="0.7" fill="%23fff" opacity="0.3"/><circle cx="300" cy="180" r="0.9" fill="%23fff" opacity="0.5"/><circle cx="400" cy="250" r="0.6" fill="%23fff" opacity="0.3"/><circle cx="500" cy="320" r="1.2" fill="%23fff" opacity="0.4"/><circle cx="600" cy="390" r="0.8" fill="%23fff" opacity="0.3"/><circle cx="700" cy="460" r="0.7" fill="%23fff" opacity="0.5"/><circle cx="120" cy="540" r="0.9" fill="%23fff" opacity="0.4"/><path d="M0,150 Q400,50 800,200" stroke="%234B0082" stroke-width="3" fill="none" opacity="0.2"/><path d="M0,300 Q400,400 800,350" stroke="%234B0082" stroke-width="2" fill="none" opacity="0.1"/><path d="M0,450 Q400,500 800,400" stroke="%234B0082" stroke-width="4" fill="none" opacity="0.15"/></svg>');
                position: relative;
                overflow: hidden;
                border: 2px solid #ff9900;
                border-radius: 5px;
            }
            .player {
                width: 40px;
                height: 60px;
                background-image: url('/assets/spaceship.svg');
                background-size: contain;
                background-repeat: no-repeat;
                position: absolute;
                bottom: 60px;
                left: 50%;
                transform: translateX(-50%);
                z-index: 10;
                filter: drop-shadow(0 0 10px #00aaff);
            }
            .bullet {
                width: 8px;
                height: 16px;
                background-image: url('/assets/bullet.svg');
                background-size: contain;
                background-repeat: no-repeat;
                position: absolute;
                z-index: 5;
                filter: drop-shadow(0 0 5px #ffff00);
            }
            .enemy-bullet {
                width: 8px;
                height: 16px;
                background-image: url('/assets/enemy_bullet.svg');
                background-size: contain;
                background-repeat: no-repeat;
                position: absolute;
                z-index: 5;
            }
            .enemy {
                width: 40px;
                height: 40px;
                position: absolute;
                background-size: contain;
                background-repeat: no-repeat;
                z-index: 5;
                filter: contrast(1.2) brightness(1.1);
            }
            .enemy.ddos { 
                background-image: url('/assets/enemy_ddos.svg');
                filter: drop-shadow(0 0 5px #ff3333);
            }
            .enemy.malware { 
                background-image: url('/assets/enemy_malware.svg');
                filter: drop-shadow(0 0 5px #33ff33);
            }
            .enemy.hacker { 
                background-image: url('/assets/enemy_hacker.svg');
                filter: drop-shadow(0 0 5px #3333ff);
            }
            .boss {
                width: 80px;
                height: 80px;
                background-size: contain;
                background-repeat: no-repeat;
                position: absolute;
                z-index: 15;
            }
            .boss.level1 {
                background-image: url('/assets/boss_level1.svg');
            }
            .boss.level2 {
                background-image: url('/assets/boss_level2.svg');
            }
            .boss.level3 {
                background-image: url('/assets/boss_level3.svg');
            }
            .boss-health-container {
                width: 80px;
                height: 8px;
                background-color: #333;
                position: absolute;
                border-radius: 4px;
                overflow: hidden;
                z-index: 16;
            }
            .boss-health-bar {
                height: 100%;
                background-color: #E91E63;
                width: 100%;
            }
            .aws-resources {
                width: 600px;
                height: 40px;
                background-image: url('assets/aws_resources.svg');
                background-size: contain;
                background-repeat: no-repeat;
                position: absolute;
                bottom: 0;
                left: 50%;
                transform: translateX(-50%);
                z-index: 8;
            }
            .aws-health-container {
                width: 600px;
                height: 5px;
                background-color: #333;
                position: absolute;
                bottom: 45px;
                left: 50%;
                transform: translateX(-50%);
                border-radius: 2px;
                overflow: hidden;
                z-index: 9;
            }
            .aws-health-bar {
                height: 100%;
                background-color: #4CAF50;
                width: 100%;
            }
            .powerup {
                width: 30px;
                height: 30px;
                position: absolute;
                background-size: contain;
                background-repeat: no-repeat;
                z-index: 7;
                animation: pulse 1.5s infinite;
            }
            .powerup.health {
                background-image: url('assets/powerup_health.svg');
            }
            .powerup.double {
                background-image: url('assets/powerup_double.svg');
            }
            .powerup.shield {
                background-image: url('assets/powerup_shield.svg');
            }
            @keyframes pulse {
                0% { transform: scale(1); opacity: 1; }
                50% { transform: scale(1.1); opacity: 0.8; }
                100% { transform: scale(1); opacity: 1; }
            }
            .shield-effect {
                width: 60px;
                height: 80px;
                border-radius: 50%;
                border: 2px solid #FFC107;
                position: absolute;
                bottom: 50px;
                left: 50%;
                transform: translateX(-50%);
                z-index: 9;
                animation: shield-pulse 1s infinite;
            }
            @keyframes shield-pulse {
                0% { box-shadow: 0 0 5px 2px rgba(255, 193, 7, 0.5); }
                50% { box-shadow: 0 0 10px 5px rgba(255, 193, 7, 0.7); }
                100% { box-shadow: 0 0 5px 2px rgba(255, 193, 7, 0.5); }
            }
            .explosion {
                width: 40px;
                height: 40px;
                background-image: url('assets/explosion.svg');
                background-size: contain;
                background-repeat: no-repeat;
                position: absolute;
                z-index: 15;
                animation: explode 0.5s forwards;
            }
            @keyframes explode {
                0% { transform: scale(0.5); opacity: 1; }
                100% { transform: scale(1.5); opacity: 0; }
            }
            .level-up {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                color: #FF9900;
                font-size: 48px;
                font-weight: bold;
                text-shadow: 0 0 10px #FF5722;
                opacity: 0;
                z-index: 20;
                animation: levelUp 2s forwards;
            }
            @keyframes levelUp {
                0% { opacity: 0; transform: translate(-50%, -50%) scale(0.5); }
                50% { opacity: 1; transform: translate(-50%, -50%) scale(1.2); }
                100% { opacity: 0; transform: translate(-50%, -50%) scale(1.5); }
            }
            .game-info {
                background-color: #1a232e;
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
            }
            .score-table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            .score-table th, .score-table td {
                padding: 10px;
                border: 1px solid #465973;
            }
            .score-table th {
                background-color: #465973;
            }
            .button {
                background-color: #ff9900;
                color: #232f3e;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                cursor: pointer;
                margin: 10px;
            }
            .button:hover {
                background-color: #ffac33;
            }
            .hud {
                display: flex;
                justify-content: space-between;
                padding: 10px;
                background-color: rgba(0,0,0,0.7);
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                z-index: 20;
            }
            .health-bar {
                width: 200px;
                height: 20px;
                background-color: #ff0000;
                position: relative;
                border-radius: 10px;
                overflow: hidden;
            }
            .health-bar-fill {
                height: 100%;
                background-color: #00cc00;
                width: 100%;
                transition: width 0.3s;
            }
            .game-over {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                text-align: center;
                color: white;
                font-size: 24px;
                background-color: rgba(0,0,0,0.8);
                padding: 20px;
                border-radius: 10px;
                display: none;
                z-index: 30;
            }
            .controls {
                margin-top: 10px;
                display: flex;
                justify-content: center;
            }
            .control-btn {
                background-color: #465973;
                color: white;
                border: none;
                padding: 15px 25px;
                margin: 0 10px;
                border-radius: 5px;
                font-weight: bold;
                cursor: pointer;
                font-size: 18px;
            }
            .shoot-btn {
                background-color: #ff9900;
                padding: 15px 40px;
            }
            
            .debug-overlay {
                position: absolute;
                top: 10px;
                right: 10px;
                background-color: rgba(0,0,0,0.7);
                color: white;
                padding: 5px;
                font-size: 12px;
                z-index: 100;
                display: none;
            }
            
            /* Hitbox visualization for debugging */
            .hitbox-debug {
                position: absolute;
                border-radius: 50%;
                pointer-events: none;
                z-index: 100;
                display: none;
            }
            .bullet-hitbox {
                border: 1px solid yellow;
                opacity: 0.5;
            }
            .enemy-hitbox {
                border: 1px solid red;
                opacity: 0.5;
            }
            
            /* Difficulty selector */
            .difficulty-selector {
                margin: 15px 0;
                padding: 10px;
                background-color: #2d3e50;
                border-radius: 5px;
            }
            
            .difficulty-btn {
                background-color: #465973;
                color: white;
                border: none;
                padding: 8px 15px;
                margin: 0 5px;
                border-radius: 5px;
                font-weight: bold;
                cursor: pointer;
            }
            
            .difficulty-btn.selected {
                background-color: #ff9900;
                color: #232f3e;
            }
            
            /* Control mode buttons */
            .control-mode-btn {
                background-color: #465973;
                color: white;
                border: none;
                padding: 8px 15px;
                margin: 0 5px;
                border-radius: 5px;
                font-weight: bold;
                cursor: pointer;
            }
            
            .control-mode-btn.selected {
                background-color: #ff9900;
                color: #232f3e;
            }
            
            /* Settings sections */
            .settings-section {
                margin: 15px 0;
                padding: 10px;
                background-color: #2d3e50;
                border-radius: 5px;
            }
            
            .settings-section h3 {
                margin-top: 0;
                color: #ff9900;
            }
            
            /* Difficulty modal */
            .difficulty-modal {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.9);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 50;
            }
            
            .difficulty-modal-content {
                background-color: #1a232e;
                padding: 30px;
                border-radius: 10px;
                text-align: center;
                border: 2px solid #ff9900;
                width: 80%;
                max-width: 500px;
            }
            
            .difficulty-buttons, .control-mode-buttons {
                margin: 10px 0;
                display: flex;
                justify-content: center;
                flex-wrap: wrap;
            }
            
            /* Make the game container responsive */
            @media (max-width: 820px) {
                .game-container {
                    width: 100%;
                    height: 500px;
                }
                .container {
                    width: 100%;
                    padding: 10px;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Cloud Defender</h1>
            
            <div class="game-container" id="game-container">
                <div class="hud">
                    <div>
                        <div class="health-bar">
                            <div class="health-bar-fill" id="health-bar"></div>
                        </div>
                        <div id="health-text">Health: 100</div>
                    </div>
                    <div>
                        <div id="score">Score: 0</div>
                        <div id="level">Level: 1</div>
                    </div>
                </div>
                <div class="player" id="player"></div>
                <div class="aws-resources" id="aws-resources"></div>
                <div class="aws-health-container">
                    <div class="aws-health-bar" id="aws-health-bar"></div>
                </div>
                <div class="game-over" id="game-over">
                    <h2>GAME OVER</h2>
                    <p id="final-score">Final Score: 0</p>
                    <form id="score-form">
                        <input type="text" id="player-name" placeholder="Your Name" required>
                        <button type="submit" class="button">Submit Score</button>
                    </form>
                </div>
                <div class="debug-overlay" id="debug-overlay"></div>
            <div class="difficulty-modal" id="difficulty-modal">
                <div class="difficulty-modal-content">
                    <h2>Select Game Settings</h2>
                    
                    <div class="settings-section">
                        <h3>Difficulty:</h3>
                        <div class="difficulty-buttons">
                            <button class="difficulty-btn selected" id="modal-easy-btn">Easy</button>
                            <button class="difficulty-btn" id="modal-medium-btn">Medium</button>
                            <button class="difficulty-btn" id="modal-hard-btn">Hard</button>
                        </div>
                    </div>
                    
                    <div class="settings-section">
                        <h3>Control Mode:</h3>
                        <div class="control-mode-buttons">
                            <button class="control-mode-btn selected" id="touch-mode-btn">Touch/Click</button>
                            <button class="control-mode-btn" id="keyboard-mode-btn">Keyboard</button>
                            <button class="control-mode-btn" id="mouse-mode-btn">Mouse</button>
                        </div>
                    </div>
                    
                    <button class="button" id="start-game-btn">Start Game</button>
                </div>
            </div>
            </div>
            
            <div class="controls">
                <button class="control-btn" id="left-btn">◀ LEFT</button>
                <button class="control-btn shoot-btn" id="shoot-btn">SHOOT</button>
                <button class="control-btn" id="right-btn">RIGHT ▶</button>
            </div>
            
            <div class="game-info">
                <h2>Game Description</h2>
                <p>Defend your AWS cloud infrastructure from various threats! Control your AWS Shield and shoot down malicious entities before they breach your defenses.</p>
                <p>This game runs in a serverless container on Amazon ECS with Fargate and stores high scores in DynamoDB.</p>
                <h3>How to Play</h3>
                <p>Use the LEFT and RIGHT buttons to move and SHOOT button to fire.</p>
                <p>On desktop, you can also use arrow keys to move and spacebar to shoot.</p>
                <a href="/download" class="button">Download Full Game Client</a>
            </div>
            
            <div class="game-info">
                <h2>High Scores</h2>
                <div id="high-scores">Loading high scores...</div>
            </div>
        </div>
        
        <script>
            // Game variables
            const gameContainer = document.getElementById('game-container');
            const player = document.getElementById('player');
            const healthBar = document.getElementById('health-bar');
            const healthText = document.getElementById('health-text');
            const scoreDisplay = document.getElementById('score');
            const levelDisplay = document.getElementById('level');
            const gameOverScreen = document.getElementById('game-over');
            const finalScoreDisplay = document.getElementById('final-score');
            const debugOverlay = document.getElementById('debug-overlay');
            const difficultyModal = document.getElementById('difficulty-modal');
            const awsHealthBar = document.getElementById('aws-health-bar');
            
            // Difficulty buttons in modal
            const easyBtn = document.getElementById('modal-easy-btn');
            const mediumBtn = document.getElementById('modal-medium-btn');
            const hardBtn = document.getElementById('modal-hard-btn');
            const startGameBtn = document.getElementById('start-game-btn');
            
            // Control mode buttons
            const touchModeBtn = document.getElementById('touch-mode-btn');
            const keyboardModeBtn = document.getElementById('keyboard-mode-btn');
            const mouseModeBtn = document.getElementById('mouse-mode-btn');
            
            let playerX = 400;
            let playerHealth = 100;
            let awsHealth = 100;
            let score = 0;
            let level = 1;
            let bullets = [];
            let enemyBullets = [];
            let enemies = [];
            let powerups = [];
            let boss = null;
            let bossActive = false;
            let bossHealth = 0;
            let bossMaxHealth = 0;
            let gameOver = false;
            let gameActive = false;
            let difficulty = 'easy'; // Default difficulty
            let controlMode = 'touch'; // Default control mode
            let enemiesDefeated = 0;
            let enemiesRequiredForBoss = 20; // Number of enemies to defeat before boss appears
            let hasShield = false;
            let hasDoubleShot = false;
            let shieldElement = null;
            
            // Constants
            const PLAYER_SPEED = 10;
            const BULLET_SPEED = 8;
            const ENEMY_BULLET_SPEED = 5;
            const POWERUP_SPEED = 2;
            let ENEMY_SPEED = 2; // Will be adjusted based on difficulty
            let MAX_ENEMIES = 8; // Will be adjusted based on difficulty
            const CONTAINER_WIDTH = 800;
            const CONTAINER_HEIGHT = 600;
            const ENEMY_SHOOTING_CHANCE = 0.005; // Chance of enemy shooting per frame
            const BOSS_SHOOTING_CHANCE = 0.05; // Chance of boss shooting per frame
            const BOSS_MOVE_CHANCE = 0.02; // Chance of boss changing direction
            const POWERUP_DROP_CHANCE = 0.3; // Chance of enemy dropping powerup when destroyed
            const SHIELD_DURATION = 10000; // Shield powerup duration in milliseconds
            const DOUBLE_SHOT_DURATION = 15000; // Double shot powerup duration in milliseconds
            
            // Enemy types
            const ENEMY_TYPES = ['ddos', 'malware', 'hacker'];
            
            // Powerup types
            const POWERUP_TYPES = ['health', 'double', 'shield'];
            
            // Difficulty settings
            const DIFFICULTY_SETTINGS = {
                easy: {
                    enemySpeed: 2.0,
                    maxEnemies: 6,
                    spawnBaseDelay: 2000,
                    spawnLevelFactor: 100,
                    minSpawnDelay: 800,
                    enemyShootingMultiplier: 0.5,
                    bossHealthMultiplier: 1.0,
                    powerupDropChanceMultiplier: 1.5
                },
                medium: {
                    enemySpeed: 2.5,
                    maxEnemies: 8,
                    spawnBaseDelay: 1800,
                    spawnLevelFactor: 120,
                    minSpawnDelay: 700,
                    enemyShootingMultiplier: 1.0,
                    bossHealthMultiplier: 1.5,
                    powerupDropChanceMultiplier: 1.0
                },
                hard: {
                    enemySpeed: 3.0,
                    maxEnemies: 10,
                    spawnBaseDelay: 1500,
                    spawnLevelFactor: 150,
                    minSpawnDelay: 500,
                    enemyShootingMultiplier: 1.5,
                    bossHealthMultiplier: 2.0,
                    powerupDropChanceMultiplier: 0.7
                }
            };
            
            // Initialize player position
            player.style.left = playerX + 'px';
            
            // Control buttons
            document.getElementById('left-btn').addEventListener('mousedown', () => movePlayer('left'));
            document.getElementById('right-btn').addEventListener('mousedown', () => movePlayer('right'));
            document.getElementById('shoot-btn').addEventListener('click', shootBullet);
            
            // Difficulty buttons in modal
            easyBtn.addEventListener('click', () => selectDifficulty('easy'));
            mediumBtn.addEventListener('click', () => selectDifficulty('medium'));
            hardBtn.addEventListener('click', () => selectDifficulty('hard'));
            
            // Control mode buttons
            touchModeBtn.addEventListener('click', () => selectControlMode('touch'));
            keyboardModeBtn.addEventListener('click', () => selectControlMode('keyboard'));
            mouseModeBtn.addEventListener('click', () => selectControlMode('mouse'));
            
            startGameBtn.addEventListener('click', startGame);
            
            // Keyboard controls
            document.addEventListener('keydown', (e) => {
                if (!gameActive) return;
                
                // Prevent default spacebar behavior (scrolling)
                if (e.key === ' ' || e.code === 'Space') {
                    e.preventDefault();
                    shootBullet();
                }
                
                if (e.key === 'ArrowLeft') {
                    movePlayer('left');
                } else if (e.key === 'ArrowRight') {
                    movePlayer('right');
                }
            });
            
            // Set difficulty
            function selectDifficulty(newDifficulty) {
                difficulty = newDifficulty;
                
                // Update UI
                easyBtn.classList.remove('selected');
                mediumBtn.classList.remove('selected');
                hardBtn.classList.remove('selected');
                
                if (newDifficulty === 'easy') {
                    easyBtn.classList.add('selected');
                } else if (newDifficulty === 'medium') {
                    mediumBtn.classList.add('selected');
                } else {
                    hardBtn.classList.add('selected');
                }
            }
            
            // Set control mode
            function selectControlMode(newControlMode) {
                controlMode = newControlMode;
                
                // Update UI
                touchModeBtn.classList.remove('selected');
                keyboardModeBtn.classList.remove('selected');
                mouseModeBtn.classList.remove('selected');
                
                if (newControlMode === 'touch') {
                    touchModeBtn.classList.add('selected');
                } else if (newControlMode === 'keyboard') {
                    keyboardModeBtn.classList.add('selected');
                } else {
                    mouseModeBtn.classList.add('selected');
                }
            }
            
            // Functions
            function startGame() {
                // Hide difficulty modal
                difficultyModal.style.display = 'none';
                
                gameActive = true;
                gameOver = false;
                playerHealth = 100;
                awsHealth = 100;
                score = 0;
                level = 1;
                bullets = [];
                enemyBullets = [];
                enemies = [];
                powerups = [];
                boss = null;
                bossActive = false;
                enemiesDefeated = 0;
                enemiesRequiredForBoss = 20 * level;
                hasShield = false;
                hasDoubleShot = false;
                
                // Clear any existing elements
                const existingBullets = document.querySelectorAll('.bullet');
                existingBullets.forEach(bullet => bullet.remove());
                
                const existingEnemyBullets = document.querySelectorAll('.enemy-bullet');
                existingEnemyBullets.forEach(bullet => bullet.remove());
                
                const existingEnemies = document.querySelectorAll('.enemy');
                existingEnemies.forEach(enemy => enemy.remove());
                
                const existingPowerups = document.querySelectorAll('.powerup');
                existingPowerups.forEach(powerup => powerup.remove());
                
                const existingBoss = document.querySelector('.boss');
                if (existingBoss) existingBoss.remove();
                
                const existingBossHealth = document.querySelector('.boss-health-container');
                if (existingBossHealth) existingBossHealth.remove();
                
                const existingShield = document.querySelector('.shield-effect');
                if (existingShield) existingShield.remove();
                
                // Reset displays
                updateHealthBar();
                updateAwsHealthBar();
                scoreDisplay.textContent = 'Score: 0';
                levelDisplay.textContent = 'Level: 1';
                gameOverScreen.style.display = 'none';
                
                // Apply difficulty settings
                const settings = DIFFICULTY_SETTINGS[difficulty];
                ENEMY_SPEED = settings.enemySpeed;
                MAX_ENEMIES = settings.maxEnemies;
                
                // Adjust difficulty based on control mode
                // Mouse control is easier, so make it slightly harder
                if (controlMode === 'mouse') {
                    ENEMY_SPEED *= 1.2;
                    MAX_ENEMIES += 1;
                }
                
                // Show/hide control buttons based on mode
                const controlsDiv = document.querySelector('.controls');
                if (controlMode === 'touch') {
                    controlsDiv.style.display = 'flex';
                } else {
                    controlsDiv.style.display = 'none';
                }
                
                // Set up mouse controls if needed
                if (controlMode === 'mouse') {
                    gameContainer.style.cursor = 'none';
                } else {
                    gameContainer.style.cursor = 'default';
                }
                
                // Start game loop
                gameLoop();
                
                // Start enemy spawning
                enemySpawnLoop();
                
                // Notify server
                fetch('/game/start', { method: 'POST' });
            }
            
            function movePlayer(direction) {
                if (!gameActive) return;
                
                if (direction === 'left' && playerX > 40) {
                    playerX -= PLAYER_SPEED;
                } else if (direction === 'right' && playerX < CONTAINER_WIDTH - 40) {
                    playerX += PLAYER_SPEED;
                }
                
                player.style.left = playerX + 'px';
                
                // Notify server
                fetch('/game/move', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ direction: direction })
                });
            }
            
            function activatePowerup(type) {
                switch(type) {
                    case 'health':
                        // Heal player
                        playerHealth = Math.min(100, playerHealth + 30);
                        updateHealthBar();
                        
                        // Heal AWS resources
                        awsHealth = Math.min(100, awsHealth + 20);
                        updateAwsHealthBar();
                        break;
                        
                    case 'double':
                        // Check if already has double shot
                        if (hasDoubleShot) {
                            // Upgrade to quad shot
                            hasDoubleShot = 'quad';
                            
                            // Show visual indicator
                            player.style.filter = "brightness(1.5) hue-rotate(120deg)";
                        } else {
                            // Activate double shot
                            hasDoubleShot = true;
                            
                            // Show visual indicator
                            player.style.filter = "brightness(1.3) hue-rotate(240deg)";
                        }
                        
                        // Set timeout to deactivate
                        setTimeout(() => {
                            hasDoubleShot = false;
                            player.style.filter = "";
                        }, DOUBLE_SHOT_DURATION);
                        break;
                        
                    case 'shield':
                        // Activate shield
                        hasShield = true;
                        
                        // Create shield visual
                        if (!shieldElement) {
                            shieldElement = document.createElement('div');
                            shieldElement.className = 'shield-effect';
                            gameContainer.appendChild(shieldElement);
                        }
                        
                        // Set timeout to deactivate
                        setTimeout(() => {
                            hasShield = false;
                            if (shieldElement && shieldElement.parentNode) {
                                shieldElement.parentNode.removeChild(shieldElement);
                                shieldElement = null;
                            }
                        }, SHIELD_DURATION);
                        break;
                }
                
                // Show powerup message
                showLevelUpMessage("POWERUP: " + type.toUpperCase());
            }
            
            function shootBullet() {
                if (!gameActive) return;
                
                // Limit bullet firing rate based on control mode
                const now = Date.now();
                if (controlMode === 'mouse' && bullets.length > 0) {
                    // For mouse mode, enforce a cooldown between shots
                    const lastBullet = bullets[bullets.length - 1];
                    if (lastBullet.timestamp && now - lastBullet.timestamp < 300) {
                        return; // Too soon to fire again
                    }
                }
                
                if (hasDoubleShot === 'quad') {
                    // Create four bullets
                    const positions = [
                        { x: playerX - 15, y: CONTAINER_HEIGHT - 100 },
                        { x: playerX - 5, y: CONTAINER_HEIGHT - 100 },
                        { x: playerX + 5, y: CONTAINER_HEIGHT - 100 },
                        { x: playerX + 15, y: CONTAINER_HEIGHT - 100 }
                    ];
                    
                    positions.forEach(pos => {
                        const bullet = document.createElement('div');
                        bullet.className = 'bullet';
                        bullet.style.left = (pos.x - 4) + 'px';
                        bullet.style.bottom = '100px';
                        gameContainer.appendChild(bullet);
                        
                        bullets.push({
                            element: bullet,
                            x: pos.x,
                            y: pos.y,
                            timestamp: now
                        });
                    });
                } else if (hasDoubleShot === true) {
                    // Create left bullet
                    const leftBullet = document.createElement('div');
                    leftBullet.className = 'bullet';
                    leftBullet.style.left = (playerX - 15) + 'px';
                    leftBullet.style.bottom = '100px';
                    gameContainer.appendChild(leftBullet);
                    
                    bullets.push({
                        element: leftBullet,
                        x: playerX - 10,
                        y: CONTAINER_HEIGHT - 100,
                        timestamp: now
                    });
                    
                    // Create right bullet
                    const rightBullet = document.createElement('div');
                    rightBullet.className = 'bullet';
                    rightBullet.style.left = (playerX + 7) + 'px';
                    rightBullet.style.bottom = '100px';
                    gameContainer.appendChild(rightBullet);
                    
                    bullets.push({
                        element: rightBullet,
                        x: playerX + 10,
                        y: CONTAINER_HEIGHT - 100,
                        timestamp: now
                    });
                } else {
                    // Create single bullet
                    const bullet = document.createElement('div');
                    bullet.className = 'bullet';
                    bullet.style.left = (playerX - 4) + 'px';
                    bullet.style.bottom = '100px';
                    gameContainer.appendChild(bullet);
                    
                    bullets.push({
                        element: bullet,
                        x: playerX,
                        y: CONTAINER_HEIGHT - 100,
                        timestamp: now
                    });
                }
                
                // Notify server
                fetch('/game/shoot', { method: 'POST' });
            }
            
            function createEnemy() {
                if (!gameActive || bossActive || enemies.length >= MAX_ENEMIES) return;
                
                const enemyX = Math.floor(Math.random() * (CONTAINER_WIDTH - 60)) + 30;
                const enemyType = ENEMY_TYPES[Math.floor(Math.random() * ENEMY_TYPES.length)];
                
                const enemy = document.createElement('div');
                enemy.className = 'enemy ' + enemyType;
                enemy.style.left = enemyX + 'px';
                enemy.style.top = '0px';
                gameContainer.appendChild(enemy);
                
                // Add some randomness to enemy speed based on type
                let speedMultiplier = 1.0;
                if (enemyType === 'ddos') {
                    speedMultiplier = 1.2; // Faster
                } else if (enemyType === 'malware') {
                    speedMultiplier = 1.0; // Medium
                } else if (enemyType === 'hacker') {
                    speedMultiplier = 0.8; // Slower
                }
                
                // Determine if this enemy can shoot (only after level 1)
                const canShoot = level > 1 && Math.random() < 0.3;
                
                enemies.push({
                    element: enemy,
                    x: enemyX,
                    y: 0,
                    type: enemyType,
                    speed: ENEMY_SPEED * speedMultiplier,
                    canShoot: canShoot
                });
            }
            
            function createBoss() {
                if (!gameActive || bossActive) return;
                
                bossActive = true;
                
                // Calculate boss health based on level and difficulty
                const settings = DIFFICULTY_SETTINGS[difficulty];
                bossMaxHealth = 100 * level * settings.bossHealthMultiplier;
                bossHealth = bossMaxHealth;
                
                // Determine boss type based on level
                const bossLevel = (level - 1) % 3 + 1; // Cycles through 1, 2, 3
                
                // Create boss element
                const bossElement = document.createElement('div');
                bossElement.className = 'boss level' + bossLevel;
                bossElement.style.left = (CONTAINER_WIDTH / 2 - 40) + 'px';
                bossElement.style.top = '50px';
                gameContainer.appendChild(bossElement);
                
                // Create boss health bar
                const bossHealthContainer = document.createElement('div');
                bossHealthContainer.className = 'boss-health-container';
                bossHealthContainer.style.left = (CONTAINER_WIDTH / 2 - 40) + 'px';
                bossHealthContainer.style.top = '40px';
                
                const bossHealthBar = document.createElement('div');
                bossHealthBar.className = 'boss-health-bar';
                bossHealthContainer.appendChild(bossHealthBar);
                gameContainer.appendChild(bossHealthContainer);
                
                // Create boss object
                boss = {
                    element: bossElement,
                    healthContainer: bossHealthContainer,
                    healthBar: bossHealthBar,
                    x: CONTAINER_WIDTH / 2 - 40,
                    y: 50,
                    width: 80,
                    height: 80,
                    speed: 2 + (level * 0.5),
                    direction: Math.random() > 0.5 ? 1 : -1,
                    lastShot: 0,
                    level: bossLevel,
                    lastPowerupDrop: 0
                };
                
                // Show level up message
                showLevelUpMessage("BOSS BATTLE!");
            }
            
            function createPowerup(x, y) {
                if (!gameActive || level <= 1) return; // No powerups in level 1
                
                const powerupType = POWERUP_TYPES[Math.floor(Math.random() * POWERUP_TYPES.length)];
                
                const powerup = document.createElement('div');
                powerup.className = 'powerup ' + powerupType;
                powerup.style.left = (x - 15) + 'px';
                powerup.style.top = y + 'px';
                gameContainer.appendChild(powerup);
                
                powerups.push({
                    element: powerup,
                    x: x,
                    y: y,
                    type: powerupType
                });
            }
            
            function showLevelUpMessage(message) {
                const levelUpMsg = document.createElement('div');
                levelUpMsg.className = 'level-up';
                levelUpMsg.textContent = message;
                gameContainer.appendChild(levelUpMsg);
                
                // Remove the message after animation completes
                setTimeout(() => {
                    if (levelUpMsg.parentNode) {
                        levelUpMsg.parentNode.removeChild(levelUpMsg);
                    }
                }, 2000);
            }
            
            function updateBossHealth() {
                if (!boss || !bossActive) return;
                
                const healthPercent = (bossHealth / bossMaxHealth) * 100;
                boss.healthBar.style.width = healthPercent + '%';
                
                // Change color based on health
                if (healthPercent > 60) {
                    boss.healthBar.style.backgroundColor = '#E91E63'; // Pink
                } else if (healthPercent > 30) {
                    boss.healthBar.style.backgroundColor = '#FF9800'; // Orange
                } else {
                    boss.healthBar.style.backgroundColor = '#F44336'; // Red
                }
            }
            
            function enemyShoot(enemy) {
                if (!gameActive || !enemy.canShoot) return;
                
                const bullet = document.createElement('div');
                bullet.className = 'enemy-bullet';
                bullet.style.left = (enemy.x - 4) + 'px';
                bullet.style.top = (enemy.y + 20) + 'px';
                gameContainer.appendChild(bullet);
                
                enemyBullets.push({
                    element: bullet,
                    x: enemy.x,
                    y: enemy.y + 20
                });
            }
            
            function bossShoot() {
                if (!gameActive || !bossActive || !boss) return;
                
                // Create bullets from all four weapon ports
                const bulletPositions = [
                    { x: boss.x + 15, y: boss.y + 40 },  // Left
                    { x: boss.x + 40, y: boss.y + 15 },  // Top
                    { x: boss.x + 65, y: boss.y + 40 },  // Right
                    { x: boss.x + 40, y: boss.y + 65 }   // Bottom
                ];
                
                bulletPositions.forEach(pos => {
                    const bullet = document.createElement('div');
                    bullet.className = 'enemy-bullet';
                    bullet.style.left = (pos.x - 4) + 'px';
                    bullet.style.top = pos.y + 'px';
                    gameContainer.appendChild(bullet);
                    
                    // Calculate direction towards player
                    const dx = playerX - pos.x;
                    const dy = (CONTAINER_HEIGHT - 40) - pos.y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    
                    enemyBullets.push({
                        element: bullet,
                        x: pos.x,
                        y: pos.y,
                        dx: dx / dist,  // Normalized direction
                        dy: dy / dist
                    });
                });
                
                boss.lastShot = Date.now();
            }
            
            function updateHealthBar() {
                healthBar.style.width = playerHealth + '%';
                healthText.textContent = 'Health: ' + playerHealth;
                
                // Change health bar color based on health level
                if (playerHealth > 60) {
                    healthBar.style.backgroundColor = '#00cc00'; // Green
                } else if (playerHealth > 30) {
                    healthBar.style.backgroundColor = '#ffcc00'; // Yellow
                } else {
                    healthBar.style.backgroundColor = '#ff0000'; // Red
                }
            }
            
            function updateAwsHealthBar() {
                awsHealthBar.style.width = awsHealth + '%';
                
                // Change health bar color based on health level
                if (awsHealth > 60) {
                    awsHealthBar.style.backgroundColor = '#4CAF50'; // Green
                } else if (awsHealth > 30) {
                    awsHealthBar.style.backgroundColor = '#FFC107'; // Amber
                } else {
                    awsHealthBar.style.backgroundColor = '#F44336'; // Red
                }
            }
            
            function checkCollisions() {
                // Check bullet-enemy collisions
                for (let i = bullets.length - 1; i >= 0; i--) {
                    if (i >= bullets.length) continue; // Safety check
                    
                    const bullet = bullets[i];
                    const bulletRect = {
                        x: bullet.x - 4,
                        y: bullet.y - 8,
                        width: 8,
                        height: 16
                    };
                    
                    // Check for boss collision first
                    if (bossActive && boss) {
                        const bossRect = {
                            x: boss.x,
                            y: boss.y,
                            width: boss.width,
                            height: boss.height
                        };
                        
                        if (bulletRect.x < bossRect.x + bossRect.width &&
                            bulletRect.x + bulletRect.width > bossRect.x &&
                            bulletRect.y < bossRect.y + bossRect.height &&
                            bulletRect.y + bulletRect.height > bossRect.y) {
                            
                            // Create explosion effect
                            createExplosion(bullet.x, bullet.y);
                            
                            // Remove bullet
                            if (bullet.element && bullet.element.parentNode) {
                                bullet.element.remove();
                            }
                            bullets.splice(i, 1);
                            
                            // Damage boss
                            bossHealth -= 5;
                            updateBossHealth();
                            
                            // Check if boss is defeated
                            if (bossHealth <= 0) {
                                // Create big explosion
                                createExplosion(boss.x + 40, boss.y + 40);
                                createExplosion(boss.x + 20, boss.y + 20);
                                createExplosion(boss.x + 60, boss.y + 20);
                                createExplosion(boss.x + 20, boss.y + 60);
                                createExplosion(boss.x + 60, boss.y + 60);
                                
                                // Remove boss
                                boss.element.remove();
                                boss.healthContainer.remove();
                                
                                // Award points
                                score += 500 * level;
                                scoreDisplay.textContent = 'Score: ' + score;
                                
                                // Level up
                                level++;
                                levelDisplay.textContent = 'Level: ' + level;
                                
                                // Show level up message
                                showLevelUpMessage("LEVEL " + level);
                                
                                // Reset for next level
                                bossActive = false;
                                boss = null;
                                enemiesDefeated = 0;
                                enemiesRequiredForBoss = 20 * level;
                            }
                            
                            continue;
                        }
                    }
                    
                    // Check for regular enemy collisions
                    for (let j = enemies.length - 1; j >= 0; j--) {
                        if (j >= enemies.length) continue; // Safety check
                        
                        const enemy = enemies[j];
                        const enemyRect = {
                            x: enemy.x - 20,
                            y: enemy.y - 20,
                            width: 40,
                            height: 40
                        };
                        
                        // Check for bullet-enemy collisions with pixel-perfect hit detection
                        if (bulletRect.x < enemyRect.x + enemyRect.width &&
                            bulletRect.x + bulletRect.width > enemyRect.x &&
                            bulletRect.y < enemyRect.y + enemyRect.height &&
                            bulletRect.y + bulletRect.height > enemyRect.y) {
                            
                            // Always consider it a hit if the centers are close enough
                            const dx = bullet.x - enemy.x;
                            const dy = bullet.y - enemy.y;
                            const distance = Math.sqrt(dx * dx + dy * dy);
                            
                            // Increased hit radius for better hit detection
                            const hitRadius = 25;
                            let hit = distance < hitRadius;
                            
                            if (hit) {
                                // Debug info
                                if (debugOverlay) {
                                    debugOverlay.textContent = `Hit: Bullet(${bullet.x},${bullet.y}) Enemy(${enemy.x},${enemy.y}) Dist:${distance.toFixed(2)}`;
                                    debugOverlay.style.display = 'block';
                                }
                                
                                // Create explosion effect
                                createExplosion(enemy.x, enemy.y);
                                
                                // Collision detected
                                if (bullet.element && bullet.element.parentNode) {
                                    bullet.element.remove();
                                }
                                bullets.splice(i, 1);
                                
                                if (enemy.element && enemy.element.parentNode) {
                                    enemy.element.remove();
                                }
                                
                                // Check if enemy should drop powerup (only after level 1)
                                if (level > 1) {
                                    const settings = DIFFICULTY_SETTINGS[difficulty];
                                    if (Math.random() < POWERUP_DROP_CHANCE * settings.powerupDropChanceMultiplier) {
                                        createPowerup(enemy.x, enemy.y);
                                    }
                                }
                                
                                enemies.splice(j, 1);
                                
                                // Increment enemies defeated counter
                                enemiesDefeated++;
                                
                                score += 10 * level;
                                scoreDisplay.textContent = 'Score: ' + score;
                            }
                            break;
                        }
                    }
                }
                
                // Check enemy bullet-player collisions
                for (let i = enemyBullets.length - 1; i >= 0; i--) {
                    if (i >= enemyBullets.length) continue; // Safety check
                    
                    const bullet = enemyBullets[i];
                    const bulletRect = {
                        x: bullet.x - 4,
                        y: bullet.y - 8,
                        width: 8,
                        height: 16
                    };
                    
                    const playerRect = {
                        x: playerX - 20,
                        y: CONTAINER_HEIGHT - 60,
                        width: 40,
                        height: 40
                    };
                    
                    // Check for rectangle collision
                    if (bulletRect.x < playerRect.x + playerRect.width &&
                        bulletRect.x + bulletRect.width > playerRect.x &&
                        bulletRect.y < playerRect.y + playerRect.height &&
                        bulletRect.y + bulletRect.height > playerRect.y) {
                        
                        // Create explosion effect
                        createExplosion(bullet.x, bullet.y);
                        
                        // Collision detected
                        if (bullet.element && bullet.element.parentNode) {
                            bullet.element.remove();
                        }
                        enemyBullets.splice(i, 1);
                        
                        // Check if player has shield
                        if (!hasShield) {
                            playerHealth -= 10;
                            updateHealthBar();
                            
                            if (playerHealth <= 0) {
                                endGame();
                            }
                        }
                    }
                }
                
                // Check enemy-player collisions
                for (let i = enemies.length - 1; i >= 0; i--) {
                    if (i >= enemies.length) continue; // Safety check
                    
                    const enemy = enemies[i];
                    const enemyRect = {
                        x: enemy.x - 20,
                        y: enemy.y - 20,
                        width: 40,
                        height: 40
                    };
                    
                    const playerRect = {
                        x: playerX - 20,
                        y: CONTAINER_HEIGHT - 60,
                        width: 40,
                        height: 40
                    };
                    
                    // Check for rectangle collision
                    if (enemyRect.x < playerRect.x + playerRect.width &&
                        enemyRect.x + enemyRect.width > playerRect.x &&
                        enemyRect.y < playerRect.y + playerRect.height &&
                        enemyRect.y + enemyRect.height > playerRect.y) {
                        
                        // Create explosion effect
                        createExplosion(enemy.x, enemy.y);
                        
                        // Collision detected
                        if (enemy.element && enemy.element.parentNode) {
                            enemy.element.remove();
                        }
                        enemies.splice(i, 1);
                        
                        // Check if player has shield
                        if (!hasShield) {
                            playerHealth -= 10;
                            updateHealthBar();
                            
                            if (playerHealth <= 0) {
                                endGame();
                            }
                        }
                    }
                }
                
                // Check powerup-player collisions with improved hit detection
                for (let i = powerups.length - 1; i >= 0; i--) {
                    if (i >= powerups.length) continue; // Safety check
                    
                    const powerup = powerups[i];
                    const powerupRect = {
                        x: powerup.x - 15,
                        y: powerup.y - 15,
                        width: 30,
                        height: 30
                    };
                    
                    const playerRect = {
                        x: playerX - 20,
                        y: CONTAINER_HEIGHT - 60,
                        width: 40,
                        height: 40
                    };
                    
                    // First do a quick rectangle check
                    if (powerupRect.x < playerRect.x + playerRect.width &&
                        powerupRect.x + powerupRect.width > playerRect.x &&
                        powerupRect.y < playerRect.y + playerRect.height &&
                        powerupRect.y + powerupRect.height > playerRect.y) {
                        
                        // More precise collision detection based on distance
                        const dx = powerup.x - playerX;
                        const dy = powerup.y - (CONTAINER_HEIGHT - 40);
                        const distance = Math.sqrt(dx * dx + dy * dy);
                        
                        if (distance < 35) { // Adjusted collision radius
                            // Activate powerup
                            activatePowerup(powerup.type);
                            
                            // Remove powerup
                            if (powerup.element && powerup.element.parentNode) {
                                powerup.element.remove();
                            }
                            powerups.splice(i, 1);
                        }
                    }
                }
                
                // Check boss-player collision
                if (bossActive && boss) {
                    const bossRect = {
                        x: boss.x,
                        y: boss.y,
                        width: boss.width,
                        height: boss.height
                    };
                    
                    const playerRect = {
                        x: playerX - 20,
                        y: CONTAINER_HEIGHT - 60,
                        width: 40,
                        height: 40
                    };
                    
                    if (bossRect.x < playerRect.x + playerRect.width &&
                        bossRect.x + bossRect.width > playerRect.x &&
                        bossRect.y < playerRect.y + playerRect.height &&
                        bossRect.y + bossRect.height > playerRect.y) {
                        
                        // Check if player has shield
                        if (!hasShield) {
                            // Severe damage to player
                            playerHealth -= 30;
                            updateHealthBar();
                            
                            // Create explosion
                            createExplosion(playerX, CONTAINER_HEIGHT - 40);
                            
                            if (playerHealth <= 0) {
                                endGame();
                            }
                        }
                    }
                }
            }
            
            // Create explosion effect
            function createExplosion(x, y) {
                const explosion = document.createElement('div');
                explosion.className = 'explosion';
                explosion.style.left = (x - 20) + 'px';
                explosion.style.top = (y - 20) + 'px';
                gameContainer.appendChild(explosion);
                
                // Remove explosion element after animation completes
                setTimeout(() => {
                    if (explosion.parentNode) {
                        explosion.parentNode.removeChild(explosion);
                    }
                }, 500);
            }
            
            function endGame() {
                gameActive = false;
                gameOver = true;
                
                // Reset cursor if in mouse mode
                if (controlMode === 'mouse') {
                    gameContainer.style.cursor = 'default';
                }
                
                // Create explosion for player ship
                createExplosion(playerX, CONTAINER_HEIGHT - 40);
                
                finalScoreDisplay.textContent = 'Final Score: ' + score;
                gameOverScreen.style.display = 'block';
                
                // Set up score submission
                document.getElementById('score-form').addEventListener('submit', function(e) {
                    e.preventDefault();
                    const playerName = document.getElementById('player-name').value;
                    
                    fetch('/scores', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            player_name: playerName,
                            score: score,
                            level: level,
                            difficulty: difficulty,
                            control_mode: controlMode
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        alert('Score submitted!');
                        // Show difficulty modal again
                        difficultyModal.style.display = 'flex';
                        gameOverScreen.style.display = 'none';
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        alert('Error submitting score');
                    });
                });
            }
            
            function gameLoop() {
                if (!gameActive) return;
                
                // Move bullets
                for (let i = bullets.length - 1; i >= 0; i--) {
                    const bullet = bullets[i];
                    bullet.y -= BULLET_SPEED;
                    bullet.element.style.bottom = (CONTAINER_HEIGHT - bullet.y) + 'px';
                    
                    if (bullet.y < 0) {
                        bullet.element.remove();
                        bullets.splice(i, 1);
                    }
                }
                
                // Move enemy bullets
                for (let i = enemyBullets.length - 1; i >= 0; i--) {
                    const bullet = enemyBullets[i];
                    
                    // If this is a directed bullet (from boss)
                    if (bullet.dx !== undefined && bullet.dy !== undefined) {
                        bullet.x += bullet.dx * ENEMY_BULLET_SPEED;
                        bullet.y += bullet.dy * ENEMY_BULLET_SPEED;
                        bullet.element.style.left = (bullet.x - 4) + 'px';
                        bullet.element.style.top = bullet.y + 'px';
                    } else {
                        // Regular enemy bullet (moves straight down)
                        bullet.y += ENEMY_BULLET_SPEED;
                        bullet.element.style.top = bullet.y + 'px';
                    }
                    
                    // Remove bullets that go off screen
                    if (bullet.y > CONTAINER_HEIGHT || bullet.y < 0 || 
                        bullet.x < 0 || bullet.x > CONTAINER_WIDTH) {
                        bullet.element.remove();
                        enemyBullets.splice(i, 1);
                    }
                }
                
                // Move enemies
                for (let i = enemies.length - 1; i >= 0; i--) {
                    const enemy = enemies[i];
                    // Use enemy's individual speed if available
                    const enemySpeed = enemy.speed || ENEMY_SPEED;
                    enemy.y += enemySpeed;
                    enemy.element.style.top = enemy.y + 'px';
                    
                    // Update enemy x position
                    enemy.element.style.left = enemy.x + 'px';
                    
                    // Enemy shooting (only if they can shoot and after level 1)
                    if (level > 1 && enemy.canShoot) {
                        const settings = DIFFICULTY_SETTINGS[difficulty];
                        if (Math.random() < ENEMY_SHOOTING_CHANCE * settings.enemyShootingMultiplier) {
                            enemyShoot(enemy);
                        }
                    }
                    
                    // Check if enemy reached AWS resources
                    if (enemy.y > CONTAINER_HEIGHT - 50) {
                        // Damage AWS resources
                        awsHealth -= 5;
                        updateAwsHealthBar();
                        
                        // Create explosion
                        createExplosion(enemy.x, enemy.y);
                        
                        // Remove enemy
                        enemy.element.remove();
                        enemies.splice(i, 1);
                        
                        // Check if AWS resources are destroyed
                        if (awsHealth <= 0) {
                            endGame();
                        }
                        
                        continue;
                    }
                    
                    // Remove enemies that go off screen
                    if (enemy.y > CONTAINER_HEIGHT) {
                        enemy.element.remove();
                        enemies.splice(i, 1);
                    }
                }
                
                // Move powerups
                for (let i = powerups.length - 1; i >= 0; i--) {
                    const powerup = powerups[i];
                    powerup.y += POWERUP_SPEED;
                    powerup.element.style.top = powerup.y + 'px';
                    
                    // Remove powerups that go off screen
                    if (powerup.y > CONTAINER_HEIGHT) {
                        powerup.element.remove();
                        powerups.splice(i, 1);
                    }
                }
                
                // Move boss
                if (bossActive && boss) {
                    // Move horizontally
                    boss.x += boss.speed * boss.direction;
                    
                    // Bounce off walls
                    if (boss.x <= 0 || boss.x >= CONTAINER_WIDTH - boss.width) {
                        boss.direction *= -1;
                    }
                    
                    // Random direction change
                    if (Math.random() < BOSS_MOVE_CHANCE) {
                        boss.direction *= -1;
                    }
                    
                    // Update position
                    boss.element.style.left = boss.x + 'px';
                    boss.healthContainer.style.left = boss.x + 'px';
                    
                    // Boss shooting
                    const settings = DIFFICULTY_SETTINGS[difficulty];
                    if (Math.random() < BOSS_SHOOTING_CHANCE * settings.enemyShootingMultiplier) {
                        bossShoot();
                    }
                    
                    // Boss random powerup drop
                    const now = Date.now();
                    if (!boss.lastPowerupDrop || now - boss.lastPowerupDrop > 5000) { // At least 5 seconds between drops
                        if (Math.random() < 0.02) { // 2% chance per frame
                            const powerupType = POWERUP_TYPES[Math.floor(Math.random() * POWERUP_TYPES.length)];
                            createPowerup(boss.x + Math.random() * boss.width, boss.y + boss.height);
                            boss.lastPowerupDrop = now;
                        }
                    }
                }
                
                // Update shield position if active
                if (hasShield && shieldElement) {
                    shieldElement.style.left = playerX + 'px';
                }
                
                // Check collisions
                checkCollisions();
                
                // Continue game loop
                requestAnimationFrame(gameLoop);
            }
            
            function enemySpawnLoop() {
                if (!gameActive) return;
                
                // Don't spawn regular enemies during boss battle
                if (!bossActive) {
                    createEnemy();
                    
                    // Check if it's time for a boss
                    if (enemiesDefeated >= enemiesRequiredForBoss) {
                        createBoss();
                    }
                }
                
                // Adjust spawn rate based on difficulty and level
                const settings = DIFFICULTY_SETTINGS[difficulty];
                let spawnDelay = Math.max(
                    settings.minSpawnDelay, 
                    settings.spawnBaseDelay - (level * settings.spawnLevelFactor)
                );
                
                // Adjust spawn rate based on control mode
                if (controlMode === 'mouse') {
                    spawnDelay *= 0.85; // Spawn enemies faster for mouse control
                }
                
                setTimeout(enemySpawnLoop, spawnDelay);
            }
            
            // Mouse controls
            gameContainer.addEventListener('mousemove', (e) => {
                if (!gameActive || controlMode !== 'mouse') return;
                
                // Get mouse position relative to game container
                const rect = gameContainer.getBoundingClientRect();
                const mouseX = e.clientX - rect.left;
                
                // Move player to mouse position (with boundaries)
                if (mouseX > 20 && mouseX < CONTAINER_WIDTH - 20) {
                    playerX = mouseX;
                    player.style.left = playerX + 'px';
                }
            });
            
            gameContainer.addEventListener('click', (e) => {
                if (!gameActive || controlMode !== 'mouse') return;
                shootBullet();
            });
            
            // Fetch high scores
            fetch('/scores')
                .then(response => response.json())
                .then(data => {
                    const scoresDiv = document.getElementById('high-scores');
                    if (data.length === 0) {
                        scoresDiv.innerHTML = '<p>No high scores yet. Be the first!</p>';
                    } else {
                        let table = '<table class="score-table"><tr><th>Player</th><th>Score</th><th>Level</th><th>Difficulty</th><th>Controls</th><th>Date</th></tr>';
                        data.forEach(score => {
                            const difficulty = score.difficulty || 'easy';
                            const controlMode = score.control_mode || 'touch';
                            table += `<tr><td>${score.player_name}</td><td>${score.score}</td><td>${score.level}</td><td>${difficulty}</td><td>${controlMode}</td><td>${new Date(score.timestamp * 1000).toLocaleString()}</td></tr>`;
                        });
                        table += '</table>';
                        scoresDiv.innerHTML = table;
                    }
                })
                .catch(error => {
                    console.error('Error fetching scores:', error);
                    document.getElementById('high-scores').innerHTML = '<p>Error loading high scores</p>';
                });
                
            // Show difficulty modal at start
            difficultyModal.style.display = 'flex';
        </script>
        <script src="/assets/debug.js"></script>
        <script src="/assets/visual-effects.js"></script>
        <link rel="stylesheet" href="/assets/visual-styles.css">
    </body>
    </html>
    """

@app.route('/download', methods=['GET'])
def download_client():
    """Provide information about downloading the game client"""
    logger.info("Serving download page")
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Download Cloud Defender</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                text-align: center;
                background-color: #232f3e;
                color: white;
            }
            h1 { color: #ff9900; }
            .container {
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            .info-box {
                background-color: #1a232e;
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
                text-align: left;
            }
            pre {
                background-color: #2d3e50;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
                white-space: pre-wrap;
                word-wrap: break-word;
            }
            .button {
                background-color: #ff9900;
                color: #232f3e;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                cursor: pointer;
                margin: 10px;
                text-decoration: none;
                display: inline-block;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Download Cloud Defender</h1>
            <div class="info-box">
                <h2>Game Client</h2>
                <p>To play the full version of Cloud Defender with graphics and sound:</p>
                <ol>
                    <li>Install Python 3.9+ and pip on your computer</li>
                    <li>Install the required packages:</li>
                    <pre>pip install pygame numpy requests pillow</pre>
                    <li>Download the game client code:</li>
                    <pre>
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

# Server URL - replace with your actual server URL
SERVER_URL = "http://your-ecs-service-url"

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
        response = requests.get(f"{SERVER_URL}/health")
        if response.status_code != 200:
            print(f"Server connection failed: {response.status_code}")
    except Exception as e:
        print(f"Error connecting to server: {e}")
        print("Running in offline mode")
    
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
                    requests.post(f"{SERVER_URL}/scores", json={
                        "player_name": player_name,
                        "score": score,
                        "level": level
                    })
                except:
                    pass
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
                    </pre>
                    <li>Save the code above as <code>cloud_defender.py</code></li>
                    <li>Run the game:</li>
                    <pre>python cloud_defender.py</pre>
                </ol>
                <p>Note: Replace "http://your-ecs-service-url" with the actual URL of this service.</p>
            </div>
            <a href="/" class="button">Back to Home</a>
        </div>
    </body>
    </html>
    """

@app.route('/scores', methods=['GET'])
def get_scores():
    """Get high scores from the database"""
    try:
        logger.info("Retrieving scores")
        if use_dynamodb:
            response = table.scan()
            scores = response.get('Items', [])
        else:
            scores = memory_scores
            
        # Sort by score descending
        scores.sort(key=lambda x: x.get('score', 0), reverse=True)
        # Return top 10
        return jsonify(scores[:10]), 200
    except Exception as e:
        logger.error(f"Error retrieving scores: {str(e)}")
        # Fallback to memory scores
        memory_scores.sort(key=lambda x: x.get('score', 0), reverse=True)
        return jsonify(memory_scores[:10]), 200

@app.route('/scores', methods=['POST'])
def save_score():
    """Save a new high score"""
    try:
        score_data = request.json
        score_item = {
            'id': str(int(time.time())),  # Use timestamp as ID
            'player_name': score_data.get('player_name', 'Anonymous'),
            'score': score_data.get('score', 0),
            'level': score_data.get('level', 1),
            'difficulty': score_data.get('difficulty', 'easy'),
            'control_mode': score_data.get('control_mode', 'touch'),
            'timestamp': int(time.time())
        }
        logger.info(f"Saving score: {score_item}")
        
        # Try to save to DynamoDB if available
        if use_dynamodb:
            try:
                table.put_item(Item=score_item)
                logger.info("Score saved to DynamoDB")
            except Exception as e:
                logger.error(f"Error saving to DynamoDB: {str(e)}")
                memory_scores.append(score_item)
                logger.info("Score saved to memory")
        else:
            memory_scores.append(score_item)
            logger.info("Score saved to memory (DynamoDB not available)")
                
        return jsonify(score_item), 201
    except Exception as e:
        logger.error(f"Error processing score submission: {str(e)}")
        return jsonify({'error': 'Failed to save score'}), 500

# Game API endpoints
@app.route('/game/start', methods=['POST'])
def start_game():
    """Start a new game"""
    global game_state
    try:
        game_state = GameState()
        logger.info("New game started")
        return jsonify(game_state.to_dict()), 200
    except Exception as e:
        logger.error(f"Error starting game: {str(e)}")
        return jsonify({'error': 'Failed to start game'}), 500

@app.route('/game/status', methods=['GET'])
def game_status():
    """Get current game state"""
    global game_state
    try:
        game_state.update()
        return jsonify(game_state.to_dict()), 200
    except Exception as e:
        logger.error(f"Error getting game status: {str(e)}")
        return jsonify({'error': 'Failed to get game status'}), 500

@app.route('/game/move', methods=['POST'])
def move_player():
    """Move the player"""
    global game_state
    try:
        direction = request.json.get('direction', 'right')
        
        if direction == 'left' and game_state.player_x > 20:
            game_state.player_x -= PLAYER_SPEED
        elif direction == 'right' and game_state.player_x < SCREEN_WIDTH - 20:
            game_state.player_x += PLAYER_SPEED
            
        return jsonify({'success': True}), 200
    except Exception as e:
        logger.error(f"Error moving player: {str(e)}")
        return jsonify({'error': 'Failed to move player'}), 500

@app.route('/game/shoot', methods=['POST'])
def shoot():
    """Fire a bullet"""
    global game_state
    try:
        game_state.bullets.append([game_state.player_x, game_state.player_y])
        return jsonify({'success': True}), 200
    except Exception as e:
        logger.error(f"Error shooting: {str(e)}")
        return jsonify({'error': 'Failed to shoot'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8082)))
