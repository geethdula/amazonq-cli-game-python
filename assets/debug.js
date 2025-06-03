/**
 * Debug utilities for Cloud Defender game
 * This script adds debugging capabilities that can be enabled during development
 */

// Debug mode flag - set to true to enable debugging features
const DEBUG_MODE = false;

// Initialize debug features if debug mode is enabled
if (DEBUG_MODE) {
    console.log("Debug mode enabled");
    
    // Create debug overlay
    const debugOverlay = document.getElementById('debug-overlay');
    if (debugOverlay) {
        debugOverlay.style.display = 'block';
    }
    
    // Add hitbox visualization
    function createHitboxVisualizers() {
        // For bullets
        for (let bullet of bullets) {
            const hitbox = document.createElement('div');
            hitbox.className = 'hitbox-debug bullet-hitbox';
            hitbox.style.width = '16px';
            hitbox.style.height = '16px';
            hitbox.style.left = (bullet.x - 8) + 'px';
            hitbox.style.top = (bullet.y - 8) + 'px';
            gameContainer.appendChild(hitbox);
            
            // Store reference to hitbox
            bullet.hitbox = hitbox;
        }
        
        // For enemies
        for (let enemy of enemies) {
            const hitbox = document.createElement('div');
            hitbox.className = 'hitbox-debug enemy-hitbox';
            hitbox.style.width = '40px';
            hitbox.style.height = '40px';
            hitbox.style.left = (enemy.x - 20) + 'px';
            hitbox.style.top = (enemy.y - 20) + 'px';
            gameContainer.appendChild(hitbox);
            
            // Store reference to hitbox
            enemy.hitbox = hitbox;
        }
    }
    
    // Update hitbox positions
    function updateHitboxes() {
        // For bullets
        for (let bullet of bullets) {
            if (bullet.hitbox) {
                bullet.hitbox.style.left = (bullet.x - 8) + 'px';
                bullet.hitbox.style.top = (bullet.y - 8) + 'px';
            }
        }
        
        // For enemies
        for (let enemy of enemies) {
            if (enemy.hitbox) {
                enemy.hitbox.style.left = (enemy.x - 20) + 'px';
                enemy.hitbox.style.top = (enemy.y - 20) + 'px';
            }
        }
    }
    
    // Add keyboard shortcuts for debugging
    document.addEventListener('keydown', function(e) {
        // Press 'D' to toggle debug overlay
        if (e.key === 'd' || e.key === 'D') {
            debugOverlay.style.display = debugOverlay.style.display === 'none' ? 'block' : 'none';
        }
        
        // Press 'H' to toggle hitbox visualization
        if (e.key === 'h' || e.key === 'H') {
            const hitboxes = document.querySelectorAll('.hitbox-debug');
            hitboxes.forEach(hitbox => {
                hitbox.style.display = hitbox.style.display === 'none' ? 'block' : 'none';
            });
        }
        
        // Press 'K' to kill all enemies (for testing)
        if (e.key === 'k' || e.key === 'K') {
            enemies.forEach(enemy => {
                if (enemy.element && enemy.element.parentNode) {
                    enemy.element.remove();
                }
            });
            enemies = [];
        }
        
        // Press 'B' to spawn boss (for testing)
        if (e.key === 'b' || e.key === 'B') {
            createBoss();
        }
        
        // Press 'P' to spawn powerup (for testing)
        if (e.key === 'p' || e.key === 'P') {
            const powerupType = POWERUP_TYPES[Math.floor(Math.random() * POWERUP_TYPES.length)];
            createPowerup(Math.random() * CONTAINER_WIDTH, Math.random() * CONTAINER_HEIGHT / 2);
        }
        
        // Press 'L' to level up (for testing)
        if (e.key === 'l' || e.key === 'L') {
            level++;
            levelDisplay.textContent = 'Level: ' + level;
            showLevelUpMessage("LEVEL " + level);
        }
    });
    
    // Override game loop to include debug features
    const originalGameLoop = gameLoop;
    gameLoop = function() {
        originalGameLoop();
        
        if (gameActive) {
            // Update debug info
            debugOverlay.textContent = `FPS: ${Math.round(1000 / (Date.now() - (lastFrameTime || Date.now())))} | Enemies: ${enemies.length} | Bullets: ${bullets.length}`;
            lastFrameTime = Date.now();
            
            // Update hitboxes
            updateHitboxes();
        }
    };
    
    // Track frame time for FPS calculation
    let lastFrameTime = null;
    
    // Show hitboxes on startup
    setTimeout(function() {
        document.querySelectorAll('.hitbox-debug').forEach(hitbox => {
            hitbox.style.display = 'block';
        });
    }, 1000);
}
