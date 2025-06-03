/**
 * Game audio integration for Cloud Defender
 * This script connects game events to sound effects
 */

// Wait for the game to initialize
document.addEventListener('DOMContentLoaded', function() {
    // Wait for sounds.js to initialize
    setTimeout(initGameAudio, 500);
});

/**
 * Initialize game audio by connecting game events to sound effects
 */
function initGameAudio() {
    // Check if sound system is available
    if (!window.gameSounds) {
        console.warn('Sound system not available');
        return;
    }
    
    // Override game functions to add sound effects
    addSoundToShooting();
    addSoundToEnemies();
    addSoundToPowerups();
    addSoundToBosses();
    addSoundToGameEvents();
    addSoundToButtons();
    
    // Start background music when game starts
    const startGameBtn = document.getElementById('start-game-btn');
    if (startGameBtn) {
        const originalStartGame = startGameBtn.onclick;
        startGameBtn.onclick = function(e) {
            if (originalStartGame) originalStartGame.call(this, e);
            window.gameSounds.playMusic();
        };
    }
}

/**
 * Add sound effects to player shooting
 */
function addSoundToShooting() {
    // Override shootBullet function
    if (window.shootBullet) {
        const originalShootBullet = window.shootBullet;
        window.shootBullet = function() {
            originalShootBullet.apply(this, arguments);
            window.gameSounds.play('playerShoot', 0.4);
        };
    }
}

/**
 * Add sound effects to enemy interactions
 */
function addSoundToEnemies() {
    // Override checkCollisions function to add hit sounds
    if (window.checkCollisions) {
        const originalCheckCollisions = window.checkCollisions;
        window.checkCollisions = function() {
            // Store enemy and bullet counts before collision check
            const enemyCountBefore = enemies ? enemies.length : 0;
            const bulletCountBefore = bullets ? bullets.length : 0;
            const playerHealthBefore = playerHealth;
            
            // Call original function
            originalCheckCollisions.apply(this, arguments);
            
            // Check if enemies were destroyed
            if (enemies && enemies.length < enemyCountBefore) {
                window.gameSounds.play('enemyExplode', 0.5);
            }
            
            // Check if bullets hit something
            if (bullets && bullets.length < bulletCountBefore) {
                window.gameSounds.play('enemyHit', 0.3);
            }
            
            // Check if player was hit
            if (playerHealth < playerHealthBefore) {
                window.gameSounds.play('playerHit', 0.6);
            }
        };
    }
    
    // Add sound to enemy shooting
    if (window.enemyShoot) {
        const originalEnemyShoot = window.enemyShoot;
        window.enemyShoot = function(enemy) {
            originalEnemyShoot.apply(this, arguments);
            window.gameSounds.play('enemyShoot', 0.2);
        };
    }
}

/**
 * Add sound effects to powerup interactions
 */
function addSoundToPowerups() {
    // Add sound when powerup is activated
    if (window.activatePowerup) {
        const originalActivatePowerup = window.activatePowerup;
        window.activatePowerup = function(type) {
            originalActivatePowerup.apply(this, arguments);
            window.gameSounds.play('powerupCollect', 0.7);
        };
    }
    
    // Add sound when powerup is created
    if (window.createPowerup) {
        const originalCreatePowerup = window.createPowerup;
        window.createPowerup = function(x, y) {
            originalCreatePowerup.apply(this, arguments);
            window.gameSounds.play('powerupAppear', 0.4);
        };
    }
}

/**
 * Add sound effects to boss interactions
 */
function addSoundToBosses() {
    // Add sound when boss appears
    if (window.createBoss) {
        const originalCreateBoss = window.createBoss;
        window.createBoss = function() {
            originalCreateBoss.apply(this, arguments);
            window.gameSounds.play('bossAppear', 0.8);
        };
    }
    
    // Add sound when boss shoots
    if (window.bossShoot) {
        const originalBossShoot = window.bossShoot;
        window.bossShoot = function() {
            originalBossShoot.apply(this, arguments);
            window.gameSounds.play('enemyShoot', 0.5);
        };
    }
}

/**
 * Add sound effects to game events
 */
function addSoundToGameEvents() {
    // Add sound when level up
    if (window.showLevelUpMessage) {
        const originalShowLevelUpMessage = window.showLevelUpMessage;
        window.showLevelUpMessage = function(message) {
            originalShowLevelUpMessage.apply(this, arguments);
            if (message.includes("LEVEL")) {
                window.gameSounds.play('levelUp', 0.7);
            }
        };
    }
    
    // Add sound when game over
    if (window.endGame) {
        const originalEndGame = window.endGame;
        window.endGame = function() {
            originalEndGame.apply(this, arguments);
            window.gameSounds.play('gameOver', 0.8);
            window.gameSounds.stopMusic();
        };
    }
}

/**
 * Add sound effects to button clicks
 */
function addSoundToButtons() {
    // Add click sound to all buttons
    const buttons = document.querySelectorAll('.button, .control-btn, .difficulty-btn, .control-mode-btn');
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            window.gameSounds.play('buttonClick', 0.5);
        });
    });
}
