"""
Provider factory for ShortSync Pro.

Creates and manages provider instances with fallback logic.
Supports MCP, simple, and hybrid provider modes.
"""

import logging
from typing import Dict, Any, Optional, Type
from enum import Enum

from bot.providers.base import (
    BaseTrendProvider, BaseScriptProvider, BaseFactCheckProvider,
    BaseAssetProvider, BaseVoiceoverProvider, BaseVideoProvider
)

logger = logging.getLogger(__name__)

class ProviderMode(Enum):
    """Provider operating modes"""
    SIMPLE = "simple"
    MCP = "mcp"
    HYBRID = "hybrid"

class ProviderConfig:
    """Configuration for a provider"""
    
    def __init__(self, provider_type: str, config: Dict[str, Any]):
        self.provider_type = provider_type
        self.mode = ProviderMode(config.get('mode', 'simple'))
        self.mcp_server_url = config.get('mcp_server_url')
        self.fallback_to_simple = config.get('fallback_to_simple', True)
        self.timeout_seconds = config.get('timeout_seconds', 30)
        self.max_retries = config.get('max_retries', 3)
        self.api_keys = config.get('api_keys', {})

class ProviderFactory:
    """Factory for creating provider instances"""
    
    def __init__(self, config):
        self.config = config
        self.providers: Dict[str, Any] = {}
        self.provider_configs: Dict[str, ProviderConfig] = {}
        self._initialized = False
        
        # Initialize provider configurations
        self._init_provider_configs()
    
    def _init_provider_configs(self):
        """Initialize provider configurations from main config"""
        # Trend detection provider
        trend_config = self.config.modules.get('trend_detection', {})
        self.provider_configs['trend'] = ProviderConfig(
            'trend',
            {
                'mode': getattr(trend_config, 'provider_type', 'simple').value,
                'mcp_server_url': getattr(trend_config, 'mcp_server_url', None),
                'fallback_to_simple': getattr(trend_config, 'fallback_to_simple', True),
                'timeout_seconds': getattr(trend_config, 'timeout_seconds', 30),
                'api_keys': {
                    'youtube_api_key': self.config.apis.get('youtube', {}).get('api_key'),
                    'newsapi_key': self.config.apis.get('newsapi', {}).get('api_key')
                }
            }
        )
        
        # Script generation provider
        script_config = self.config.modules.get('script_generation', {})
        self.provider_configs['script'] = ProviderConfig(
            'script',
            {
                'mode': getattr(script_config, 'provider_type', 'simple').value,
                'mcp_server_url': getattr(script_config, 'mcp_server_url', None),
                'fallback_to_simple': getattr(script_config, 'fallback_to_simple', True),
                'timeout_seconds': getattr(script_config, 'timeout_seconds', 30),
                'api_keys': {
                    'cohere_api_key': self.config.apis.get('cohere', {}).get('api_key'),
                    'hf_api_key': self.config.apis.get('huggingface', {}).get('api_key'),
                    'openai_api_key': self.config.apis.get('openai', {}).get('api_key')
                }
            }
        )
        
        # Fact checking provider
        fact_check_config = self.config.modules.get('fact_checking', {})
        self.provider_configs['fact_check'] = ProviderConfig(
            'fact_check',
            {
                'mode': getattr(fact_check_config, 'provider_type', 'simple').value,
                'mcp_server_url': getattr(fact_check_config, 'mcp_server_url', None),
                'fallback_to_simple': getattr(fact_check_config, 'fallback_to_simple', True),
                'timeout_seconds': getattr(fact_check_config, 'timeout_seconds', 30),
                'enabled': getattr(fact_check_config, 'enabled', False)
            }
        )
        
        # Asset gathering provider
        asset_config = self.config.modules.get('asset_gathering', {})
        self.provider_configs['asset'] = ProviderConfig(
            'asset',
            {
                'mode': getattr(asset_config, 'provider_type', 'simple').value,
                'mcp_server_url': getattr(asset_config, 'mcp_server_url', None),
                'fallback_to_simple': getattr(asset_config, 'fallback_to_simple', True),
                'timeout_seconds': getattr(asset_config, 'timeout_seconds', 30),
                'api_keys': {
                    'pexels_api_key': self.config.apis.get('pexels', {}).get('api_key'),
                    'unsplash_api_key': self.config.apis.get('unsplash', {}).get('api_key')
                }
            }
        )
        
        # Voiceover provider
        voiceover_config = self.config.modules.get('voiceover', {})
        self.provider_configs['voiceover'] = ProviderConfig(
            'voiceover',
            {
                'mode': getattr(voiceover_config, 'provider_type', 'simple').value,
                'mcp_server_url': getattr(voiceover_config, 'mcp_server_url', None),
                'fallback_to_simple': getattr(voiceover_config, 'fallback_to_simple', True),
                'timeout_seconds': getattr(voiceover_config, 'timeout_seconds', 30),
                'api_keys': {
                    'elevenlabs_api_key': self.config.apis.get('elevenlabs', {}).get('api_key')
                }
            }
        )
        
        # Video assembly provider
        video_config = self.config.modules.get('video_assembly', {})
        self.provider_configs['video'] = ProviderConfig(
            'video',
            {
                'mode': getattr(video_config, 'provider_type', 'simple').value,
                'mcp_server_url': getattr(video_config, 'mcp_server_url', None),
                'fallback_to_simple': getattr(video_config, 'fallback_to_simple', True),
                'timeout_seconds': getattr(video_config, 'timeout_seconds', 30)
            }
        )
    
    async def initialize(self):
        """Initialize the factory and all providers"""
        if self._initialized:
            return
        
        logger.info("Initializing provider factory...")
        
        # Initialize each provider type
        provider_types = [
            ('trend', self.create_trend_provider),
            ('script', self.create_script_provider),
            ('fact_check', self.create_fact_check_provider),
            ('asset', self.create_asset_provider),
            ('voiceover', self.create_voiceover_provider),
            ('video', self.create_video_provider)
        ]
        
        for provider_name, create_method in provider_types:
            try:
                provider = await create_method()
                if provider:
                    self.providers[provider_name] = provider
                    logger.info(f"Initialized {provider_name} provider")
                else:
                    logger.warning(f"Could not initialize {provider_name} provider")
            except Exception as e:
                logger.error(f"Failed to initialize {provider_name} provider: {e}")
        
        self._initialized = True
        logger.info(f"Provider factory initialized with {len(self.providers)} providers")
    
    async def create_trend_provider(self) -> Optional[BaseTrendProvider]:
        """Create trend detection provider"""
        config = self.provider_configs.get('trend')
        
        if not config:
            logger.warning("No trend provider configuration found")
            return None
        
        try:
            if config.mode == ProviderMode.MCP and config.mcp_server_url:
                # Try MCP provider first
                provider = await self._create_mcp_trend_provider(config)
                if provider:
                    return provider
            
            # Fallback to simple provider
            if config.fallback_to_simple:
                return await self._create_simple_trend_provider(config)
            
        except Exception as e:
            logger.error(f"Failed to create trend provider: {e}")
            if config.fallback_to_simple:
                return await self._create_simple_trend_provider(config)
        
        return None
    
    async def create_script_provider(self) -> Optional[BaseScriptProvider]:
        """Create script generation provider"""
        config = self.provider_configs.get('script')
        
        if not config:
            logger.warning("No script provider configuration found")
            return None
        
        try:
            if config.mode == ProviderMode.MCP and config.mcp_server_url:
                # Try MCP provider first
                provider = await self._create_mcp_script_provider(config)
                if provider:
                    return provider
            
            # Fallback to simple provider
            if config.fallback_to_simple:
                return await self._create_simple_script_provider(config)
            
        except Exception as e:
            logger.error(f"Failed to create script provider: {e}")
            if config.fallback_to_simple:
                return await self._create_simple_script_provider(config)
        
        return None
    
    async def create_fact_check_provider(self) -> Optional[BaseFactCheckProvider]:
        """Create fact checking provider"""
        config = self.provider_configs.get('fact_check')
        
        if not config or not getattr(config, 'enabled', False):
            logger.debug("Fact checking disabled or not configured")
            return None
        
        try:
            if config.mode == ProviderMode.MCP and config.mcp_server_url:
                # Try MCP provider first
                provider = await self._create_mcp_fact_check_provider(config)
                if provider:
                    return provider
            
            # Fallback to simple provider
            if config.fallback_to_simple:
                return await self._create_simple_fact_check_provider(config)
            
        except Exception as e:
            logger.error(f"Failed to create fact check provider: {e}")
            if config.fallback_to_simple:
                return await self._create_simple_fact_check_provider(config)
        
        return None
    
    async def create_asset_provider(self) -> Optional[BaseAssetProvider]:
        """Create asset gathering provider"""
        config = self.provider_configs.get('asset')
        
        if not config:
            logger.warning("No asset provider configuration found")
            return None
        
        try:
            if config.mode == ProviderMode.MCP and config.mcp_server_url:
                # Try MCP provider first
                provider = await self._create_mcp_asset_provider(config)
                if provider:
                    return provider
            
            # Fallback to simple provider
            if config.fallback_to_simple:
                return await self._create_simple_asset_provider(config)
            
        except Exception as e:
            logger.error(f"Failed to create asset provider: {e}")
            if config.fallback_to_simple:
                return await self._create_simple_asset_provider(config)
        
        return None
    
    async def create_voiceover_provider(self) -> Optional[BaseVoiceoverProvider]:
        """Create voiceover provider"""
        config = self.provider_configs.get('voiceover')
        
        if not config:
            logger.warning("No voiceover provider configuration found")
            return None
        
        try:
            if config.mode == ProviderMode.MCP and config.mcp_server_url:
                # Try MCP provider first
                provider = await self._create_mcp_voiceover_provider(config)
                if provider:
                    return provider
            
            # Fallback to simple provider
            if config.fallback_to_simple:
                return await self._create_simple_voiceover_provider(config)
            
        except Exception as e:
            logger.error(f"Failed to create voiceover provider: {e}")
            if config.fallback_to_simple:
                return await self._create_simple_voiceover_provider(config)
        
        return None
    
    async def create_video_provider(self) -> Optional[BaseVideoProvider]:
        """Create video assembly provider"""
        config = self.provider_configs.get('video')
        
        if not config:
            logger.warning("No video provider configuration found")
            return None
        
        try:
            if config.mode == ProviderMode.MCP and config.mcp_server_url:
                # Try MCP provider first
                provider = await self._create_mcp_video_provider(config)
                if provider:
                    return provider
            
            # Fallback to simple provider
            if config.fallback_to_simple:
                return await self._create_simple_video_provider(config)
            
        except Exception as e:
            logger.error(f"Failed to create video provider: {e}")
            if config.fallback_to_simple:
                return await self._create_simple_video_provider(config)
        
        return None
    
    async def _create_simple_trend_provider(self, config: ProviderConfig) -> Optional[BaseTrendProvider]:
        """Create simple trend detection provider"""
        try:
            from bot.providers.simple.trend_provider import SimpleTrendProvider
            
            provider_config = {
                'youtube_api_key': config.api_keys.get('youtube_api_key'),
                'newsapi_key': config.api_keys.get('newsapi_key'),
                'timeout_seconds': config.timeout_seconds,
                'max_retries': config.max_retries
            }
            
            provider = SimpleTrendProvider(provider_config)
            if hasattr(provider, 'initialize'):
                await provider.initialize()
            
            return provider
            
        except ImportError as e:
            logger.error(f"Simple trend provider not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create simple trend provider: {e}")
            return None
    
    async def _create_simple_script_provider(self, config: ProviderConfig) -> Optional[BaseScriptProvider]:
        """Create simple script generation provider"""
        try:
            from bot.providers.simple.script_provider import SimpleScriptProvider
            
            provider_config = {
                'cohere_api_key': config.api_keys.get('cohere_api_key'),
                'hf_api_key': config.api_keys.get('hf_api_key'),
                'openai_api_key': config.api_keys.get('openai_api_key'),
                'timeout_seconds': config.timeout_seconds,
                'max_retries': config.max_retries
            }
            
            provider = SimpleScriptProvider(provider_config)
            if hasattr(provider, 'initialize'):
                await provider.initialize()
            
            return provider
            
        except ImportError as e:
            logger.error(f"Simple script provider not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create simple script provider: {e}")
            return None
    
    async def _create_simple_fact_check_provider(self, config: ProviderConfig) -> Optional[BaseFactCheckProvider]:
        """Create simple fact checking provider"""
        # Simple fact checking is usually disabled by default
        # This would be a placeholder or basic web search implementation
        logger.debug("Simple fact checking provider not implemented")
        return None
    
    async def _create_simple_asset_provider(self, config: ProviderConfig) -> Optional[BaseAssetProvider]:
        """Create simple asset gathering provider"""
        try:
            from bot.providers.simple.asset_provider import SimpleAssetProvider
            
            provider_config = {
                'pexels_api_key': config.api_keys.get('pexels_api_key'),
                'unsplash_api_key': config.api_keys.get('unsplash_api_key'),
                'timeout_seconds': config.timeout_seconds,
                'max_retries': config.max_retries
            }
            
            provider = SimpleAssetProvider(provider_config)
            if hasattr(provider, 'initialize'):
                await provider.initialize()
            
            return provider
            
        except ImportError as e:
            logger.error(f"Simple asset provider not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create simple asset provider: {e}")
            return None
    
    async def _create_simple_voiceover_provider(self, config: ProviderConfig) -> Optional[BaseVoiceoverProvider]:
        """Create simple voiceover provider"""
        try:
            from bot.providers.simple.voiceover_provider import SimpleVoiceoverProvider
            
            provider_config = {
                'elevenlabs_api_key': config.api_keys.get('elevenlabs_api_key'),
                'timeout_seconds': config.timeout_seconds,
                'max_retries': config.max_retries
            }
            
            provider = SimpleVoiceoverProvider(provider_config)
            if hasattr(provider, 'initialize'):
                await provider.initialize()
            
            return provider
            
        except ImportError as e:
            logger.error(f"Simple voiceover provider not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create simple voiceover provider: {e}")
            return None
    
    async def _create_simple_video_provider(self, config: ProviderConfig) -> Optional[BaseVideoProvider]:
        """Create simple video assembly provider"""
        try:
            from bot.providers.simple.video_provider import SimpleVideoProvider
            
            provider_config = {
                'timeout_seconds': config.timeout_seconds,
                'max_retries': config.max_retries
            }
            
            provider = SimpleVideoProvider(provider_config)
            if hasattr(provider, 'initialize'):
                await provider.initialize()
            
            return provider
            
        except ImportError as e:
            logger.error(f"Simple video provider not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create simple video provider: {e}")
            return None
    
    async def _create_mcp_trend_provider(self, config: ProviderConfig) -> Optional[BaseTrendProvider]:
        """Create MCP trend detection provider"""
        # MCP implementation would go here
        # This requires MCP server to be running
        logger.debug("MCP trend provider not implemented (requires MCP server)")
        return None
    
    async def _create_mcp_script_provider(self, config: ProviderConfig) -> Optional[BaseScriptProvider]:
        """Create MCP script generation provider"""
        logger.debug("MCP script provider not implemented (requires MCP server)")
        return None
    
    async def _create_mcp_fact_check_provider(self, config: ProviderConfig) -> Optional[BaseFactCheckProvider]:
        """Create MCP fact checking provider"""
        logger.debug("MCP fact check provider not implemented (requires MCP server)")
        return None
    
    async def _create_mcp_asset_provider(self, config: ProviderConfig) -> Optional[BaseAssetProvider]:
        """Create MCP asset gathering provider"""
        logger.debug("MCP asset provider not implemented (requires MCP server)")
        return None
    
    async def _create_mcp_voiceover_provider(self, config: ProviderConfig) -> Optional[BaseVoiceoverProvider]:
        """Create MCP voiceover provider"""
        logger.debug("MCP voiceover provider not implemented (requires MCP server)")
        return None
    
    async def _create_mcp_video_provider(self, config: ProviderConfig) -> Optional[BaseVideoProvider]:
        """Create MCP video assembly provider"""
        logger.debug("MCP video provider not implemented (requires MCP server)")
        return None
    
    def get_provider(self, provider_type: str) -> Optional[Any]:
        """Get initialized provider by type"""
        return self.providers.get(provider_type)
    
    def get_all_providers(self) -> Dict[str, Any]:
        """Get all initialized providers"""
        return self.providers.copy()
    
    async def close(self):
        """Close all provider resources"""
        for provider_name, provider in self.providers.items():
            try:
                if hasattr(provider, 'close'):
                    await provider.close()
                logger.debug(f"Closed {provider_name} provider")
            except Exception as e:
                logger.error(f"Error closing {provider_name} provider: {e}")
        
        self.providers.clear()
        self._initialized = False
        logger.info("All providers closed")
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about all providers"""
        info = {
            'initialized': self._initialized,
            'providers': {},
            'configs': {}
        }
        
        for provider_name, provider in self.providers.items():
            info['providers'][provider_name] = {
                'type': type(provider).__name__,
                'initialized': True
            }
        
        for provider_name, config in self.provider_configs.items():
            info['configs'][provider_name] = {
                'mode': config.mode.value,
                'mcp_server_url': config.mcp_server_url,
                'fallback_to_simple': config.fallback_to_simple,
                'timeout_seconds': config.timeout_seconds,
                'has_api_keys': bool(config.api_keys)
            }
        
        return info

# Global provider registry
PROVIDER_REGISTRY = {}

def register_provider(provider_type: str, provider_class: Type):
    """Register a provider class in the global registry"""
    PROVIDER_REGISTRY[provider_type] = provider_class

def get_registered_providers() -> Dict[str, Type]:
    """Get all registered provider classes"""
    return PROVIDER_REGISTRY.copy()
