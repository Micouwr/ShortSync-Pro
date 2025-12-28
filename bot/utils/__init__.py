"""
Utilities package for ShortSync Pro.

This package contains utility functions and helpers used throughout the system:
- File system utilities
- Video processing utilities
- Text processing and formatting
- API interaction helpers
- Cleanup and maintenance utilities
"""

__all__ = [
    'cleanup',
    'youtube_api',
    'video_utils',
    'text_utils',
    'file_utils',
    'validation'
]

# Utilities package version
__version__ = "1.0.0"

# Export common utility functions
from .cleanup import cleanup_temp_files, cleanup_old_outputs
from .youtube_api import YouTubeAPIHelper, validate_youtube_credentials
from .file_utils import ensure_directory, safe_filename, get_file_hash

def initialize_utilities():
    """Initialize utilities package."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Utilities package initialized")
    
    # Create necessary utility directories
    from pathlib import Path
    temp_dirs = ['temp', 'temp/video', 'temp/audio', 'temp/images']
    
    for dir_name in temp_dirs:
        dir_path = Path(dir_name)
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory exists: {dir_path}")
    
    return True

# Package metadata
PACKAGE_NAME = "shortsync-utilities"
DESCRIPTION = "Utility functions for ShortSync Pro"

def get_utility_functions():
    """Get information about available utility functions."""
    return {
        'package': PACKAGE_NAME,
        'version': __version__,
        'description': DESCRIPTION,
        'categories': {
            'cleanup': 'File cleanup and maintenance utilities',
            'youtube': 'YouTube API interaction helpers',
            'video': 'Video processing utilities',
            'text': 'Text processing and formatting',
            'files': 'File system utilities',
            'validation': 'Data validation utilities'
        }
    }
