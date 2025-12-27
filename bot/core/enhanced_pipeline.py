# bot/core/enhanced_pipeline.py
"""
Enhanced pipeline using provider factory
"""

import asyncio
from typing import Dict, Any, Optional
import logging
from pathlib import Path

from bot.providers.factory import ProviderFactory
from bot.providers.base import Trend, Script, Asset
from bot.core.pipeline import Pipeline
from bot.config import Config, PipelineStage

logger = logging.getLogger(__name__)

class EnhancedPipeline(Pipeline):
    """Enhanced pipeline using provider pattern"""
    
    def __init__(self, config: Config, state_manager, job_queue):
        super().__init__(config, state_manager, job_queue)
        self.provider_factory = ProviderFactory(config)
        self.providers = {}
    
    async def initialize_providers(self):
        """Initialize all providers"""
        self.providers['trend'] = await self.provider_factory.create_trend_provider()
        self.providers['script'] = await self.provider_factory.create_script_provider()
        self.providers['fact_check'] = await self.provider_factory.create_fact_check_provider()
        self.providers['asset'] = await self.provider_factory.create_asset_provider()
        self.providers['voiceover'] = await self.provider_factory.create_voiceover_provider()
        self.providers['video'] = await self.provider_factory.create_video_provider()
        
        # Initialize each provider
        for name, provider in self.providers.items():
            if hasattr(provider, 'initialize'):
                await provider.initialize()
    
    async def _process_trend_detection(self, job) -> Dict[str, Any]:
        """Process trend detection with provider"""
        provider = self.providers['trend']
        
        # Get trends
        trends = await provider.get_trends(limit=5)
        
        # Select best trend
        if not trends:
            logger.error("No trends found")
            return None
        
        selected = trends[0]
        
        # Validate trend (basic or MCP-enhanced)
        validation = await provider.validate_trend(selected)
        
        if not validation.get('is_valid', True):
            logger.warning(f"Trend validation failed: {validation}")
            # Try next trend
            if len(trends) > 1:
                selected = trends[1]
                validation = await provider.validate_trend(selected)
        
        return {
            'trend': selected,
            'validation': validation,
            'alternatives': trends[1:3]
        }
    
    async def _process_script_generation(self, job) -> Script:
        """Generate script with provider"""
        provider = self.providers['script']
        trend = job.trend_data['trend']
        
        # Generate script
        script = await provider.generate_script(
            topic=trend.topic,
            duration_seconds=self.config.content.duration_range[1]
        )
        
        # Improve script
        improved = await provider.improve_script(script)
        
        # Fact check if enabled
        if self.config.modules['fact_checking'].enabled:
            fact_check = await self.providers['fact_check'].fact_check(improved.content)
            improved.metadata['fact_check'] = fact_check
        
        return improved
    
    async def _process_asset_gathering(self, job) -> Dict[str, Any]:
        """Gather assets with provider"""
        provider = self.providers['asset']
        trend = job.trend_data['trend']
        script = job.script_result
        
        # Search for video assets
        videos = await provider.search_videos(
            query=trend.topic,
            duration_range=(3, 8),
            limit=5
        )
        
        # Search for image assets
        images = await provider.search_images(
            query=trend.topic,
            limit=10
        )
        
        return {
            'videos': videos,
            'images': images,
            'selected_video': videos[0] if videos else None,
            'selected_images': images[:3] if images else []
        }
    
    async def _process_voiceover(self, job) -> Path:
        """Generate voiceover with provider"""
        provider = self.providers['voiceover']
        script = job.script_result
        
        output_path = self.config.dirs['output'] / 'audio' / f"{job.job_id}.mp3"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        return await provider.generate_voiceover(
            text=script.content,
            output_path=output_path
        )
    
    async def _process_video_assembly(self, job) -> Path:
        """Assemble video with provider"""
        provider = self.providers['video']
        
        output_path = self.config.dirs['output'] / 'video' / f"{job.job_id}.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        return await provider.assemble_video(
            script=job.script_result,
            voiceover_path=job.voiceover_result,
            assets=job.asset_result['selected_assets'],
            output_path=output_path
        )
