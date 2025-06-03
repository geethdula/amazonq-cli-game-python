/**
 * Sound effects manager for Cloud Defender game
 * This script handles loading and playing sound effects
 */

// Sound effect URLs - these would be actual audio files in production
const SOUND_URLS = {
    // Player sounds
    playerShoot: 'assets/sounds/player_shoot.mp3',
    playerHit: 'assets/sounds/player_hit.mp3',
    playerExplode: 'assets/sounds/player_explode.mp3',
    
    // Enemy sounds
    enemyHit: 'assets/sounds/enemy_hit.mp3',
    enemyExplode: 'assets/sounds/enemy_explode.mp3',
    enemyShoot: 'assets/sounds/enemy_shoot.mp3',
    
    // Boss sounds
    bossAppear: 'assets/sounds/boss_appear.mp3',
    bossHit: 'assets/sounds/boss_hit.mp3',
    bossExplode: 'assets/sounds/boss_explode.mp3',
    
    // Powerup sounds
    powerupAppear: 'assets/sounds/powerup_appear.mp3',
    powerupCollect: 'assets/sounds/powerup_collect.mp3',
    
    // UI sounds
    buttonClick: 'assets/sounds/button_click.mp3',
    levelUp: 'assets/sounds/level_up.mp3',
    gameOver: 'assets/sounds/game_over.mp3',
    
    // Background music
    bgMusic: 'assets/sounds/background_music.mp3'
};

// Sound effect volume levels
const VOLUME_LEVELS = {
    master: 0.7,
    sfx: 0.8,
    music: 0.5
};

// Audio objects cache
const audioCache = {};

// Mute state
let muted = false;

/**
 * Initialize the sound system
 */
function initSounds() {
    // Create audio context if Web Audio API is available
    try {
        window.AudioContext = window.AudioContext || window.webkitAudioContext;
        window.audioContext = new AudioContext();
        console.log('Audio context created successfully');
    } catch (e) {
        console.warn('Web Audio API not supported in this browser');
    }
    
    // Add mute button to game UI
    addMuteButton();
    
    // Preload common sounds
    preloadSounds(['playerShoot', 'enemyHit', 'powerupCollect', 'buttonClick']);
}

/**
 * Preload sound effects to reduce latency
 */
function preloadSounds(soundKeys) {
    if (!window.audioContext) return;
    
    soundKeys.forEach(key => {
        if (SOUND_URLS[key]) {
            loadSound(key);
        }
    });
}

/**
 * Load a sound file
 */
function loadSound(soundKey) {
    if (!window.audioContext || muted) return Promise.resolve(null);
    
    // Return from cache if already loaded
    if (audioCache[soundKey]) {
        return Promise.resolve(audioCache[soundKey]);
    }
    
    return fetch(SOUND_URLS[soundKey])
        .then(response => response.arrayBuffer())
        .then(arrayBuffer => window.audioContext.decodeAudioData(arrayBuffer))
        .then(audioBuffer => {
            audioCache[soundKey] = audioBuffer;
            return audioBuffer;
        })
        .catch(error => {
            console.warn(`Error loading sound ${soundKey}:`, error);
            return null;
        });
}

/**
 * Play a sound effect
 */
function playSound(soundKey, volume = 1.0) {
    if (!window.audioContext || muted) return;
    
    // Calculate actual volume based on master and sfx levels
    const actualVolume = volume * VOLUME_LEVELS.master * VOLUME_LEVELS.sfx;
    
    // If sound is not in cache, load it first
    if (!audioCache[soundKey]) {
        loadSound(soundKey).then(buffer => {
            if (buffer) playBuffer(buffer, actualVolume);
        });
        return;
    }
    
    // Play from cache
    playBuffer(audioCache[soundKey], actualVolume);
}

/**
 * Play an audio buffer
 */
function playBuffer(buffer, volume) {
    if (!window.audioContext || !buffer) return;
    
    const source = window.audioContext.createBufferSource();
    source.buffer = buffer;
    
    // Create gain node for volume control
    const gainNode = window.audioContext.createGain();
    gainNode.gain.value = volume;
    
    // Connect nodes
    source.connect(gainNode);
    gainNode.connect(window.audioContext.destination);
    
    // Play sound
    source.start(0);
}

/**
 * Play background music
 */
function playBackgroundMusic() {
    if (!window.audioContext || muted) return;
    
    // Load music if not cached
    if (!audioCache.bgMusic) {
        loadSound('bgMusic').then(buffer => {
            if (buffer) {
                playLoopingMusic(buffer);
            }
        });
        return;
    }
    
    // Play from cache
    playLoopingMusic(audioCache.bgMusic);
}

/**
 * Play looping background music
 */
function playLoopingMusic(buffer) {
    if (!window.audioContext || !buffer) return;
    
    const source = window.audioContext.createBufferSource();
    source.buffer = buffer;
    source.loop = true;
    
    // Create gain node for volume control
    const gainNode = window.audioContext.createGain();
    gainNode.gain.value = VOLUME_LEVELS.master * VOLUME_LEVELS.music;
    
    // Connect nodes
    source.connect(gainNode);
    gainNode.connect(window.audioContext.destination);
    
    // Store reference for stopping later
    window.bgMusicSource = source;
    window.bgMusicGain = gainNode;
    
    // Play music
    source.start(0);
}

/**
 * Stop background music
 */
function stopBackgroundMusic() {
    if (window.bgMusicSource) {
        window.bgMusicSource.stop();
        window.bgMusicSource = null;
    }
}

/**
 * Toggle mute state
 */
function toggleMute() {
    muted = !muted;
    
    // Update mute button
    const muteButton = document.getElementById('mute-button');
    if (muteButton) {
        muteButton.textContent = muted ? '🔇' : '🔊';
    }
    
    // Stop background music if muted
    if (muted && window.bgMusicSource) {
        stopBackgroundMusic();
    } else if (!muted && !window.bgMusicSource) {
        playBackgroundMusic();
    }
}

/**
 * Add mute button to game UI
 */
function addMuteButton() {
    const gameContainer = document.getElementById('game-container');
    if (!gameContainer) return;
    
    const muteButton = document.createElement('button');
    muteButton.id = 'mute-button';
    muteButton.textContent = '🔊';
    muteButton.style.position = 'absolute';
    muteButton.style.top = '10px';
    muteButton.style.right = '10px';
    muteButton.style.zIndex = '100';
    muteButton.style.background = 'rgba(0,0,0,0.5)';
    muteButton.style.color = 'white';
    muteButton.style.border = '1px solid #ff9900';
    muteButton.style.borderRadius = '5px';
    muteButton.style.padding = '5px 10px';
    muteButton.style.cursor = 'pointer';
    
    muteButton.addEventListener('click', toggleMute);
    
    gameContainer.appendChild(muteButton);
}

// Initialize sounds when document is loaded
document.addEventListener('DOMContentLoaded', initSounds);

// Export sound functions for use in game
window.gameSounds = {
    play: playSound,
    playMusic: playBackgroundMusic,
    stopMusic: stopBackgroundMusic,
    toggleMute: toggleMute
};
