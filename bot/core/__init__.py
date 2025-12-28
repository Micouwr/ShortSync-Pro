"""
Core framework package for ShortSync Pro.

This package contains the fundamental building blocks:
- State management
- Job queue system
- Pipeline orchestration
- Health monitoring
- Rate limiting and circuit breaking
- Configuration management
"""

__all__ = [
    'circuit_breaker',
    'config_manager',
    'enhanced_pipeline',
    'health',
    'state_manager',
    'job_queue',
    'rate_limiter',
    'metrics'
]

# Package version
__version__ = "1.0.0"

def initialize_core():
    """Initialize all core components."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Core framework package initialized")
    return True
