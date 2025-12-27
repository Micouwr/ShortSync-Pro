# bot/config.py
"""
Professional configuration with MCP-ready architecture
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import yaml
from dotenv import load_dotenv

load_dotenv()

class ProviderType(Enum):
    """Provider types for each module"""
    SIMPLE = "simple"
    MCP = "mcp"
    HYBRID = "hybrid"

@dataclass
class ModuleConfig:
    """Configuration for each module"""
    enabled: bool = True
    provider_type: ProviderType = ProviderType.SIMPLE
    mcp_server_url: Optional[str] = None
    fallback_to_simple: bool = True
    timeout_seconds: int = 30

@dataclass
class PipelineConfig:
    """Pipeline configuration"""
    max_concurrent_jobs: int = 3
    job_timeout_minutes: int = 15
    retry_attempts: int = 3
    retry_delay_seconds: int = 30

@dataclass
class YouTubeConfig:
    """YouTube specific configuration"""
    max_daily_uploads: int = 3
    min_upload_interval: int = 14400  # 4 hours
    default_privacy: str = "private"
    categories: List[str] = field(default_factory=lambda: [
        "Education", "Science & Technology", "Howto & Style"
    ])

class Config:
    """Main configuration class"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.base_dir = Path(__file__).parent.parent
        
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
        }
        
        # Create all directories
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
        
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
        }
        
        # Pipeline config
        self.pipeline = PipelineConfig()
        
        # YouTube config
        self.youtube = YouTubeConfig()
        
        # API configurations
        self.apis = self._load_api_configs()
        
        # Load YAML config if provided
        if config_path and Path(config_path).exists():
            self._load_yaml_config(config_path)
    
    def _load_api_configs(self) -> Dict[str, Any]:
        """Load API configurations"""
        return {
            'pexels': {
                'api_key': os.getenv('PEXELS_API_KEY'),
                'rate_limit': {'requests': 200, 'period': 3600}
            },
            'unsplash': {
                'api_key': os.getenv('UNSPLASH_API_KEY'),
                'rate_limit': {'requests': 50, 'period': 3600}
            },
            'elevenlabs': {
                'api_key': os.getenv('ELEVENLABS_API_KEY'),
                'rate_limit': {'requests': 100, 'period': 3600}
            },
            'huggingface': {
                'api_key': os.getenv('HF_API_KEY'),
                'rate_limit': {'requests': 30, 'period': 3600}
            },
            'cohere': {
                'api_key': os.getenv('COHERE_API_KEY'),
                'rate_limit': {'requests': 100, 'period': 60}
            }
        }
    
    def _load_yaml_config(self, config_path: str):
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
            # Update configuration
            # ... implementation based on YAML structure
    
    @property
    def use_mcp(self) -> bool:
        """Check if any module is using MCP"""
        return any(
            module.provider_type == ProviderType.MCP 
            for module in self.modules.values()
        )
