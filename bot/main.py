# bot/main.py
"""
Main entry point for YouTube Automation Bot
"""

import asyncio
import signal
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from bot.config import Config
from bot.core.state_manager import StateManager
from bot.core.job_queue import JobQueue
from bot.core.enhanced_pipeline import EnhancedPipeline

def setup_logging(config: Config):
    """Setup comprehensive logging"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler
    log_file = config.dirs['logs'] / 'bot.log'
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    # Error file handler
    error_file = config.dirs['logs'] / 'error.log'
    error_handler = RotatingFileHandler(
        error_file, maxBytes=5*1024*1024, backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_format)
    logger.addHandler(error_handler)
    
    return logger

async def shutdown(signal, loop, pipeline, logger):
    """Graceful shutdown"""
    logger.info(f"Received signal {signal.name}, shutting down...")
    
    # Cancel all tasks
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()
    
    logger.info("Shutdown complete")

async def main():
    """Main entry point"""
    # Load configuration
    config = Config()
    
    # Setup logging
    logger = setup_logging(config)
    logger.info("🚀 YouTube Automation Bot Starting...")
    logger.info(f"Configuration: MCP enabled={config.use_mcp}")
    
    try:
        # Initialize core components
        state_manager = StateManager(config)
        job_queue = JobQueue(config)
        
        # Create and initialize pipeline
        pipeline = EnhancedPipeline(config, state_manager, job_queue)
        await pipeline.initialize_providers()
        
        # Setup signal handlers
        loop = asyncio.get_running_loop()
        signals = (signal.SIGTERM, signal.SIGINT)
        for sig in signals:
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(shutdown(s, loop, pipeline, logger))
            )
        
        # Start the pipeline
        logger.info("Starting pipeline...")
        await pipeline.start()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
