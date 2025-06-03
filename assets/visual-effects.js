/**
 * Visual effects for Cloud Defender game
 * This script adds additional visual effects to enhance the game experience
 */

// Wait for the game to initialize
document.addEventListener('DOMContentLoaded', function() {
    // Create starfield background
    createStarfield();
    
    // Add particle effects for explosions
    enhanceExplosions();
    
    // Add shield pulse effect
    enhanceShieldEffect();
});

/**
 * Creates a dynamic starfield background
 */
function createStarfield() {
    // Only create if game container exists
    const gameContainer = document.getElementById('game-container');
    if (!gameContainer) return;
    
    // Create starfield container
    const starfield = document.createElement('div');
    starfield.className = 'starfield';
    starfield.style.position = 'absolute';
    starfield.style.top = '0';
    starfield.style.left = '0';
    starfield.style.width = '100%';
    starfield.style.height = '100%';
    starfield.style.zIndex = '1';
    starfield.style.overflow = 'hidden';
    gameContainer.prepend(starfield);
    
    // Create stars
    const numStars = 50;
    for (let i = 0; i < numStars; i++) {
        createStar(starfield);
    }
    
    // Animate stars
    animateStars(starfield);
}

/**
 * Creates a single star element
 */
function createStar(container) {
    const star = document.createElement('div');
    star.className = 'star';
    
    // Random position
    const x = Math.random() * 100;
    const y = Math.random() * 100;
    
    // Random size
    const size = Math.random() * 2 + 1;
    
    // Random brightness
    const opacity = Math.random() * 0.5 + 0.3;
    
    // Set star styles
    star.style.position = 'absolute';
    star.style.left = x + '%';
    star.style.top = y + '%';
    star.style.width = size + 'px';
    star.style.height = size + 'px';
    star.style.borderRadius = '50%';
    star.style.backgroundColor = '#ffffff';
    star.style.opacity = opacity;
    
    // Add to container
    container.appendChild(star);
    
    // Store initial position for animation
    star.dataset.x = x;
    star.dataset.y = y;
    star.dataset.speed = Math.random() * 0.05 + 0.01;
}

/**
 * Animates the stars to create parallax scrolling effect
 */
function animateStars(container) {
    // Only run if game is active
    if (!gameActive) {
        requestAnimationFrame(() => animateStars(container));
        return;
    }
    
    const stars = container.querySelectorAll('.star');
    
    stars.forEach(star => {
        // Move star down
        const y = parseFloat(star.dataset.y) + parseFloat(star.dataset.speed);
        
        // Reset if star goes off screen
        if (y > 100) {
            star.dataset.y = 0;
            star.dataset.x = Math.random() * 100;
        } else {
            star.dataset.y = y;
        }
        
        // Update position
        star.style.top = y + '%';
    });
    
    // Continue animation
    requestAnimationFrame(() => animateStars(container));
}

/**
 * Enhances explosion effects with additional particles
 */
function enhanceExplosions() {
    // Override the createExplosion function to add more particles
    const originalCreateExplosion = window.createExplosion;
    
    if (originalCreateExplosion) {
        window.createExplosion = function(x, y) {
            // Call original function
            originalCreateExplosion(x, y);
            
            // Add additional particle effects
            createExplosionParticles(x, y);
        };
    }
}

/**
 * Creates particle effects for explosions
 */
function createExplosionParticles(x, y) {
    const gameContainer = document.getElementById('game-container');
    if (!gameContainer) return;
    
    // Number of particles
    const numParticles = 8;
    
    // Create particles
    for (let i = 0; i < numParticles; i++) {
        const particle = document.createElement('div');
        particle.className = 'explosion-particle';
        
        // Set particle styles
        particle.style.position = 'absolute';
        particle.style.left = x + 'px';
        particle.style.top = y + 'px';
        particle.style.width = '3px';
        particle.style.height = '3px';
        particle.style.borderRadius = '50%';
        particle.style.backgroundColor = i % 2 === 0 ? '#ffcc00' : '#ff6600';
        
        // Add to container
        gameContainer.appendChild(particle);
        
        // Random direction
        const angle = Math.random() * Math.PI * 2;
        const speed = Math.random() * 3 + 2;
        const dx = Math.cos(angle) * speed;
        const dy = Math.sin(angle) * speed;
        
        // Animate particle
        let opacity = 1;
        let posX = x;
        let posY = y;
        
        const animateParticle = () => {
            if (opacity <= 0) {
                if (particle.parentNode) {
                    particle.parentNode.removeChild(particle);
                }
                return;
            }
            
            // Update position
            posX += dx;
            posY += dy;
            opacity -= 0.05;
            
            particle.style.left = posX + 'px';
            particle.style.top = posY + 'px';
            particle.style.opacity = opacity;
            
            requestAnimationFrame(animateParticle);
        };
        
        requestAnimationFrame(animateParticle);
    }
}

/**
 * Enhances shield effect with additional visual elements
 */
function enhanceShieldEffect() {
    // Check for shield effect updates
    setInterval(() => {
        const shieldElement = document.querySelector('.shield-effect');
        if (shieldElement && hasShield) {
            // Add shield particles
            createShieldParticle(shieldElement);
        }
    }, 200);
}

/**
 * Creates a particle effect for the shield
 */
function createShieldParticle(shieldElement) {
    const gameContainer = document.getElementById('game-container');
    if (!gameContainer) return;
    
    // Get shield position
    const rect = shieldElement.getBoundingClientRect();
    const containerRect = gameContainer.getBoundingClientRect();
    
    const centerX = rect.left - containerRect.left + rect.width / 2;
    const centerY = rect.top - containerRect.top + rect.height / 2;
    
    // Create particle
    const particle = document.createElement('div');
    particle.className = 'shield-particle';
    
    // Random position on shield perimeter
    const angle = Math.random() * Math.PI * 2;
    const radius = 30;
    const x = centerX + Math.cos(angle) * radius;
    const y = centerY + Math.sin(angle) * radius;
    
    // Set particle styles
    particle.style.position = 'absolute';
    particle.style.left = x + 'px';
    particle.style.top = y + 'px';
    particle.style.width = '4px';
    particle.style.height = '4px';
    particle.style.borderRadius = '50%';
    particle.style.backgroundColor = '#FFC107';
    particle.style.opacity = '0.7';
    
    // Add to container
    gameContainer.appendChild(particle);
    
    // Animate particle
    let opacity = 0.7;
    
    const animateParticle = () => {
        if (opacity <= 0) {
            if (particle.parentNode) {
                particle.parentNode.removeChild(particle);
            }
            return;
        }
        
        opacity -= 0.05;
        particle.style.opacity = opacity;
        
        requestAnimationFrame(animateParticle);
    };
    
    requestAnimationFrame(animateParticle);
}
