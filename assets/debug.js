// Debug functionality for Cloud Defender game
document.addEventListener('DOMContentLoaded', function() {
    // Add debug mode toggle button
    const gameContainer = document.getElementById('game-container');
    if (!gameContainer) return;
    
    const debugModeBtn = document.createElement('button');
    debugModeBtn.textContent = 'Toggle Debug Mode';
    debugModeBtn.className = 'button';
    debugModeBtn.style.position = 'absolute';
    debugModeBtn.style.top = '10px';
    debugModeBtn.style.right = '10px';
    debugModeBtn.style.zIndex = '1000';
    debugModeBtn.style.fontSize = '12px';
    debugModeBtn.style.padding = '5px';
    gameContainer.appendChild(debugModeBtn);
    
    // Add debug overlay if it doesn't exist
    let debugOverlay = document.getElementById('debug-overlay');
    if (!debugOverlay) {
        debugOverlay = document.createElement('div');
        debugOverlay.id = 'debug-overlay';
        debugOverlay.className = 'debug-overlay';
        gameContainer.appendChild(debugOverlay);
    }
    
    // Debug mode state
    window.debugMode = false;
    window.lastFrameTime = Date.now();
    
    // Toggle debug mode
    debugModeBtn.addEventListener('click', function() {
        window.debugMode = !window.debugMode;
        debugOverlay.style.display = window.debugMode ? 'block' : 'none';
        
        // Toggle hitbox visualization
        const hitboxes = document.querySelectorAll('.hitbox-debug');
        hitboxes.forEach(function(box) {
            box.style.display = window.debugMode ? 'block' : 'none';
        });
        
        // Update button text
        debugModeBtn.textContent = window.debugMode ? 'Hide Debug Mode' : 'Show Debug Mode';
        
        // Add CSS for hitbox visualization if needed
        if (window.debugMode && !document.getElementById('debug-styles')) {
            const style = document.createElement('style');
            style.id = 'debug-styles';
            style.textContent = `
                .hitbox-debug {
                    position: absolute;
                    border-radius: 50%;
                    pointer-events: none;
                    z-index: 100;
                }
                .bullet-hitbox {
                    border: 1px solid yellow;
                    opacity: 0.5;
                }
                .enemy-hitbox {
                    border: 1px solid red;
                    opacity: 0.5;
                }
                .debug-overlay {
                    background-color: rgba(0,0,0,0.7) !important;
                    padding: 10px !important;
                    font-size: 14px !important;
                    z-index: 1000 !important;
                }
            `;
            document.head.appendChild(style);
        }
    });
    
    // Patch the game's collision detection to use more generous hit detection
    patchGameCollisionDetection();
});

// Function to draw hitboxes for debugging (to be called in gameLoop)
function drawDebugHitboxes(gameContainer, bullets, enemies) {
    if (!window.debugMode) return;
    
    // Clear any existing hitbox visualizations
    const existingHitboxes = document.querySelectorAll('.hitbox-debug');
    existingHitboxes.forEach(box => box.remove());
    
    // Draw bullet hitboxes
    bullets.forEach(bullet => {
        const hitbox = document.createElement('div');
        hitbox.className = 'hitbox-debug bullet-hitbox';
        hitbox.style.left = (bullet.x - 15) + 'px';
        hitbox.style.top = (bullet.y - 15) + 'px';
        hitbox.style.width = '30px';
        hitbox.style.height = '30px';
        gameContainer.appendChild(hitbox);
    });
    
    // Draw enemy hitboxes
    enemies.forEach(enemy => {
        const hitbox = document.createElement('div');
        hitbox.className = 'hitbox-debug enemy-hitbox';
        hitbox.style.left = (enemy.x - 25) + 'px';
        hitbox.style.top = (enemy.y - 25) + 'px';
        hitbox.style.width = '50px';
        hitbox.style.height = '50px';
        gameContainer.appendChild(hitbox);
    });
}

// Function to update debug overlay
function updateDebugOverlay(debugOverlay, gameStats) {
    if (!window.debugMode || !debugOverlay) return;
    
    const now = Date.now();
    const fps = Math.round(1000 / (now - window.lastFrameTime));
    window.lastFrameTime = now;
    
    debugOverlay.innerHTML = `
        Bullets: ${gameStats.bullets || 0}<br>
        Enemies: ${gameStats.enemies || 0}<br>
        Player: (${gameStats.playerX || 0}, ${gameStats.playerY || 0})<br>
        FPS: ${fps || 0}<br>
        Hit radius: 25px
    `;
}

// Function to patch the game's collision detection
function patchGameCollisionDetection() {
    // This function will be called after the page loads
    // It will wait for the game to initialize and then patch the checkCollisions function
    
    // Check every 100ms if the game has initialized
    const checkInterval = setInterval(function() {
        if (typeof checkCollisions === 'function') {
            // Game has initialized, patch the function
            clearInterval(checkInterval);
            
            // Store the original function
            const originalCheckCollisions = checkCollisions;
            
            // Replace with our patched version
            window.checkCollisions = function() {
                // Call the original function first
                originalCheckCollisions.apply(this, arguments);
                
                // Update debug info if debug mode is on
                if (window.debugMode) {
                    const gameContainer = document.getElementById('game-container');
                    const debugOverlay = document.getElementById('debug-overlay');
                    
                    if (gameContainer && typeof bullets !== 'undefined' && typeof enemies !== 'undefined') {
                        // Draw hitboxes
                        drawDebugHitboxes(gameContainer, bullets, enemies);
                        
                        // Update debug overlay
                        if (debugOverlay) {
                            updateDebugOverlay(debugOverlay, {
                                bullets: bullets.length,
                                enemies: enemies.length,
                                playerX: playerX,
                                playerY: CONTAINER_HEIGHT - 40
                            });
                        }
                    }
                }
            };
            
            console.log('Game collision detection patched successfully');
        }
    }, 100);
    
    // Stop checking after 10 seconds to avoid infinite loop
    setTimeout(function() {
        clearInterval(checkInterval);
    }, 10000);
}
