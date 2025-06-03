"""
Player ship sprite for Cloud Defender game.
This file contains the ASCII representation of the player's spaceship.
"""

PLAYER_SHIP = """
    /\\
   /  \\
  /    \\
 /      \\
/________\\
|  AWS   |
|________|
   |  |
   |__|
"""

PLAYER_SHIP_SMALL = """
  /\\
 /--\\
|AWS|
 |__|
"""

# Color: Blue with white text
PLAYER_COLOR = (30, 144, 255)  # Dodger Blue
PLAYER_TEXT_COLOR = (255, 255, 255)  # White

# Ship dimensions (for collision detection)
PLAYER_WIDTH = 50
PLAYER_HEIGHT = 60

# Ship properties
PLAYER_SPEED = 5
PLAYER_HEALTH = 100
PLAYER_FIRE_RATE = 0.25  # seconds between shots
