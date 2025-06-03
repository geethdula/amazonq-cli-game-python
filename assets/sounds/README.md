# Cloud Defender Sound Assets

This directory contains sound effects and music for the Cloud Defender game.

## Required Sound Files

The following sound files should be placed in this directory:

### Player Sounds
- `player_shoot.mp3` - Player firing weapon
- `player_hit.mp3` - Player taking damage
- `player_explode.mp3` - Player ship exploding

### Enemy Sounds
- `enemy_hit.mp3` - Enemy taking damage
- `enemy_explode.mp3` - Enemy exploding
- `enemy_shoot.mp3` - Enemy firing weapon

### Boss Sounds
- `boss_appear.mp3` - Boss arrival sound
- `boss_hit.mp3` - Boss taking damage
- `boss_explode.mp3` - Boss exploding

### Powerup Sounds
- `powerup_appear.mp3` - Powerup appearing
- `powerup_collect.mp3` - Powerup collection

### UI Sounds
- `button_click.mp3` - UI button click
- `level_up.mp3` - Level up fanfare
- `game_over.mp3` - Game over sound

### Music
- `background_music.mp3` - Game background music

## Sound File Specifications

For optimal performance and compatibility:

- Format: MP3 (44.1kHz, 128kbps recommended)
- Duration: Keep sound effects short (under 2 seconds)
- Volume: Normalize audio to prevent clipping
- Size: Keep files small (under 100KB for effects, under 2MB for music)

## Obtaining Sound Files

You can create or obtain sound files from various sources:

1. Create your own using audio editing software like Audacity
2. Use royalty-free sound libraries:
   - [Freesound](https://freesound.org/)
   - [OpenGameArt](https://opengameart.org/)
   - [Soundsnap](https://www.soundsnap.com/)
3. Use sound generation tools:
   - [BFXR](https://www.bfxr.net/) - Great for retro game sounds
   - [ChipTone](https://sfbgames.itch.io/chiptone) - Chiptune sound effects

## Integration

The sound system is configured to automatically load and play these files when needed.
See the `sounds.js` and `game-audio.js` files for implementation details.

## License Information

When using third-party sound files, ensure you have the appropriate licenses and provide attribution as required.
