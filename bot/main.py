#!/usr/bin/env python3
"""
ShortSync Pro - Minimal Working Version

A simplified main entry point that works with minimal dependencies.
We'll build up complexity as we add more components.
"""

import asyncio
import signal
import sys
import logging
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

# Import what we have
try:
    from bot.config import get_config, Config
except ImportError as e:
    print(f"ERROR: Importing config failed: {e}")
    print("Make sure bot/__init__.py and bot/config.py exist")
    sys.exit(1)

def setup_logging(config: Optional[Config] = None) -> logging.Logger:
    """
    Simple logging setup
    """
    # Create logs directory if needed
    if config and hasattr(config, 'dirs') and 'logs' in config.dirs:
        config.dirs['logs'].mkdir(parents=True, exist_ok=True)
        log_file = config.dirs['logs'] / 'shortsync.log'
    else:
        # Default logs directory
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / 'shortsync.log'
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding='utf-8')
        ]
    )
    
    logger = logging.getLogger(__name__)
    return logger

async def shutdown(signal_name: str, logger: logging.Logger):
    """
    Simple graceful shutdown
    """
    logger.info(f"Received {signal_name}, shutting down...")
    
    # Cancel all running tasks
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    
    if tasks:
        logger.info(f"Cancelling {len(tasks)} running tasks...")
        for task in tasks:
            task.cancel()
        
        # Wait for tasks to complete cancellation
        await asyncio.gather(*tasks, return_exceptions=True)
    
    logger.info("Shutdown complete")

async def initialize_basic_components(config: Config, logger: logging.Logger) -> dict:
    """
    Initialize only the components we have
    """
    components = {}
    
    try:
        logger.info("Initializing basic components...")
        
        # We'll add components as we create them
        # For now, just return empty dict
        
        logger.info("Basic components initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        # Don't raise - we want to continue with what we have
    
    return components

async def run_basic_pipeline(config: Config, logger: logging.Logger):
    """
    Run a simple test pipeline
    """
    try:
        logger.info("Starting basic pipeline...")
        
        # Simple test loop
        iteration = 0
        while True:
            iteration += 1
            logger.info(f"Pipeline iteration {iteration}")
            logger.info(f"   Environment: {config.environment}")
            logger.info(f"   Debug mode: {config.debug}")
            
            # Log directory info
            if hasattr(config, 'dirs'):
                for name, path in config.dirs.items():
                    if path.exists():
                        logger.debug(f"   Directory {name}: {path}")
            
            # Check for stop condition (every 5 iterations)
            if iteration >= 5:
                logger.info("Test completed successfully")
                break
            
            # Simulate work
            await asyncio.sleep(2)
            
    except asyncio.CancelledError:
        logger.info("Pipeline cancelled")
        raise
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        raise

async def main() -> int:
    """
    Main entry point - minimal working version
    """
    start_time = time.time()
    exit_code = 0
    logger = None
    
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='ShortSync Pro - YouTube Automation Bot')
        parser.add_argument('--config', type=str, help='Configuration file path (optional)')
        parser.add_argument('--dev', action='store_true', help='Enable development mode')
        parser.add_argument('--debug', action='store_true', help='Enable debug logging')
        parser.add_argument('--test', action='store_true', help='Run in test mode (limited iterations)')
        args = parser.parse_args()
        
        # Load configuration
        config = get_config(args.config if args.config else None)
        
        # Override config if dev mode
        if args.dev:
            config.environment = 'development'
            config.debug = True
        
        # Setup logging
        logger = setup_logging(config)
        
        if args.debug:
            logger.setLevel(logging.DEBUG)
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug("Debug logging enabled")
        
        # Banner
        logger.info("\n" + "=" * 60)
        logger.info("ShortSync Pro - YouTube Automation Bot")
        logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Version: 1.0.0")
        logger.info(f"Environment: {config.environment}")
        logger.info(f"Debug: {config.debug}")
        logger.info("=" * 60 + "\n")
        
        # Log config info
        logger.info("Configuration loaded:")
        logger.info(f"   Base directory: {config.base_dir}")
        logger.info(f"   Data directory: {config.dirs.get('data', 'Not set')}")
        logger.info(f"   Log directory: {config.dirs.get('logs', 'Not set')}")
        
        # Check API keys
        if hasattr(config, 'apis'):
            missing_apis = []
            for api_name, api_config in config.apis.items():
                api_key = api_config.get('api_key', '')
                if not api_key:
                    missing_apis.append(api_name)
            
            if missing_apis:
                logger.warning(f"Missing API keys: {', '.join(missing_apis)}")
            else:
                logger.info("All API keys configured")
        
        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        
        def signal_handler(sig):
            asyncio.create_task(shutdown(signal.Signals(sig).name, logger))
        
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
        
        # Initialize components
        components = await initialize_basic_components(config, logger)
        
        logger.info("Initialization complete")
        logger.info("\n" + "-" * 60)
        
        # Run pipeline
        if args.test:
            logger.info("Running in test mode (5 iterations)")
            await run_basic_pipeline(config, logger)
        else:
            logger.info("Bot ready. Press Ctrl+C to stop.")
            # Just keep running
            while True:
                await asyncio.sleep(1)
        
    except KeyboardInterrupt:
        if logger:
            logger.info("\nBot stopped by user")
        exit_code = 0
        
    except Exception as e:
        if logger:
            logger.error(f"Fatal error: {e}", exc_info=True)
        else:
            print(f"Fatal error: {e}")
        exit_code = 1
        
    finally:
        # Calculate runtime
        runtime = time.time() - start_time
        hours, remainder = divmod(runtime, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if logger:
            logger.info("\n" + "=" * 60)
            logger.info(f"Bot shutting down")
            logger.info(f"Runtime: {int(hours)}h {int(minutes)}m {int(seconds)}s")
            logger.info("=" * 60)
    
    return exit_code

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nBot stopped")
        sys.exit(0)
    except Exception as e:
        print(f"Startup error: {e}")
        sys.exit(1)
