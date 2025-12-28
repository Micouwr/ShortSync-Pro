# bot/providers/factory.py
"""
Factory for creating providers based on configuration.
Makes it easy to switch between simple and MCP providers.
"""

from typing import Dict, Any
from bot.providers.base import (
    BaseTrendProvider, BaseScriptProvider, BaseFactCheckProvider,
    BaseAssetProvider, BaseVoiceoverProvider, BaseVideoProvider
)
from bot.config import ProviderType, Config

class ProviderFactory:
    """Factory for creating providers"""
    
    def __init__(self, config: Config):
        self.config = config
    
    async def create_trend_provider(self) -> BaseTrendProvider:
        """Create trend provider based on config"""
        module_config = self.config.modules['trend_detection']
        
        if module_config.provider_type == ProviderType.MCP:
            # Future MCP implementation
            from bot.providers.mcp.trend_provider import MCPTrendProvider
            return MCPTrendProvider(self.config)
        else:
            from bot.providers.simple.trend_provider import SimpleTrendProvider
            return SimpleTrendProvider(self.config.apis)
    
    async def create_script_provider(self) -> BaseScriptProvider:
        """Create script provider based on config"""
        module_config = self.config.modules['script_generation']
        
        if module_config.provider_type == ProviderType.MCP:
            # Future MCP implementation
            from bot.providers.mcp.script_provider import MCPScriptProvider
            return MCPScriptProvider(self.config)
        else:
            from bot.providers.simple.script_provider import SimpleScriptProvider
            return SimpleScriptProvider(self.config.apis)
    
    async def create_fact_check_provider(self) -> BaseFactCheckProvider:
        """Create fact check provider (disabled by default)"""
        module_config = self.config.modules['fact_checking']
        
        if not module_config.enabled:
            from bot.providers.simple.fact_check_provider import SimpleFactCheckProvider
            return SimpleFactCheckProvider(self.config)
        
        if module_config.provider_type == ProviderType.MCP:
            # Future MCP implementation
            from bot.providers.mcp.fact_check_provider import MCPFactCheckProvider
            return MCPFactCheckProvider(self.config)
        else:
            from bot.providers.simple.fact_check_provider import SimpleFactCheckProvider
            return SimpleFactCheckProvider(self.config)
    
    async def create_asset_provider(self) -> BaseAssetProvider:
        """Create asset provider"""
        module_config = self.config.modules['asset_gathering']
        
        if module_config.provider_type == ProviderType.MCP:
            # Future MCP implementation
            from bot.providers.mcp.asset_provider import MCPAssetProvider
            return MCPAssetProvider(self.config)
        else:
            from bot.providers.simple.asset_provider import SimpleAssetProvider
            return SimpleAssetProvider(self.config.apis)
    
    async def create_voiceover_provider(self) -> BaseVoiceoverProvider:
        """Create voiceover provider"""
        module_config = self.config.modules['voiceover']
        
        if module_config.provider_type == ProviderType.MCP:
            # Future MCP implementation
            from bot.providers.mcp.voiceover_provider import MCPVoiceoverProvider
            return MCPVoiceoverProvider(self.config)
        else:
            from bot.providers.simple.voiceover_provider import SimpleVoiceoverProvider
            return SimpleVoiceoverProvider(self.config.apis)
    
    async def create_video_provider(self) -> BaseVideoProvider:
        """Create video provider"""
        module_config = self.config.modules['video_assembly']
        
        if module_config.provider_type == ProviderType.MCP:
            # Future MCP implementation
            from bot.providers.mcp.video_provider import MCPVideoProvider
            return MCPVideoProvider(self.config)
        else:
            from bot.providers.simple.video_provider import SimpleVideoProvider
            return SimpleVideoProvider(self.config)
