"""
ShortSync Pro - Professional YouTube Shorts Automation Bot

A modular, scalable system for creating and managing YouTube Shorts content
with human quality control and anti-AI-slop protection.

Features:
- Trend detection using free APIs
- Multi-AI script generation with quality checks
- Professional thumbnail creation
- Voiceover generation
- Video assembly
- Human approval system
- Automatic YouTube upload
- Multi-platform syndication
"""

__version__ = "2.0.0"
__author__ = "ShortSync Pro"
__license__ = "Business Source License 1.1"
__copyright__ = "Copyright (c) 2024 ShortSync Pro"

# Version info tuple
VERSION_INFO = (2, 0, 0)

# Package metadata
PACKAGE_NAME = "shortsync-pro"
DESCRIPTION = "Professional YouTube Shorts Automation Bot"
URL = "https://github.com/shortsync/shortsync-pro"
DOCS_URL = "https://docs.shortsync.pro"

# Optional: Package-level logger
import logging
logger = logging.getLogger(__name__)

def get_version():
    """Get the version string."""
    return __version__

def initialize_package():
    """Initialize the package - called when needed."""
    logger.info(f"Initializing {PACKAGE_NAME} v{__version__}")
    return True

# This makes the package importable
__all__ = [
    '__version__',
    '__author__',
    'get_version',
    'initialize_package',
]

# Optional: Print version info when imported (useful for debugging)
if __name__ == "__main__":
    print(f"{PACKAGE_NAME} v{__version__}")
    print(f"Author: {__author__}")
    print(f"License: {__license__}")
