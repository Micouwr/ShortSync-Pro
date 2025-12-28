"""
State manager for ShortSync Pro.

Manages the global state of the bot including:
- Current pipeline execution state
- Resource usage tracking
- Recovery state for crash recovery
- Performance metrics aggregation
"""

import asyncio
import json
import pickle
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class StateType(Enum):
    """Types of state that can be managed"""
    PIPELINE = "pipeline"
    JOB = "job"
    RESOURCE = "resource"
    METRIC = "metric"
    RECOVERY = "recovery"

class PipelineStage(Enum):
    """Pipeline execution stages"""
    IDLE = "idle"
    TREND_DETECTION = "trend_detection"
    SCRIPT_GENERATION = "script_generation"
    ASSET_GATHERING = "asset_gathering"
    VOICEOVER_GENERATION = "voiceover_generation"
    VIDEO_ASSEMBLY = "video_assembly"
    THUMBNAIL_GENERATION = "thumbnail_generation"
    QUALITY_CHECK = "quality_check"
    APPROVAL_PENDING = "approval_pending"
    YOUTUBE_UPLOAD = "youtube_upload"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class PipelineState:
    """State of a pipeline execution"""
    pipeline_id: str
    stage: PipelineStage = PipelineStage.IDLE
    current_job_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    progress: float = 0.0  # 0.0 to 1.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class JobState:
    """State of an individual job"""
    job_id: str
    job_type: str
    status: str = "pending"  # pending, processing, completed, failed
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@dataclass
class ResourceUsage:
    """Resource usage tracking"""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    disk_mb: float = 0.0
    active_connections: int = 0
    active_jobs: int = 0

class StateManager:
    """Main state management class"""
    
    def __init__(self, config, db_manager):
        self.config = config
        self.db = db_manager
        self.state_file = config.dirs['state'] / 'bot_state.json'
        self.recovery_file = config.dirs['state'] / 'recovery_state.pkl'
        
        # In-memory state caches
        self.active_pipelines: Dict[str, PipelineState] = {}
        self.active_jobs: Dict[str, JobState] = {}
        self.resource_history: List[ResourceUsage] = []
        
        # Recovery state
        self.recovery_needed = False
        self.last_save_time = None
        
    async def initialize(self):
        """Initialize state manager"""
        logger.info("Initializing state manager...")
        
        # Ensure state directory exists
        self.config.dirs['state'].mkdir(parents=True, exist_ok=True)
        
        # Load previous state if exists
        await self.load_state()
        
        # Check for recovery needed
        self.recovery_needed = await self.check_recovery_needed()
        
        if self.recovery_needed:
            logger.warning("Recovery needed from previous shutdown")
            await self.recover_state()
        
        logger.info("State manager initialized")
        return self
    
    async def create_pipeline_state(self, pipeline_id: str) -> PipelineState:
        """Create a new pipeline state"""
        state = PipelineState(pipeline_id=pipeline_id)
        self.active_pipelines[pipeline_id] = state
        await self.save_state()
        return state
    
    async def update_pipeline_stage(self, pipeline_id: str, stage: PipelineStage, 
                                   progress: float = 0.0, metadata: Dict[str, Any] = None):
        """Update pipeline stage"""
        if pipeline_id not in self.active_pipelines:
            logger.warning(f"Pipeline {pipeline_id} not found, creating new state")
            state = await self.create_pipeline_state(pipeline_id)
        else:
            state = self.active_pipelines[pipeline_id]
        
        state.stage = stage
        state.progress = progress
        
        if metadata:
            state.metadata.update(metadata)
        
        if stage == PipelineStage.TREND_DETECTION and not state.start_time:
            state.start_time = datetime.utcnow()
        elif stage in [PipelineStage.COMPLETED, PipelineStage.FAILED]:
            state.end_time = datetime.utcnow()
        
        await self.save_state()
        logger.debug(f"Updated pipeline {pipeline_id} to stage {stage.value} (progress: {progress})")
    
    async def set_pipeline_error(self, pipeline_id: str, error_message: str):
        """Set pipeline error state"""
        if pipeline_id in self.active_pipelines:
            state = self.active_pipelines[pipeline_id]
            state.stage = PipelineStage.FAILED
            state.error_message = error_message
            state.end_time = datetime.utcnow()
            await self.save_state()
            logger.error(f"Pipeline {pipeline_id} failed: {error_message}")
    
    async def create_job_state(self, job_id: str, job_type: str) -> JobState:
        """Create a new job state"""
        state = JobState(job_id=job_id, job_type=job_type)
        self.active_jobs[job_id] = state
        await self.save_state()
        return state
    
    async def update_job_status(self, job_id: str, status: str, progress: float = 0.0,
                               result: Dict[str, Any] = None, error: str = None):
        """Update job status"""
        if job_id not in self.active_jobs:
            logger.warning(f"Job {job_id} not found")
            return
        
        state = self.active_jobs[job_id]
        state.status = status
        state.progress = progress
        
        if status == "processing" and not state.started_at:
            state.started_at = datetime.utcnow()
        elif status in ["completed", "failed"]:
            state.completed_at = datetime.utcnow()
            state.result = result
            state.error = error
        
        await self.save_state()
        logger.debug(f"Updated job {job_id} to status {status} (progress: {progress})")
    
    async def record_resource_usage(self, cpu_percent: float, memory_mb: float, 
                                   disk_mb: float, active_jobs: int):
        """Record current resource usage"""
        usage = ResourceUsage(
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            disk_mb=disk_mb,
            active_jobs=active_jobs
        )
        
        self.resource_history.append(usage)
        
        # Keep only last 1000 records
        if len(self.resource_history) > 1000:
            self.resource_history = self.resource_history[-1000:]
        
        # Save to database periodically
        if len(self.resource_history) % 10 == 0:
            await self.db.record_metric("cpu_usage", cpu_percent)
            await self.db.record_metric("memory_usage_mb", memory_mb)
            await self.db.record_metric("disk_usage_mb", disk_mb)
            await self.db.record_metric("active_jobs", active_jobs)
    
    async def get_active_pipelines(self) -> List[PipelineState]:
        """Get all active pipelines"""
        return list(self.active_pipelines.values())
    
    async def get_active_jobs(self) -> List[JobState]:
        """Get all active jobs"""
        return [job for job in self.active_jobs.values() 
                if job.status in ["pending", "processing"]]
    
    async def get_pipeline_state(self, pipeline_id: str) -> Optional[PipelineState]:
        """Get pipeline state by ID"""
        return self.active_pipelines.get(pipeline_id)
    
    async def get_job_state(self, job_id: str) -> Optional[JobState]:
        """Get job state by ID"""
        return self.active_jobs.get(job_id)
    
    async def cleanup_old_states(self, hours_old: int = 24):
        """Clean up old state entries"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_old)
        
        # Cleanup pipelines
        to_remove = []
        for pipeline_id, state in self.active_pipelines.items():
            if state.end_time and state.end_time < cutoff_time:
                to_remove.append(pipeline_id)
        
        for pipeline_id in to_remove:
            del self.active_pipelines[pipeline_id]
        
        # Cleanup jobs
        to_remove = []
        for job_id, state in self.active_jobs.items():
            if state.completed_at and state.completed_at < cutoff_time:
                to_remove.append(job_id)
        
        for job_id in to_remove:
            del self.active_jobs[job_id]
        
        # Cleanup resource history
        self.resource_history = [
            usage for usage in self.resource_history
            if usage.timestamp > cutoff_time
        ]
        
        await self.save_state()
        logger.info(f"Cleaned up {len(to_remove)} old state entries")
    
    async def save_state(self):
        """Save current state to disk"""
        try:
            state_data = {
                "active_pipelines": {
                    pid: asdict(state) 
                    for pid, state in self.active_pipelines.items()
                },
                "active_jobs": {
                    jid: asdict(state)
                    for jid, state in self.active_jobs.items()
                },
                "last_save": datetime.utcnow().isoformat()
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2, default=str)
            
            self.last_save_time = datetime.utcnow()
            logger.debug("State saved to disk")
            
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    async def load_state(self):
        """Load state from disk"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state_data = json.load(f)
                
                # Load pipelines
                self.active_pipelines = {}
                for pid, data in state_data.get("active_pipelines", {}).items():
                    state = PipelineState(**data)
                    # Convert string dates back to datetime
                    for date_field in ["start_time", "end_time"]:
                        if data.get(date_field):
                            setattr(state, date_field, datetime.fromisoformat(data[date_field]))
                    self.active_pipelines[pid] = state
                
                # Load jobs
                self.active_jobs = {}
                for jid, data in state_data.get("active_jobs", {}).items():
                    state = JobState(**data)
                    # Convert string dates back to datetime
                    for date_field in ["created_at", "started_at", "completed_at"]:
                        if data.get(date_field):
                            setattr(state, date_field, datetime.fromisoformat(data[date_field]))
                    self.active_jobs[jid] = state
                
                logger.info(f"Loaded state with {len(self.active_pipelines)} pipelines and {len(self.active_jobs)} jobs")
                
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            # Start fresh if state file is corrupted
            self.active_pipelines = {}
            self.active_jobs = {}
    
    async def save_recovery_state(self, recovery_data: Dict[str, Any]):
        """Save recovery state for crash recovery"""
        try:
            recovery_data["saved_at"] = datetime.utcnow()
            with open(self.recovery_file, 'wb') as f:
                pickle.dump(recovery_data, f)
            logger.debug("Recovery state saved")
        except Exception as e:
            logger.error(f"Failed to save recovery state: {e}")
    
    async def load_recovery_state(self) -> Optional[Dict[str, Any]]:
        """Load recovery state"""
        try:
            if self.recovery_file.exists():
                with open(self.recovery_file, 'rb') as f:
                    recovery_data = pickle.load(f)
                logger.info("Recovery state loaded")
                return recovery_data
        except Exception as e:
            logger.error(f"Failed to load recovery state: {e}")
        return None
    
    async def check_recovery_needed(self) -> bool:
        """Check if recovery is needed from previous shutdown"""
        if not self.state_file.exists():
            return False
        
        try:
            # Check if there were active pipelines/jobs that didn't complete
            active_pipelines = [
                state for state in self.active_pipelines.values()
                if state.stage not in [PipelineStage.COMPLETED, PipelineStage.FAILED]
            ]
            
            active_jobs = [
                state for state in self.active_jobs.values()
                if state.status in ["pending", "processing"]
            ]
            
            return len(active_pipelines) > 0 or len(active_jobs) > 0
            
        except Exception as e:
            logger.error(f"Error checking recovery need: {e}")
            return False
    
    async def recover_state(self):
        """Attempt to recover from previous shutdown"""
        logger.info("Attempting state recovery...")
        
        try:
            # Load recovery state if available
            recovery_data = await self.load_recovery_state()
            
            if recovery_data:
                # Apply recovery logic based on saved state
                logger.info(f"Recovery data available: {recovery_data.get('type', 'unknown')}")
                # Specific recovery logic would depend on what was saved
                pass
            
            # Cleanup any stale states
            await self.cleanup_old_states(hours_old=1)
            
            # Mark recovery as complete
            self.recovery_needed = False
            logger.info("State recovery completed")
            
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        active_pipelines = await self.get_active_pipelines()
        active_jobs = await self.get_active_jobs()
        
        # Calculate pipeline statistics
        pipeline_stats = {
            "total": len(self.active_pipelines),
            "active": len(active_pipelines),
            "completed": len([p for p in self.active_pipelines.values() 
                            if p.stage == PipelineStage.COMPLETED]),
            "failed": len([p for p in self.active_pipelines.values() 
                          if p.stage == PipelineStage.FAILED])
        }
        
        # Calculate job statistics
        job_stats = {
            "total": len(self.active_jobs),
            "pending": len([j for j in self.active_jobs.values() 
                          if j.status == "pending"]),
            "processing": len([j for j in self.active_jobs.values() 
                             if j.status == "processing"]),
            "completed": len([j for j in self.active_jobs.values() 
                            if j.status == "completed"]),
            "failed": len([j for j in self.active_jobs.values() 
                          if j.status == "failed"])
        }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "recovery_needed": self.recovery_needed,
            "pipelines": pipeline_stats,
            "jobs": job_stats,
            "resource_history_count": len(self.resource_history),
            "last_save": self.last_save_time.isoformat() if self.last_save_time else None
        }
    
    async def shutdown(self):
        """Clean shutdown of state manager"""
        logger.info("Shutting down state manager...")
        
        # Save final state
        await self.save_state()
        
        # Cleanup recovery file
        if self.recovery_file.exists():
            try:
                self.recovery_file.unlink()
            except Exception as e:
                logger.error(f"Failed to cleanup recovery file: {e}")
        
        logger.info("State manager shutdown complete")
