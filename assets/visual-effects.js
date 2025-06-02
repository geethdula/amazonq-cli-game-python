// Enhanced visual effects for Cloud Defender game
document.addEventListener('DOMContentLoaded', function() {
    // Add parallax background layers to the game container
    const gameContainer = document.getElementById('game-container');
    if (!gameContainer) return;
    
    // Create parallax background layers
    const layers = [
        { className: 'parallax-bg stars-small', zIndex: 1 },
        { className: 'parallax-bg stars-medium', zIndex: 2 },
        { className: 'parallax-bg stars-large', zIndex: 3 },
        { className: 'parallax-bg nebula', zIndex: 4 }
    ];
    
    // Add layers to game container
    layers.forEach(layer => {
        const div = document.createElement('div');
        div.className = layer.className;
        div.style.zIndex = layer.zIndex;
        gameContainer.appendChild(div);
    });
    
    // Override the explosion function with particle effects
    if (typeof window.createExplosion !== 'function') {
        window.originalCreateExplosion = window.createExplosion;
        
        window.createExplosion = function(x, y, size = 'medium') {
            // If the original function exists, call it as a fallback
            if (window.originalCreateExplosion) {
                window.originalCreateExplosion(x, y);
            }
            
            const particleCount = size === 'large' ? 20 : (size === 'medium' ? 12 : 6);
            const baseSize = size === 'large' ? 8 : (size === 'medium' ? 5 : 3);
            const duration = size === 'large' ? 800 : (size === 'medium' ? 500 : 300);
            
            for (let i = 0; i < particleCount; i++) {
                const particle = document.createElement('div');
                particle.className = 'explosion-particle';
                
                // Random size for each particle
                const particleSize = baseSize + Math.random() * baseSize;
                
                // Random color - orange, yellow, red
                const colors = ['#ff4500', '#ff8c00', '#ffd700', '#ff6347'];
                const color = colors[Math.floor(Math.random() * colors.length)];
                
                particle.style.width = particleSize + 'px';
                particle.style.height = particleSize + 'px';
                particle.style.backgroundColor = color;
                particle.style.boxShadow = `0 0 ${particleSize}px ${color}`;
                
                // Position at explosion center
                particle.style.left = (x - particleSize/2) + 'px';
                particle.style.top = (y - particleSize/2) + 'px';
                
                // Random direction
                const angle = Math.random() * Math.PI * 2;
                const speed = 1 + Math.random() * 3;
                const vx = Math.cos(angle) * speed;
                const vy = Math.sin(angle) * speed;
                
                gameContainer.appendChild(particle);
                
                // Animate particle
                let opacity = 1;
                let size = particleSize;
                let posX = x - particleSize/2;
                let posY = y - particleSize/2;
                
                const animateParticle = () => {
                    if (opacity <= 0) {
                        if (particle.parentNode) {
                            particle.parentNode.removeChild(particle);
                        }
                        return;
                    }
                    
                    opacity -= 0.02;
                    size += 0.1;
                    posX += vx;
                    posY += vy;
                    
                    particle.style.opacity = opacity;
                    particle.style.width = size + 'px';
                    particle.style.height = size + 'px';
                    particle.style.left = posX + 'px';
                    particle.style.top = posY + 'px';
                    
                    requestAnimationFrame(animateParticle);
                };
                
                requestAnimationFrame(animateParticle);
            }
        };
    }
    
    // Enhanced level up function
    if (typeof window.showLevelUpMessage === 'function') {
        window.originalShowLevelUpMessage = window.showLevelUpMessage;
        
        window.showLevelUpMessage = function(message) {
            // If it's a level up message
            if (message.includes('LEVEL')) {
                const level = parseInt(message.replace(/\D/g, '')) || 1;
                
                // Create level up effect container
                const levelEffect = document.createElement('div');
                levelEffect.className = 'level-transition';
                gameContainer.appendChild(levelEffect);
                
                // Add level text
                const levelText = document.createElement('div');
                levelText.className = 'level-text';
                levelText.textContent = 'LEVEL ' + level;
                levelEffect.appendChild(levelText);
                
                // Add subtitle
                const subtitle = document.createElement('div');
                subtitle.className = 'level-subtitle';
                
                // Different messages for different levels
                const messages = [
                    "Threat Level Increasing",
                    "Defend The Cloud!",
                    "Security Breach Imminent",
                    "Critical Systems Alert",
                    "Maximum Defense Required"
                ];
                subtitle.textContent = messages[Math.min(level - 1, messages.length - 1)];
                levelEffect.appendChild(subtitle);
                
                // Remove after animation completes
                setTimeout(() => {
                    levelEffect.classList.add('fade-out');
                    setTimeout(() => {
                        if (levelEffect.parentNode) {
                            levelEffect.parentNode.removeChild(levelEffect);
                        }
                    }, 1000);
                }, 2000);
            } else {
                // For other messages, use the original function
                if (window.originalShowLevelUpMessage) {
                    window.originalShowLevelUpMessage(message);
                }
            }
        };
    }
    
    console.log('Visual effects enhancement loaded');
});
