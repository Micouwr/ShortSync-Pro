"""
Health checking and monitoring
"""

import asyncio
import aiohttp
from aiohttp import web
from typing import Dict, Optional
import psutil
import socket
from datetime import datetime

class HealthChecker:
    """Health checking and monitoring service"""
    
    def __init__(self, config):
        self.config = config
        self.server = None
        self.app = web.Application()
        self.setup_routes()
    
    def setup_routes(self):
        """Setup health check routes"""
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/ready', self.ready_check)
        self.app.router.add_get('/metrics', self.metrics)
        self.app.router.add_get('/info', self.system_info)
    
    async def health_check(self, request):
        """Health check endpoint"""
        health_status = await self.check_system_health()
        
        if health_status['status'] == 'healthy':
            return web.json_response(health_status)
        else:
            return web.json_response(health_status, status=503)
    
    async def ready_check(self, request):
        """Readiness check endpoint"""
        ready_status = await self.check_readiness()
        
        if ready_status['ready']:
            return web.json_response(ready_status)
        else:
            return web.json_response(ready_status, status=503)
    
    async def metrics(self, request):
        """Metrics endpoint"""
        metrics = await self.collect_metrics()
        return web.json_response(metrics)
    
    async def system_info(self, request):
        """System information endpoint"""
        info = await self.get_system_info()
        return web.json_response(info)
    
    async def check_system_health(self) -> Dict:
        """Check overall system health"""
        checks = {}
        
        # Disk space check
        try:
            disk = psutil.disk_usage(self.config.dirs['data'])
            checks['disk_space'] = {
                'total_gb': disk.total / (1024**3),
                'used_gb': disk.used / (1024**3),
                'free_gb': disk.free / (1024**3),
                'percent_used': disk.percent,
                'healthy': disk.percent < 90
            }
        except Exception as e:
            checks['disk_space'] = {'healthy': False, 'error': str(e)}
        
        # Memory check
        try:
            memory = psutil.virtual_memory()
            checks['memory'] = {
                'total_gb': memory.total / (1024**3),
                'available_gb': memory.available / (1024**3),
                'percent_used': memory.percent,
                'healthy': memory.percent < 90
            }
        except Exception as e:
            checks['memory'] = {'healthy': False, 'error': str(e)}
        
        # CPU check
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            checks['cpu'] = {
                'percent': cpu_percent,
                'healthy': cpu_percent < 80
            }
        except Exception as e:
            checks['cpu'] = {'healthy': False, 'error': str(e)}
        
        # Check if all checks passed
        all_healthy = all(check.get('healthy', False) for check in checks.values())
        
        return {
            'status': 'healthy' if all_healthy else 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'checks': checks
        }
    
    async def check_readiness(self) -> Dict:
        """Check if system is ready to accept traffic"""
        # Add checks for dependencies (database, APIs, etc.)
        ready = True
        reasons = []
        
        # Check if data directory is accessible
        try:
            test_file = self.config.dirs['data'] / '.test'
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            ready = False
            reasons.append(f"Data directory not accessible: {e}")
        
        # Check network connectivity
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=5)
        except Exception as e:
            ready = False
            reasons.append(f"Network connectivity issue: {e}")
        
        return {
            'ready': ready,
            'timestamp': datetime.now().isoformat(),
            'reasons': reasons if not ready else []
        }
    
    async def collect_metrics(self) -> Dict:
        """Collect system and application metrics"""
        import time
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(self.config.dirs['data'])
        
        # Application metrics (you would track these in your app)
        app_metrics = {
            'jobs_processed': 0,  # Would come from your pipeline
            'jobs_failed': 0,
            'jobs_queued': 0,
            'videos_created': 0,
            'videos_uploaded': 0,
            'avg_processing_time': 0
        }
        
        return {
            'timestamp': datetime.now().isoformat(),
            'system': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024**3)
            },
            'application': app_metrics
        }
    
    async def get_system_info(self) -> Dict:
        """Get system information"""
        import platform
        
        return {
            'system': {
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'hostname': socket.gethostname(),
                'processor': platform.processor()
            },
            'application': {
                'name': 'ShortSync Pro',
                'version': '2.0.0',
                'environment': self.config.environment
            },
            'paths': {
                'data_dir': str(self.config.dirs['data']),
                'log_dir': str(self.config.dirs['logs']),
                'output_dir': str(self.config.dirs['output'])
            }
        }
    
    async def run_health_server(self, host: str = '0.0.0.0', port: int = 8081):
        """Run the health check server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        self.server = runner
        
        # Keep running
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour
    
    async def stop(self):
        """Stop the health check server"""
        if self.server:
            await self.server.cleanup()
