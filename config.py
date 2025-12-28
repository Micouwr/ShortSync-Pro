# config.py
"""
Configuration module for YouTube Shorts Automation Bot.
Centralizes all settings and environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Main configuration class"""
    
    # Directory paths
    BASE_DIR = Path(__file__).parent.absolute()
    ASSETS_DIR = BASE_DIR / "assets"
    OUTPUT_DIR = BASE_DIR / "output"
    AUDIO_DIR = OUTPUT_DIR / "audio"
    VIDEO_DIR = OUTPUT_DIR / "video"
    REVIEW_DIR = OUTPUT_DIR / "review"
    
    # Create directories if they don't exist
    for directory in [ASSETS_DIR, OUTPUT_DIR, AUDIO_DIR, VIDEO_DIR, REVIEW_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # YouTube API settings
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
    YOUTUBE_CLIENT_SECRETS_FILE = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")
    
    # AI/API settings (using placeholders)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    # Alternative free options: Hugging Face, Cohere, or local models
    
    # Video settings
    VIDEO_DURATION = 60  # seconds (YouTube Shorts max is 60)
    VIDEO_RESOLUTION = (1080, 1920)  # Vertical 9:16 format
    FPS = 30
    
    # Content settings
    MAX_TRENDS_TO_FETCH = 5
    SCRIPT_LENGTH = 100  # words max
    VOICEOVER_LANGUAGE = 'en'
    VOICEOVER_SPEED = 1.0  # Normal speed
    
    # Safety settings
    MIN_REVIEW_TIME = 60  # Minimum seconds between auto-uploads
    MAX_DAILY_UPLOADS = 3  # Stay well within YouTube limits
    
    # Paths to asset files (you'll need to provide these)
    BACKGROUND_VIDEOS_DIR = ASSETS_DIR / "background_videos"
    BACKGROUND_IMAGES_DIR = ASSETS_DIR / "background_images"
    FONTS_DIR = ASSETS_DIR / "fonts"
    MUSIC_DIR = ASSETS_DIR / "music"
    
    @classmethod
    def validate_config(cls):
        """Validate critical configuration"""
        missing = []
        
        # Check for required directories
        if not cls.BACKGROUND_VIDEOS_DIR.exists():
            missing.append(f"Background videos directory: {cls.BACKGROUND_VIDEOS_DIR}")
        
        # Warn about missing API keys (some are optional)
        if not cls.YOUTUBE_API_KEY:
            print("⚠️  Warning: YOUTUBE_API_KEY not set. Trend detection may be limited.")
        
        if missing:
            print("⚠️  Missing assets:")
            for item in missing:
                print(f"   - {item}")
            print("\nPlease create these directories or update paths in config.py")
        
        return len(missing) == 0


# Convenience function to get config instance
def get_config():
    return Config()
