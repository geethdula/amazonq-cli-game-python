/**
 * Player shoot sound effect - Data URI format
 * This can be used directly without requiring an external audio file
 */

// Base64-encoded WAV data for player shooting sound
const PLAYER_SHOOT_SOUND = "data:audio/wav;base64,UklGRqQDAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YYADAACAgICAgICAgICAgICAgICAgICAgICAgICAf3hxeH+AfXZ1gIqPjIJ6fYONlI+Hf4mVoJqSiCwA3e705PH0AgAFAODh6/z+/OLU2uv19Pvo3+Xw9/Xr6e/4/fz7/gD/+vb19vf8/v8AAPz6+vv8/f7/AAD/AAABAgMEBAUGBwkKCgsMDQ0ODg8QEBEREhISExMTFBQUFRUVFRYWFhYXFxcXGBgYGBkZGRkaGhoaGxsbGxwcHBwdHR0dHh4eHh8fHx8gICAgISEhISIiIiIjIyMjJCQkJCUlJSUmJiYmJycnJygoKCgpKSkpKioqKisrKyssLCwsLS0tLS4uLi4vLy8vMDAwMDExMTEyMjIyMzMzMzQ0NDQ1NTU1NjY2Njc3Nzc4ODg4OTk5OTo6Ojo7Ozs7PDw8PD09PT0+Pj4+Pz8/P0BAQEBBQUFBQkJCQkNDQ0NERERERUVFRUZGRkZHR0dHSEhISElJSUlKSkpKS0tLS0xMTExNTU1NTk5OTk9PT09QUFBQUVFRUVJSUlJTU1NTVFRUVFVVVVVWVlZWV1dXV1hYWFhZWVlZWlpaWltbW1tcXFxcXV1dXV5eXl5fX19fYGBgYGFhYWFiYmJiY2NjY2RkZGRlZWVlZmZmZmdnZ2doaGhoaWlpaWpqampra2trbGxsbG1tbW1ubm5ub29vb3BwcHBxcXFxcnJycnNzc3N0dHR0dXV1dXZ2dnZ3d3d3eHh4eHl5eXl6enp6e3t7e3x8fHx9fX19fn5+fn9/f3+AgICAgYGBgYKCgoKDg4ODhISEhIWFhYWGhoaGh4eHh4iIiIiJiYmJioqKiouLi4uMjIyMjY2NjY6Ojo6Pj4+PkJCQkJGRkZGSkpKSk5OTk5SUlJSVlZWVlpaWlpeXl5eYmJiYmZmZmZqampqbm5ubmZaSj4uKjpKVlZOQjYuKjZCUlpaTjouJiIqNkJOWlpWTkY6MioiHhYSCgHt1cGtnZGFeW1hVUlBOTEpJSEc=";

// Function to play the sound
function playPlayerShootSound(volume = 0.5) {
  try {
    // Create audio element
    const audio = new Audio(PLAYER_SHOOT_SOUND);
    audio.volume = volume;
    
    // Play the sound
    audio.play().catch(e => console.warn("Error playing sound:", e));
    
    // Clean up after playing
    audio.onended = () => {
      audio.src = "";
    };
  } catch (e) {
    console.warn("Error creating audio:", e);
  }
}

// Export for use in other scripts
if (typeof window !== 'undefined') {
  window.playPlayerShootSound = playPlayerShootSound;
}
