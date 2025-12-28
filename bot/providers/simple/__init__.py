"""
Simple providers subpackage for ShortSync Pro.

This package contains simple, self-contained provider implementations
that don't require external MCP servers. These are the default providers
that work out-of-the-box with minimal configuration.

Contents:
- Simple script generation providers
- Simple trend detection providers
- Simple voiceover providers
- Simple asset gathering providers
"""

__all__ = [
    'script_provider',
    'trend_provider',
    'voiceover_provider',
    'asset_provider'
]

# Simple providers version
__version__ = "1.0.0"

# Export simple provider implementations
from .script_provider import SimpleScriptProvider
from .trend_provider import SimpleTrendProvider
from .voiceover_provider import SimpleVoiceoverProvider
from .asset_provider import SimpleAssetProvider

def initialize_simple_providers():
    """Initialize simple providers subpackage."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Simple providers subpackage initialized")
    
    # Register simple providers with the main factory
    try:
        from ..factory import ProviderFactory
        factory = ProviderFactory()
        
        # Register each provider type
        providers = [
            ('script', SimpleScriptProvider),
            ('trend', SimpleTrendProvider),
            ('voiceover', SimpleVoiceoverProvider),
            ('asset', SimpleAssetProvider)
        ]
        
        for provider_type, provider_class in providers:
            factory.register_provider(provider_type, 'simple', provider_class)
            logger.debug(f"Registered simple provider: {provider_type}")
            
    except ImportError as e:
        logger.warning(f"Could not register simple providers: {e}")
    
    return True

# Package metadata
PACKAGE_NAME = "shortsync-simple-providers"
DESCRIPTION = "Simple, self-contained providers for ShortSync Pro"

def get_simple_provider_info():
    """Get information about available simple providers."""
    return {
        'package': PACKAGE_NAME,
        'version': __version__,
        'description': DESCRIPTION,
        'providers': {
            'script': 'SimpleScriptProvider - Basic AI script generation',
            'trend': 'SimpleTrendProvider - Basic trend detection',
            'voiceover': 'SimpleVoiceoverProvider - Basic text-to-speech',
            'asset': 'SimpleAssetProvider - Basic stock asset gathering'
        }
    }
