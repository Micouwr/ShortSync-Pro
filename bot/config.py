"""
Configuration management for ShortSync Pro.

Centralized configuration system with environment variable support,
file-based configuration, and validation.
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class ProviderType(Enum):
    """Provider types for each module"""
    SIMPLE = "simple"
    MCP = "mcp"
    HYBRID = "hybrid"

class ContentQuality(Enum):
    """Content quality standards"""
    PREMIUM = "premium"     # Highest quality, fact-checked
    STANDARD = "standard"   # Good quality, basic checks
    EXPRESS = "express"     # Quick content, minimal checks

@dataclass
class ModuleConfig:
    """Configuration for each module"""
    enabled: bool = True
    provider_type: ProviderType = ProviderType.SIMPLE
    mcp_server_url: Optional[str] = None
    fallback_to_simple: bool = True
    timeout_seconds: int = 30
    max_retries: int = 3

@dataclass
class ChannelConfig:
    """Configuration for individual YouTube channel"""
    name: str
    niche: str
    quality_standard: ContentQuality = ContentQuality.STANDARD
    upload_schedule: Dict[str, List[str]] = field(default_factory=lambda: {
        "monday": ["09:00", "13:00", "18:00"],
        "tuesday": ["09:00", "13:00", "18:00"],
        "wednesday": ["09:00", "13:00", "18:00"],
        "thursday": ["09:00", "13:00", "18:00"],
        "friday": ["09:00", "13:00", "18:00"],
        "saturday": ["10:00", "14:00"],
        "sunday": ["10:00", "14:00"]
    })
    branding: Dict = field(default_factory=lambda: {
        "intro_template": "default_intro.mp4",
        "outro_template": "default_outro.png",
        "watermark": "channel_logo.png",
        "color_scheme": "#FF0000",
        "voice_id": "default"
    })

@dataclass
class PipelineConfig:
    """Pipeline configuration"""
    max_concurrent_jobs: int = 3
    job_timeout_minutes: int = 15
    retry_attempts: int = 3
    retry_delay_seconds: int = 30
    checkpoint_interval: int = 5  # Save state every N jobs

@dataclass
class YouTubeConfig:
    """YouTube specific configuration"""
    max_daily_uploads: int = 3
    min_upload_interval: int = 14400  # 4 hours
    default_privacy: str = "private"
    categories: List[str] = field(default_factory=lambda: [
        "Education", "Science & Technology", "Howto & Style"
    ])
    max_video_duration: int = 58  # YouTube Shorts limit
    min_video_duration: int = 15  # Minimum for engagement

@dataclass
class ContentConfig:
    """Content generation configuration"""
    default_duration: int = 45  # seconds
    min_quality_score: float = 70.0
    max_title_length: int = 100
    max_description_length: int = 5000
    default_hashtags: List[str] = field(default_factory=lambda: [
        "#shorts", "#youtubeshorts", "#shortsvideo"
    ])

class Config:
    """Main configuration class"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.base_dir = Path(__file__).parent.parent
        
        # Environment detection
        self.environment = os.getenv("ENVIRONMENT", "development").lower()
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # Core directories
        self.dirs = {
            'data': self.base_dir / 'data',
            'logs': self.base_dir / 'logs',
            'temp': self.base_dir / 'temp',
            'assets': self.base_dir / 'assets',
            'output': self.base_dir / 'output',
            'cache': self.base_dir / 'data' / 'cache',
            'state': self.base_dir / 'data' / 'state',
            'queue': self.base_dir / 'data' / 'queue',
            'backups': self.base_dir / 'data' / 'backups'
        }
        
        # Create all directories
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create output subdirectories
        output_subdirs = ['pending_approval', 'approved', 'rejected', 'uploaded', 
                         'audio', 'video', 'thumbnails']
        for subdir in output_subdirs:
            (self.dirs['output'] / subdir).mkdir(exist_ok=True)
        
        # Module configurations (MCP-ready)
        self.modules = {
            'trend_detection': ModuleConfig(
                provider_type=ProviderType(os.getenv('TREND_PROVIDER', 'simple')),
                mcp_server_url=os.getenv('TREND_MCP_URL')
            ),
            'script_generation': ModuleConfig(
                provider_type=ProviderType(os.getenv('SCRIPT_PROVIDER', 'simple')),
                mcp_server_url=os.getenv('SCRIPT_MCP_URL')
            ),
            'fact_checking': ModuleConfig(
                enabled=False,  # Disabled by default, enable for MCP
                provider_type=ProviderType(os.getenv('FACT_CHECK_PROVIDER', 'simple')),
                mcp_server_url=os.getenv('FACT_CHECK_MCP_URL')
            ),
            'asset_gathering': ModuleConfig(
                provider_type=ProviderType(os.getenv('ASSET_PROVIDER', 'simple')),
                mcp_server_url=os.getenv('ASSET_MCP_URL')
            ),
            'voiceover': ModuleConfig(
                provider_type=ProviderType(os.getenv('VOICEOVER_PROVIDER', 'simple'))
            ),
            'video_assembly': ModuleConfig(
                provider_type=ProviderType(os.getenv('VIDEO_PROVIDER', 'simple'))
            ),
            'thumbnail_generation': ModuleConfig(
                provider_type=ProviderType(os.getenv('THUMBNAIL_PROVIDER', 'simple'))
            ),
            'youtube_upload': ModuleConfig(
                enabled=True,
                provider_type=ProviderType.SIMPLE
            )
        }
        
        # Pipeline config
        self.pipeline = PipelineConfig()
        
        # YouTube config
        self.youtube = YouTubeConfig()
        
        # Content config
        self.content = ContentConfig()
        
        # API configurations
        self.apis = self._load_api_configs()
        
        # Channel configurations
        self.channels = self._load_channels()
        
        # Load YAML config if provided
        if config_path and Path(config_path).exists():
            self._load_yaml_config(config_path)
        
        # Validate configuration
        self._validate_config()
    
    def _load_api_configs(self) -> Dict[str, Any]:
        """Load API configurations"""
        return {
            'youtube': {
                'api_key': os.getenv('YOUTUBE_API_KEY', ''),
                'client_secrets_path': os.getenv('YOUTUBE_CLIENT_SECRETS_PATH', ''),
                'rate_limit': {'requests': 10000, 'period': 86400}  # Daily quota
            },
            'pexels': {
                'api_key': os.getenv('PEXELS_API_KEY', ''),
                'rate_limit': {'requests': 200, 'period': 3600}
            },
            'unsplash': {
                'api_key': os.getenv('UNSPLASH_API_KEY', ''),
                'rate_limit': {'requests': 50, 'period': 3600}
            },
            'elevenlabs': {
                'api_key': os.getenv('ELEVENLABS_API_KEY', ''),
                'rate_limit': {'requests': 100, 'period': 3600}
            },
            'huggingface': {
                'api_key': os.getenv('HF_API_KEY', ''),
                'rate_limit': {'requests': 30, 'period': 3600}
            },
            'cohere': {
                'api_key': os.getenv('COHERE_API_KEY', ''),
                'rate_limit': {'requests': 100, 'period': 60}
            },
            'openai': {
                'api_key': os.getenv('OPENAI_API_KEY', ''),
                'rate_limit': {'requests': 3500, 'period': 60}
            },
            'newsapi': {
                'api_key': os.getenv('NEWSAPI_KEY', ''),
                'rate_limit': {'requests': 100, 'period': 86400}
            }
        }
    
    def _load_channels(self) -> List[ChannelConfig]:
        """Load channel configurations from file"""
        channels_file = self.dirs['data'] / 'channels.json'
        
        if channels_file.exists():
            try:
                with open(channels_file, 'r') as f:
                    channels_data = json.load(f)
                
                channels = []
                for channel_data in channels_data:
                    channels.append(ChannelConfig(
                        name=channel_data.get('name', 'Unnamed Channel'),
                        niche=channel_data.get('niche', 'education'),
                        quality_standard=ContentQuality(channel_data.get('quality_standard', 'standard')),
                        upload_schedule=channel_data.get('upload_schedule', {}),
                        branding=channel_data.get('branding', {})
                    ))
                return channels
            except Exception as e:
                print(f"Warning: Could not load channels from {channels_file}: {e}")
        
        # Default channel if none exist
        return [ChannelConfig(
            name="Default Channel",
            niche="education",
            quality_standard=ContentQuality.STANDARD
        )]
    
    def _load_yaml_config(self, config_path: str):
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
                
            if config_data:
                # Update module configurations
                if 'modules' in config_data:
                    for module_name, module_config in config_data['modules'].items():
                        if module_name in self.modules:
                            if 'enabled' in module_config:
                                self.modules[module_name].enabled = module_config['enabled']
                            if 'provider_type' in module_config:
                                self.modules[module_name].provider_type = ProviderType(module_config['provider_type'])
                
                # Update pipeline config
                if 'pipeline' in config_data:
                    pipeline_data = config_data['pipeline']
                    for key, value in pipeline_data.items():
                        if hasattr(self.pipeline, key):
                            setattr(self.pipeline, key, value)
                
                # Update YouTube config
                if 'youtube' in config_data:
                    youtube_data = config_data['youtube']
                    for key, value in youtube_data.items():
                        if hasattr(self.youtube, key):
                            setattr(self.youtube, key, value)
                
                # Update content config
                if 'content' in config_data:
                    content_data = config_data['content']
                    for key, value in content_data.items():
                        if hasattr(self.content, key):
                            setattr(self.content, key, value)
                            
        except Exception as e:
            print(f"Warning: Could not load YAML config from {config_path}: {e}")
    
    def _validate_config(self):
        """Validate configuration settings"""
        warnings = []
        
        # Check required API keys based on enabled modules
        if self.modules['script_generation'].enabled:
            if not self.apis['cohere']['api_key'] and not self.apis['huggingface']['api_key']:
                warnings.append("No AI API key configured (Cohere or Hugging Face needed for script generation)")
        
        if self.modules['asset_gathering'].enabled:
            if not self.apis['pexels']['api_key'] and not self.apis['unsplash']['api_key']:
                warnings.append("No stock media API key configured (Pexels or Unsplash needed for asset gathering)")
        
        if self.modules['voiceover'].enabled:
            if not self.apis['elevenlabs']['api_key']:
                warnings.append("No ElevenLabs API key configured (needed for voiceover)")
        
        if self.modules['youtube_upload'].enabled:
            if not self.apis['youtube']['api_key']:
                warnings.append("No YouTube API key configured (needed for upload)")
        
        # Validate content settings
        if self.content.min_quality_score < 0 or self.content.min_quality_score > 100:
            warnings.append(f"Invalid min_quality_score: {self.content.min_quality_score}. Must be between 0-100")
        
        if self.youtube.max_daily_uploads > 10:
            warnings.append(f"max_daily_uploads ({self.youtube.max_daily_uploads}) is high. YouTube may flag as spam.")
        
        # Log warnings
        if warnings and self.debug:
            print("Configuration warnings:")
            for warning in warnings:
                print(f"  ⚠️  {warning}")
    
    def save_channels(self):
        """Save channel configurations to file"""
        channels_file = self.dirs['data'] / 'channels.json'
        
        channels_data = []
        for channel in self.channels:
            channels_data.append({
                'name': channel.name,
                'niche': channel.niche,
                'quality_standard': channel.quality_standard.value,
                'upload_schedule': channel.upload_schedule,
                'branding': channel.branding
            })
        
        with open(channels_file, 'w') as f:
            json.dump(channels_data, f, indent=2)
    
    def add_channel(self, channel: ChannelConfig):
        """Add a new channel configuration"""
        self.channels.append(channel)
        self.save_channels()
    
    def get_channel(self, name: str) -> Optional[ChannelConfig]:
        """Get channel configuration by name"""
        for channel in self.channels:
            if channel.name == name:
                return channel
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'environment': self.environment,
            'debug': self.debug,
            'directories': {k: str(v) for k, v in self.dirs.items()},
            'modules': {
                name: {
                    'enabled': config.enabled,
                    'provider_type': config.provider_type.value,
                    'mcp_server_url': config.mcp_server_url
                }
                for name, config in self.modules.items()
            },
            'pipeline': {
                'max_concurrent_jobs': self.pipeline.max_concurrent_jobs,
                'job_timeout_minutes': self.pipeline.job_timeout_minutes,
                'retry_attempts': self.pipeline.retry_attempts,
                'retry_delay_seconds': self.pipeline.retry_delay_seconds
            },
            'youtube': {
                'max_daily_uploads': self.youtube.max_daily_uploads,
                'min_upload_interval': self.youtube.min_upload_interval,
                'default_privacy': self.youtube.default_privacy,
                'categories': self.youtube.categories
            },
            'content': {
                'default_duration': self.content.default_duration,
                'min_quality_score': self.content.min_quality_score,
                'max_title_length': self.content.max_title_length
            },
            'channels': [
                {
                    'name': channel.name,
                    'niche': channel.niche,
                    'quality_standard': channel.quality_standard.value
                }
                for channel in self.channels
            ]
        }
    
    def __str__(self) -> str:
        """String representation of configuration"""
        config_dict = self.to_dict()
        return json.dumps(config_dict, indent=2)
    
    @property
    def use_mcp(self) -> bool:
        """Check if any module is using MCP"""
        return any(
            module.provider_type == ProviderType.MCP 
            for module in self.modules.values()
        )
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment == "development"

# Singleton instance for easy access
_config_instance = None

def get_config(config_path: Optional[str] = None) -> Config:
    """Get configuration instance (singleton pattern)"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance

def reload_config(config_path: Optional[str] = None) -> Config:
    """Reload configuration from file"""
    global _config_instance
    _config_instance = Config(config_path)
    return _config_instance
