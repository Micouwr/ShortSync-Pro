"""
Job queue system for ShortSync Pro.

Manages asynchronous job processing with priority queues,
rate limiting, and job tracking.
"""

import asyncio
import uuid
import heapq
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)

class JobPriority(Enum):
    """Job priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3

class JobStatus(Enum):
    """Job status states"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass(order=True)
class PrioritizedJob:
    """Job with priority for heap queue"""
    priority: int
    timestamp: datetime
    job_id: str = field(compare=False)
    job_data: Dict[str, Any] = field(compare=False)

@dataclass
class JobResult:
    """Result of a job execution"""
    job_id: str
    status: JobStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: Optional[float] = None  # seconds

class JobType(Enum):
    """Types of jobs that can be processed"""
    TREND_RESEARCH = "trend_research"
    SCRIPT_GENERATION = "script_generation"
    ASSET_GATHERING = "asset_gathering"
    VOICEOVER_GENERATION = "voiceover_generation"
    VIDEO_ASSEMBLY = "video_assembly"
    THUMBNAIL_GENERATION = "thumbnail_generation"
    QUALITY_CHECK = "quality_check"
    YOUTUBE_UPLOAD = "youtube_upload"
    PIPELINE_EXECUTION = "pipeline_execution"

class JobQueue:
    """Main job queue management class"""
    
    def __init__(self, config, db_manager):
        self.config = config
        self.db = db_manager
        
        # Queue storage
        self.priority_queue: List[PrioritizedJob] = []
        self.active_jobs: Dict[str, asyncio.Task] = {}
        self.job_results: Dict[str, JobResult] = {}
        self.job_callbacks: Dict[str, List[callable]] = {}
        
        # Rate limiting
        self.job_type_limits: Dict[JobType, Dict[str, Any]] = {
            JobType.TREND_RESEARCH: {"max_concurrent": 2, "per_hour": 50},
            JobType.SCRIPT_GENERATION: {"max_concurrent": 3, "per_hour": 100},
            JobType.ASSET_GATHERING: {"max_concurrent": 5, "per_hour": 200},
            JobType.VOICEOVER_GENERATION: {"max_concurrent": 2, "per_hour": 50},
            JobType.VIDEO_ASSEMBLY: {"max_concurrent": 2, "per_hour": 30},
            JobType.THUMBNAIL_GENERATION: {"max_concurrent": 3, "per_hour": 100},
            JobType.QUALITY_CHECK: {"max_concurrent": 3, "per_hour": 100},
            JobType.YOUTUBE_UPLOAD: {"max_concurrent": 1, "per_hour": 10},
            JobType.PIPELINE_EXECUTION: {"max_concurrent": 2, "per_hour": 20}
        }
        
        # Statistics
        self.job_counters: Dict[JobType, Dict[str, int]] = {}
        self.hourly_counters: Dict[JobType, List[datetime]] = {}
        
        # Control flags
        self.running = False
        self.processing_task: Optional[asyncio.Task] = None
        
        # State files
        self.queue_file = config.dirs['queue'] / 'job_queue.json'
        self.stats_file = config.dirs['queue'] / 'queue_stats.json'
        
        # Locks
        self.queue_lock = asyncio.Lock()
        self.stats_lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize job queue"""
        logger.info("Initializing job queue...")
        
        # Ensure queue directory exists
        self.config.dirs['queue'].mkdir(parents=True, exist_ok=True)
        
        # Initialize counters
        for job_type in JobType:
            self.job_counters[job_type] = {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0
            }
            self.hourly_counters[job_type] = []
        
        # Load saved queue state
        await self.load_queue_state()
        
        # Start queue processor
        self.running = True
        self.processing_task = asyncio.create_task(self._process_queue())
        
        logger.info("Job queue initialized")
        return self
    
    async def create_job(self, job_type: JobType, job_data: Dict[str, Any], 
                        priority: JobPriority = JobPriority.NORMAL,
                        metadata: Dict[str, Any] = None) -> str:
        """Create a new job and add to queue"""
        job_id = str(uuid.uuid4())
        
        # Prepare job data
        full_job_data = {
            "job_id": job_id,
            "job_type": job_type.value,
            "priority": priority.value,
            "data": job_data,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "status": JobStatus.PENDING.value
        }
        
        # Create prioritized job
        prioritized_job = PrioritizedJob(
            priority=priority.value,
            timestamp=datetime.utcnow(),
            job_id=job_id,
            job_data=full_job_data
        )
        
        # Add to queue
        async with self.queue_lock:
            heapq.heappush(self.priority_queue, prioritized_job)
            
            # Update counters
            self.job_counters[job_type]["total"] += 1
            
            # Save to database
            await self.db.save_job({
                "id": job_id,
                "type": job_type.value,
                "status": "pending",
                "data": json.dumps(full_job_data)
            })
        
        # Save queue state
        await self.save_queue_state()
        
        logger.info(f"Created job {job_id} of type {job_type.value} with priority {priority.value}")
        return job_id
    
    async def get_job(self, timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        """Get next job from queue with timeout"""
        try:
            async with asyncio.timeout(timeout):
                async with self.queue_lock:
                    if not self.priority_queue:
                        return None
                    
                    # Get highest priority job
                    prioritized_job = heapq.heappop(self.priority_queue)
                    job_data = prioritized_job.job_data
                    
                    # Check rate limits
                    job_type = JobType(job_data["job_type"])
                    if not await self._check_rate_limits(job_type):
                        # Put back in queue with delay
                        heapq.heappush(self.priority_queue, prioritized_job)
                        return None
                    
                    # Update status
                    job_data["status"] = JobStatus.PROCESSING.value
                    job_data["started_at"] = datetime.utcnow().isoformat()
                    
                    # Update hourly counter
                    self.hourly_counters[job_type].append(datetime.utcnow())
                    
                    # Update database
                    await self.db.update_job_status(
                        job_data["job_id"],
                        "processing",
                        {"started_at": job_data["started_at"]}
                    )
                    
                    # Save queue state
                    await self.save_queue_state()
                    
                    logger.debug(f"Retrieved job {job_data['job_id']} for processing")
                    return job_data
                    
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"Error getting job from queue: {e}")
            return None
    
    async def submit_job_result(self, job_id: str, result: JobResult):
        """Submit result for a completed job"""
        async with self.queue_lock:
            # Update job result
            self.job_results[job_id] = result
            
            # Update counters
            job_type = await self._get_job_type_for_id(job_id)
            if job_type:
                counter_key = result.status.value.lower()
                if counter_key in self.job_counters[job_type]:
                    self.job_counters[job_type][counter_key] += 1
            
            # Remove from active jobs if present
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
            
            # Update database
            db_result = None
            if result.result:
                db_result = {"result": result.result}
            
            await self.db.update_job_status(
                job_id,
                result.status.value,
                db_result,
                result.error
            )
        
        # Execute callbacks
        if job_id in self.job_callbacks:
            for callback in self.job_callbacks[job_id]:
                try:
                    await callback(result)
                except Exception as e:
                    logger.error(f"Error in job callback: {e}")
            del self.job_callbacks[job_id]
        
        # Save queue state
        await self.save_queue_state()
        
        logger.info(f"Job {job_id} completed with status {result.status.value}")
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or processing job"""
        async with self.queue_lock:
            # Check if job is in queue
            for i, prioritized_job in enumerate(self.priority_queue):
                if prioritized_job.job_id == job_id:
                    # Remove from queue
                    self.priority_queue.pop(i)
                    heapq.heapify(self.priority_queue)
                    
                    # Update result
                    result = JobResult(
                        job_id=job_id,
                        status=JobStatus.CANCELLED,
                        completed_at=datetime.utcnow()
                    )
                    self.job_results[job_id] = result
                    
                    # Update counters
                    job_type = await self._get_job_type_for_id(job_id)
                    if job_type:
                        self.job_counters[job_type]["cancelled"] += 1
                    
                    # Update database
                    await self.db.update_job_status(job_id, "cancelled")
                    
                    logger.info(f"Cancelled pending job {job_id}")
                    return True
            
            # Check if job is active
            if job_id in self.active_jobs:
                task = self.active_jobs[job_id]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                
                # Update result
                result = JobResult(
                    job_id=job_id,
                    status=JobStatus.CANCELLED,
                    completed_at=datetime.utcnow()
                )
                self.job_results[job_id] = result
                
                # Update counters
                job_type = await self._get_job_type_for_id(job_id)
                if job_type:
                    self.job_counters[job_type]["cancelled"] += 1
                
                # Update database
                await self.db.update_job_status(job_id, "cancelled")
                
                del self.active_jobs[job_id]
                logger.info(f"Cancelled active job {job_id}")
                return True
        
        logger.warning(f"Job {job_id} not found for cancellation")
        return False
    
    async def get_job_status(self, job_id: str) -> Optional[JobResult]:
        """Get status of a specific job"""
        # Check results first
        if job_id in self.job_results:
            return self.job_results[job_id]
        
        # Check if job is active
        if job_id in self.active_jobs:
            task = self.active_jobs[job_id]
            if task.done():
                try:
                    result = task.result()
                    return result
                except Exception as e:
                    return JobResult(
                        job_id=job_id,
                        status=JobStatus.FAILED,
                        error=str(e),
                        completed_at=datetime.utcnow()
                    )
            else:
                return JobResult(
                    job_id=job_id,
                    status=JobStatus.PROCESSING,
                    started_at=datetime.utcnow()
                )
        
        # Check if job is in queue
        async with self.queue_lock:
            for prioritized_job in self.priority_queue:
                if prioritized_job.job_id == job_id:
                    return JobResult(
                        job_id=job_id,
                        status=JobStatus.PENDING
                    )
        
        # Try to get from database
        try:
            job_data = await self.db.get_job(job_id)
            if job_data:
                status = JobStatus(job_data.get("status", "pending"))
                return JobResult(
                    job_id=job_id,
                    status=status,
                    result=job_data.get("result"),
                    error=job_data.get("error_message")
                )
        except Exception as e:
            logger.error(f"Error getting job status from database: {e}")
        
        return None
    
    async def get_queue_size(self) -> int:
        """Get current queue size"""
        async with self.queue_lock:
            return len(self.priority_queue)
    
    async def get_active_job_count(self) -> int:
        """Get number of active jobs"""
        return len(self.active_jobs)
    
    async def add_callback(self, job_id: str, callback: callable):
        """Add callback for job completion"""
        if job_id not in self.job_callbacks:
            self.job_callbacks[job_id] = []
        self.job_callbacks[job_id].append(callback)
    
    async def _process_queue(self):
        """Main queue processing loop"""
        logger.info("Starting queue processor...")
        
        while self.running:
            try:
                # Get next job
                job_data = await self.get_job(timeout=1.0)
                
                if job_data:
                    # Create processing task
                    job_id = job_data["job_id"]
                    task = asyncio.create_task(
                        self._execute_job(job_data),
                        name=f"job_{job_id}"
                    )
                    
                    # Store task
                    self.active_jobs[job_id] = task
                    
                    # Add done callback
                    task.add_done_callback(
                        lambda t, jid=job_id: asyncio.create_task(
                            self._handle_job_completion(t, jid)
                        )
                    )
                
                # Cleanup old results
                await self._cleanup_old_results()
                
                # Update statistics
                await self._update_statistics()
                
                # Small sleep to prevent busy looping
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in queue processor: {e}")
                await asyncio.sleep(1.0)
        
        logger.info("Queue processor stopped")
    
    async def _execute_job(self, job_data: Dict[str, Any]) -> JobResult:
        """Execute a job (to be overridden by pipeline)"""
        # This method should be overridden by the pipeline
        # that uses the job queue
        job_id = job_data["job_id"]
        job_type = JobType(job_data["job_type"])
        
        logger.warning(f"Job execution not implemented for {job_type.value}, returning mock result")
        
        # Simulate processing time
        await asyncio.sleep(0.5)
        
        return JobResult(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            result={"message": "Job executed successfully"},
            started_at=datetime.fromisoformat(job_data.get("started_at", datetime.utcnow().isoformat())),
            completed_at=datetime.utcnow()
        )
    
    async def _handle_job_completion(self, task: asyncio.Task, job_id: str):
        """Handle job completion"""
        try:
            result = task.result()
            await self.submit_job_result(job_id, result)
        except asyncio.CancelledError:
            # Job was cancelled
            result = JobResult(
                job_id=job_id,
                status=JobStatus.CANCELLED,
                completed_at=datetime.utcnow()
            )
            await self.submit_job_result(job_id, result)
        except Exception as e:
            # Job failed
            result = JobResult(
                job_id=job_id,
                status=JobStatus.FAILED,
                error=str(e),
                completed_at=datetime.utcnow()
            )
            await self.submit_job_result(job_id, result)
    
    async def _check_rate_limits(self, job_type: JobType) -> bool:
        """Check if job type is within rate limits"""
        limits = self.job_type_limits.get(job_type, {})
        
        # Check concurrent limit
        concurrent_count = sum(
            1 for job in self.active_jobs.values()
            if not job.done()
        )
        
        if concurrent_count >= limits.get("max_concurrent", 5):
            logger.debug(f"Concurrent limit reached for {job_type.value}")
            return False
        
        # Check hourly limit
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        hourly_count = sum(
            1 for timestamp in self.hourly_counters[job_type]
            if timestamp > hour_ago
        )
        
        if hourly_count >= limits.get("per_hour", 100):
            logger.debug(f"Hourly limit reached for {job_type.value}")
            return False
        
        return True
    
    async def _get_job_type_for_id(self, job_id: str) -> Optional[JobType]:
        """Get job type for a job ID"""
        # Check in queue
        async with self.queue_lock:
            for prioritized_job in self.priority_queue:
                if prioritized_job.job_id == job_id:
                    return JobType(prioritized_job.job_data["job_type"])
        
        # Check in results
        if job_id in self.job_results:
            # Need to track job type in results or query database
            pass
        
        # Query database
        try:
            job_data = await self.db.get_job(job_id)
            if job_data and job_data.get("type"):
                return JobType(job_data["type"])
        except Exception as e:
            logger.error(f"Error getting job type from database: {e}")
        
        return None
    
    async def _cleanup_old_results(self, hours_old: int = 24):
        """Cleanup old job results"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_old)
        
        async with self.queue_lock:
            # Cleanup results
            to_remove = []
            for job_id, result in self.job_results.items():
                if result.completed_at and result.completed_at < cutoff_time:
                    to_remove.append(job_id)
            
            for job_id in to_remove:
                del self.job_results[job_id]
            
            # Cleanup hourly counters
            for job_type in self.hourly_counters:
                self.hourly_counters[job_type] = [
                    ts for ts in self.hourly_counters[job_type]
                    if ts > cutoff_time
                ]
    
    async def _update_statistics(self):
        """Update and save queue statistics"""
        async with self.stats_lock:
            stats = {
                "timestamp": datetime.utcnow().isoformat(),
                "queue_size": await self.get_queue_size(),
                "active_jobs": await self.get_active_job_count(),
                "job_counters": {
                    job_type.value: counters
                    for job_type, counters in self.job_counters.items()
                }
            }
            
            # Save to file
            try:
                with open(self.stats_file, 'w') as f:
                    json.dump(stats, f, indent=2)
            except Exception as e:
                logger.error(f"Error saving queue statistics: {e}")
    
    async def save_queue_state(self):
        """Save queue state to disk"""
        async with self.queue_lock:
            try:
                # Prepare queue data
                queue_data = []
                for prioritized_job in self.priority_queue:
                    queue_data.append({
                        "priority": prioritized_job.priority,
                        "timestamp": prioritized_job.timestamp.isoformat(),
                        "job_id": prioritized_job.job_id,
                        "job_data": prioritized_job.job_data
                    })
                
                state = {
                    "queue": queue_data,
                    "job_counters": {
                        job_type.value: counters
                        for job_type, counters in self.job_counters.items()
                    },
                    "saved_at": datetime.utcnow().isoformat()
                }
                
                with open(self.queue_file, 'w') as f:
                    json.dump(state, f, indent=2)
                
                logger.debug("Queue state saved to disk")
                
            except Exception as e:
                logger.error(f"Error saving queue state: {e}")
    
    async def load_queue_state(self):
        """Load queue state from disk"""
        try:
            if self.queue_file.exists():
                with open(self.queue_file, 'r') as f:
                    state = json.load(f)
                
                # Load queue
                self.priority_queue = []
                for item in state.get("queue", []):
                    prioritized_job = PrioritizedJob(
                        priority=item["priority"],
                        timestamp=datetime.fromisoformat(item["timestamp"]),
                        job_id=item["job_id"],
                        job_data=item["job_data"]
                    )
                    heapq.heappush(self.priority_queue, prioritized_job)
                
                # Load counters
                for job_type_str, counters in state.get("job_counters", {}).items():
                    try:
                        job_type = JobType(job_type_str)
                        self.job_counters[job_type] = counters
                    except ValueError:
                        logger.warning(f"Unknown job type in saved state: {job_type_str}")
                
                logger.info(f"Loaded queue state with {len(self.priority_queue)} jobs")
                
        except Exception as e:
            logger.error(f"Error loading queue state: {e}")
            # Start with empty queue
    
    async def get_queue_statistics(self) -> Dict[str, Any]:
        """Get detailed queue statistics"""
        async with self.stats_lock:
            stats = {
                "timestamp": datetime.utcnow().isoformat(),
                "queue_size": await self.get_queue_size(),
                "active_jobs": await self.get_active_job_count(),
                "total_jobs_processed": sum(
                    counters.get("completed", 0)
                    for counters in self.job_counters.values()
                ),
                "job_type_breakdown": {
                    job_type.value: {
                        "total": counters.get("total", 0),
                        "completed": counters.get("completed", 0),
                        "failed": counters.get("failed", 0),
                        "cancelled": counters.get("cancelled", 0),
                        "success_rate": (
                            counters.get("completed", 0) / max(counters.get("total", 1), 1)
                        ) * 100
                    }
                    for job_type, counters in self.job_counters.items()
                }
            }
            
            # Add rate limit information
            stats["rate_limits"] = {
                job_type.value: self.job_type_limits.get(job_type, {})
                for job_type in JobType
            }
            
            return stats
    
    async def shutdown(self):
        """Shutdown job queue"""
        logger.info("Shutting down job queue...")
        
        self.running = False
        
        # Cancel queue processor
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all active jobs
        async with self.queue_lock:
            for job_id, task in list(self.active_jobs.items()):
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            # Save final state
            await self.save_queue_state()
            await self._update_statistics()
        
        logger.info("Job queue shutdown complete")
