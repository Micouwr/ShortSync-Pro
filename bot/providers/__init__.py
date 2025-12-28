"""
Providers package for ShortSync Pro.

This package contains AI and service provider implementations:
- AI script generation providers (Cohere, Hugging Face, OpenAI, Claude)
- Trend detection providers
- Voiceover providers (ElevenLabs, Google TTS)
- Asset gathering providers (Pexels, Unsplash)
- Provider factory and configuration management
"""

__all__ = [
    'base',
    'factory',
    'simple',
    'mcp'
]

# Providers package version
__version__ = "1.0.0"

# Export main provider components
from .base import BaseProvider, ProviderError, ProviderConfig
from .factory import ProviderFactory

def initialize_providers():
    """Initialize providers package."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Providers package initialized")
    
    # Initialize provider registry
    from .factory import PROVIDER_REGISTRY
    logger.info(f"Registered providers: {list(PROVIDER_REGISTRY.keys())}")
    
    return True

# Package metadata
PACKAGE_NAME = "shortsync-providers"
DESCRIPTION = "AI and service providers for ShortSync Pro"

def list_available_providers():
    """List all available provider types."""
    return {
        'ai_script': ['cohere', 'huggingface', 'openai', 'claude'],
        'trend_detection': ['youtube_trends', 'news_api', 'reddit_trends'],
        'voiceover': ['elevenlabs', 'google_tts', 'amazon_polly'],
        'assets': ['pexels', 'unsplash', 'pixabay']
    }
