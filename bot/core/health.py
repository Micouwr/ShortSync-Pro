# bot/core/health.py
"""
Health check and metrics collection.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Dict, Any
import time

@dataclass
class Metrics:
    jobs_started: int = 0
    jobs_completed: int = 0
    jobs_failed: int = 0
    api_calls: Dict[str, int] = field(default_factory=dict)
    average_processing_time: float = 0.0

    def increment_job_started(self):
        self.jobs_started += 1
    
    def increment_job_completed(self):
        self.jobs_completed += 1
    
    def increment_job_failed(self):
        self.jobs_failed += 1
    
    def record_api_call(self, api_name: str):
        self.api_calls[api_name] = self.api_calls.get(api_name, 0) + 1

class HealthChecker:
    def __init__(self, config):
        self.config = config
        self.metrics = Metrics()
        self.start_time = time.time()
    
    def get_uptime(self) -> float:
        return time.time() - self.start_time
    
    def get_health(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "uptime": self.get_uptime(),
            "metrics": {
                "jobs_started": self.metrics.jobs_started,
                "jobs_completed": self.metrics.jobs_completed,
                "jobs_failed": self.metrics.jobs_failed,
                "api_calls": self.metrics.api_calls,
                "job_success_rate": self.metrics.jobs_completed / max(self.metrics.jobs_started, 1)
            }
        }
    
    async def run_health_server(self, host: str = "0.0.0.0", port: int = 8080):
        """Run a simple HTTP server for health checks."""
        from aiohttp import web
        
        async def health_handler(request):
            return web.json_response(self.get_health())
        
        app = web.Application()
        app.router.add_get('/health', health_handler)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        print(f"Health check server running on http://{host}:{port}/health")
        
        # Keep the server running
        await asyncio.Event().wait()
