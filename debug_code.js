            // Enable debug overlay to help diagnose hit detection issues
            const debugOverlay = document.getElementById('debug-overlay');
            debugOverlay.style.display = 'block';
            
            // Function to draw hitboxes for debugging (call this in gameLoop)
            function drawHitboxes() {
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
            
            // Add CSS for hitbox visualization
            const style = document.createElement('style');
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
                    display: block !important;
                    background-color: rgba(0,0,0,0.7);
                    padding: 10px;
                    font-size: 14px;
                    z-index: 1000;
                }
            `;
            document.head.appendChild(style);
