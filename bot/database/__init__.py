"""
Database package for ShortSync Pro.

This package contains database management components:
- Database connection management
- Schema definition and migrations
- Data models for videos, jobs, and analytics
- Query utilities and data access patterns
"""

__all__ = [
    'manager',
    'models',
    'migrations',
    'queries'
]

# Database package version
__version__ = "1.0.0"

# Export common database components for easy access
from .manager import DatabaseManager
from .models import Video, Job, Channel, Analytics

def initialize_database():
    """Initialize database package."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Database package initialized")
    return True

# Package metadata
PACKAGE_NAME = "shortsync-database"
DESCRIPTION = "Database management for ShortSync Pro"

def get_database_info():
    """Get database package information."""
    return {
        'name': PACKAGE_NAME,
        'version': __version__,
        'description': DESCRIPTION
    }
