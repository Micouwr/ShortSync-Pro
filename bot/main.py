#!/usr/bin/env python3
"""
ShortSync Pro - Main Entry Point
Professional YouTube Shorts Automation Bot with full production features
"""

import asyncio
import signal
import sys
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

from bot.config import Config
from bot.core.state_manager import StateManager
from bot.core.job_queue import JobQueue
from bot.core.enhanced_pipeline import EnhancedPipeline
from bot.database.manager import DatabaseManager
from bot.core.health import HealthChecker
from bot.core.config_manager import ConfigManager
from bot.license.manager import LicenseManager
from bot.monitoring.metrics import MetricsCollector
from bot.notifications.notification_manager import NotificationManager
from bot.utils.cleanup import CleanupManager
from bot.utils.backup import BackupManager
from bot.web.dashboard import DashboardServer
from bot.cli import CLI

def setup_logging(config: Config) -> logging.Logger:
    """
    Setup comprehensive logging system
    """
    # Create logs directory if it doesn't exist
    config.dirs['logs'].mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (rotating)
    from logging.handlers import RotatingFileHandler
    log_file = config.dirs['logs'] / 'shortsync.log'
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=10
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Error file handler
    error_file = config.dirs['logs'] / 'error.log'
    error_handler = RotatingFileHandler(
        error_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    logger.addHandler(error_handler)
    
    # SQLAlchemy logger (if using database)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    return logger

async def shutdown(
    signal_name: str,
    loop: asyncio.AbstractEventLoop,
    pipeline: Optional[EnhancedPipeline] = None,
    dashboard: Optional[DashboardServer] = None,
    health_checker: Optional[HealthChecker] = None,
    logger: Optional[logging.Logger] = None
):
    """
    Graceful shutdown handler
    """
    if logger:
        logger.info(f"🛑 Received {signal_name}, initiating graceful shutdown...")
    
    # Stop dashboard if running
    if dashboard:
        logger.info("Stopping dashboard server...")
        await dashboard.stop()
    
    # Stop health checker if running
    if health_checker:
        logger.info("Stopping health checker...")
        await health_checker.stop()
    
    # Stop pipeline if running
    if pipeline:
        logger.info("Stopping pipeline...")
        await pipeline.stop()
    
    # Cancel all running tasks
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    
    if tasks:
        logger.info(f"Cancelling {len(tasks)} running tasks...")
        for task in tasks:
            task.cancel()
        
        # Wait for tasks to complete cancellation
        await asyncio.gather(*tasks, return_exceptions=True)
    
    # Stop event loop
    loop.stop()
    
    if logger:
        logger.info("✅ Shutdown complete")

async def initialize_components(config: Config, logger: logging.Logger) -> dict:
    """
    Initialize all bot components
    """
    components = {}
    
    try:
        # 1. Initialize Database
        logger.info("📦 Initializing database...")
        db_manager = DatabaseManager(config)
        await db_manager.initialize()
        components['db_manager'] = db_manager
        
        # 2. Initialize License Manager
        logger.info("🔑 Checking license...")
        license_manager = LicenseManager(config)
        license_info = license_manager.check_license()
        
        if not license_info['valid']:
            logger.error(f"❌ License error: {license_info.get('error', 'Unknown error')}")
            if license_info.get('required_tier'):
                logger.error(f"   Required tier: {license_info['required_tier']}")
            # In production, you might want to exit here
            # For now, continue with limited features
        
        components['license_manager'] = license_manager
        
        # 3. Initialize State Manager
        logger.info("💾 Initializing state manager...")
        state_manager = StateManager(config)
        components['state_manager'] = state_manager
        
        # 4. Initialize Job Queue
        logger.info("📋 Initializing job queue...")
        job_queue = JobQueue(config)
        components['job_queue'] = job_queue
        
        # 5. Initialize Enhanced Pipeline
        logger.info("⚙️ Initializing enhanced pipeline...")
        pipeline = EnhancedPipeline(config, state_manager, job_queue)
        await pipeline.initialize_providers()
        components['pipeline'] = pipeline
        
        # 6. Initialize Metrics Collector
        logger.info("📊 Initializing metrics collector...")
        metrics = MetricsCollector(config)
        components['metrics'] = metrics
        
        # 7. Initialize Notification Manager
        logger.info("🔔 Initializing notification manager...")
        notification_manager = NotificationManager(config)
        await notification_manager.initialize()
        components['notification_manager'] = notification_manager
        
        # 8. Initialize Health Checker
        logger.info("🏥 Initializing health checker...")
        health_checker = HealthChecker(config)
        components['health_checker'] = health_checker
        
        # 9. Initialize Config Manager (if config file exists)
        config_path = Path('config.yaml')
        if config_path.exists():
            logger.info("⚙️ Loading configuration from config.yaml...")
            config_manager = ConfigManager(config_path)
            config_manager.load_config()
            components['config_manager'] = config_manager
        
        # 10. Initialize Cleanup Manager
        logger.info("🧹 Initializing cleanup manager...")
        cleanup_manager = CleanupManager(config)
        components['cleanup_manager'] = cleanup_manager
        
        # 11. Initialize Backup Manager
        logger.info("💾 Initializing backup manager...")
        backup_manager = BackupManager(config)
        components['backup_manager'] = backup_manager
        
        logger.info("✅ All components initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize components: {e}", exc_info=True)
        raise
    
    return components

async def schedule_background_tasks(
    components: dict,
    config: Config,
    logger: logging.Logger
):
    """
    Schedule background maintenance tasks
    """
    try:
        # Schedule cleanup (daily at 3 AM)
        asyncio.create_task(
            components['cleanup_manager'].schedule_cleanup(hour=3, minute=0)
        )
        
        # Schedule backup (weekly on Sunday at 2 AM)
        asyncio.create_task(
            components['backup_manager'].schedule_backup(
                day_of_week=6,  # Sunday
                hour=2,
                minute=0
            )
        )
        
        # Schedule metrics reporting (every hour)
        asyncio.create_task(
            components['metrics'].schedule_reporting(interval_hours=1)
        )
        
        logger.info("✅ Background tasks scheduled")
        
    except Exception as e:
        logger.error(f"❌ Failed to schedule background tasks: {e}")

async def start_dashboard(
    config: Config,
    components: dict,
    logger: logging.Logger
) -> Optional[DashboardServer]:
    """
    Start web dashboard if enabled
    """
    try:
        # Check if dashboard is enabled in config
        if not config.get('dashboard', {}).get('enabled', True):
            logger.info("🌐 Dashboard disabled in configuration")
            return None
        
        dashboard_host = config.get('dashboard', {}).get('host', '0.0.0.0')
        dashboard_port = config.get('dashboard', {}).get('port', 8080)
        
        logger.info(f"🌐 Starting dashboard on {dashboard_host}:{dashboard_port}...")
        
        dashboard = DashboardServer(
            host=dashboard_host,
            port=dashboard_port,
            config=config,
            components=components
        )
        
        await dashboard.start()
        
        logger.info(f"✅ Dashboard started at http://{dashboard_host}:{dashboard_port}")
        
        return dashboard
        
    except Exception as e:
        logger.error(f"❌ Failed to start dashboard: {e}")
        return None

async def run_pipeline(
    pipeline: EnhancedPipeline,
    logger: logging.Logger,
    check_interval: int = 60
):
    """
    Run the main pipeline
    """
    try:
        logger.info("🚀 Starting pipeline...")
        
        # Start pipeline
        pipeline_task = asyncio.create_task(pipeline.start())
        
        # Monitor pipeline
        while True:
            await asyncio.sleep(check_interval)
            
            # Check if pipeline is still running
            if pipeline_task.done():
                try:
                    pipeline_task.result()  # Check for exceptions
                except Exception as e:
                    logger.error(f"❌ Pipeline stopped with error: {e}")
                    break
                
                logger.warning("⚠️ Pipeline task completed, restarting...")
                pipeline_task = asyncio.create_task(pipeline.start())
            
            # Log pipeline status periodically
            active_jobs = len(pipeline.state.state.get('active_jobs', {}))
            if active_jobs > 0:
                logger.info(f"📊 Pipeline status: {active_jobs} active jobs")
                
    except asyncio.CancelledError:
        logger.info("Pipeline monitoring cancelled")
        raise
        
    except Exception as e:
        logger.error(f"❌ Pipeline error: {e}", exc_info=True)
        raise

async def main() -> int:
    """
    Main entry point for ShortSync Pro
    """
    start_time = time.time()
    exit_code = 0
    dashboard = None
    pipeline = None
    health_checker = None
    
    try:
        # Parse command line arguments
        import argparse
        parser = argparse.ArgumentParser(description='ShortSync Pro - YouTube Automation Bot')
        parser.add_argument('--config', type=str, default='config.yaml', help='Configuration file path')
        parser.add_argument('--dev', action='store_true', help='Enable development mode')
        parser.add_argument('--debug', action='store_true', help='Enable debug logging')
        parser.add_argument('--no-dashboard', action='store_true', help='Disable web dashboard')
        parser.add_argument('--health-port', type=int, default=8081, help='Health check server port')
        args = parser.parse_args()
        
        # Load configuration
        config = Config(config_path=args.config if Path(args.config).exists() else None)
        
        # Set development mode
        if args.dev:
            config.environment = 'development'
            config.debug = True
        
        # Setup logging
        logger = setup_logging(config)
        
        if args.debug:
            logger.setLevel(logging.DEBUG)
            logger.debug("🔍 Debug logging enabled")
        
        # Banner
        logger.info("\n" + "="*60)
        logger.info("🚀 ShortSync Pro - Professional YouTube Automation Bot")
        logger.info(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"🏷️ Version: 2.0.0")
        logger.info(f"⚙️ Environment: {config.environment}")
        logger.info("="*60 + "\n")
        
        # Initialize components
        components = await initialize_components(config, logger)
        
        # Get key components
        pipeline = components.get('pipeline')
        health_checker = components.get('health_checker')
        
        if not pipeline:
            logger.error("❌ Failed to initialize pipeline")
            return 1
        
        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        signals = (signal.SIGTERM, signal.SIGINT)
        
        for sig in signals:
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(
                    shutdown(
                        signal_name=s.name,
                        loop=loop,
                        pipeline=pipeline,
                        dashboard=dashboard,
                        health_checker=health_checker,
                        logger=logger
                    )
                )
            )
        
        # Schedule background tasks
        await schedule_background_tasks(components, config, logger)
        
        # Start health check server
        if health_checker:
            health_port = args.health_port
            health_server_task = asyncio.create_task(
                health_checker.run_health_server(port=health_port)
            )
            logger.info(f"🏥 Health server started on port {health_port}")
        
        # Start dashboard (if not disabled)
        if not args.no_dashboard:
            dashboard = await start_dashboard(config, components, logger)
        
        # Send startup notification
        notification_manager = components.get('notification_manager')
        if notification_manager:
            await notification_manager.send_notification(
                title="ShortSync Pro Started",
                message=f"Bot started successfully at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                level="success"
            )
        
        # Run pipeline
        await run_pipeline(pipeline, logger)
        
    except KeyboardInterrupt:
        logger.info("\n👋 Bot stopped by user")
        exit_code = 0
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        exit_code = 1
        
        # Send error notification
        try:
            notification_manager = components.get('notification_manager')
            if notification_manager:
                await notification_manager.send_notification(
                    title="ShortSync Pro Fatal Error",
                    message=f"Bot crashed with error: {str(e)[:200]}",
                    level="critical"
                )
        except:
            pass  # Don't crash if notification fails
        
    finally:
        # Calculate runtime
        runtime = time.time() - start_time
        hours, remainder = divmod(runtime, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if 'logger' in locals():
            logger.info("\n" + "="*60)
            logger.info(f"🛑 Bot shutting down")
            logger.info(f"⏱️  Runtime: {int(hours)}h {int(minutes)}m {int(seconds)}s")
            logger.info("="*60)
        
        # Ensure all components are properly cleaned up
        try:
            if pipeline:
                await pipeline.stop()
            if dashboard:
                await dashboard.stop()
            if health_checker:
                await health_checker.stop()
        except:
            pass
    
    return exit_code

def run_cli():
    """
    Run the CLI interface
    """
    cli = CLI()
    cli.run()

if __name__ == "__main__":
    # Check if running in CLI mode
    if len(sys.argv) > 1 and sys.argv[1] in ['--cli', '-c']:
        run_cli()
    else:
        # Run the main bot
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
