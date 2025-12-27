# bot/providers/base.py
"""
Abstract base classes for all providers.
Enables easy MCP integration later.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path
import asyncio

@dataclass
class Trend:
    """Trend data structure"""
    topic: str
    score: float
    category: str
    source: str
    metadata: Dict[str, Any] = None

@dataclass
class Script:
    """Script data structure"""
    title: str
    content: str
    duration_seconds: int
    metadata: Dict[str, Any] = None

@dataclass
class Asset:
    """Asset data structure"""
    url: str
    type: str  # video, image, audio
    license: str
    duration_seconds: Optional[int] = None
    metadata: Dict[str, Any] = None

class BaseTrendProvider(ABC):
    """Abstract base class for trend providers"""
    
    @abstractmethod
    async def get_trends(self, category: Optional[str] = None, 
                        limit: int = 10) -> List[Trend]:
        """Get trending topics"""
        pass
    
    @abstractmethod
    async def validate_trend(self, trend: Trend) -> Dict[str, Any]:
        """Validate/Research a trend"""
        pass

class BaseScriptProvider(ABC):
    """Abstract base class for script providers"""
    
    @abstractmethod
    async def generate_script(self, topic: str, 
                            duration_seconds: int = 45) -> Script:
        """Generate a script for a topic"""
        pass
    
    @abstractmethod
    async def improve_script(self, script: Script) -> Script:
        """Improve an existing script"""
        pass

class BaseFactCheckProvider(ABC):
    """Abstract base class for fact checking (MCP-ready)"""
    
    @abstractmethod
    async def fact_check(self, claim: str) -> Dict[str, Any]:
        """Check the validity of a claim"""
        pass
    
    @abstractmethod
    async def get_sources(self, topic: str) -> List[Dict[str, str]]:
        """Get authoritative sources for a topic"""
        pass

class BaseAssetProvider(ABC):
    """Abstract base class for asset providers"""
    
    @abstractmethod
    async def search_videos(self, query: str, 
                          duration_range: tuple = (3, 10),
                          limit: int = 5) -> List[Asset]:
        """Search for video assets"""
        pass
    
    @abstractmethod
    async def search_images(self, query: str, 
                          limit: int = 10) -> List[Asset]:
        """Search for image assets"""
        pass

class BaseVoiceoverProvider(ABC):
    """Abstract base class for voiceover providers"""
    
    @abstractmethod
    async def generate_voiceover(self, text: str,
                               voice_id: str = "default",
                               output_path: Path = None) -> Path:
        """Generate voiceover from text"""
        pass

class BaseVideoProvider(ABC):
    """Abstract base class for video assembly"""
    
    @abstractmethod
    async def assemble_video(self, script: Script,
                           voiceover_path: Path,
                           assets: List[Asset],
                           output_path: Path = None) -> Path:
        """Assemble video from components"""
        pass
