# bot/core/circuit_breaker.py
"""
Circuit breaker for external API calls.
"""

import asyncio
import time
from contextlib import contextmanager
from typing import Optional

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_failure_time: Optional[float] = None
    
    async def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            # Check if recovery timeout has passed
            if self.last_failure_time and (time.time() - self.last_failure_time) > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerError("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                # Successful call in HALF_OPEN state, reset
                self.reset()
            return result
        except Exception as e:
            self._record_failure()
            raise e
    
    def _record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
    
    def reset(self):
        self.failures = 0
        self.state = "CLOSED"
        self.last_failure_time = None

class CircuitBreakerError(Exception):
    pass

# Example usage in a provider:
# circuit_breaker = CircuitBreaker()
# result = await circuit_breaker.call(api_function, arg1, arg2)
