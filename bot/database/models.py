"""
Database models for ShortSync Pro using aiosqlite.

Defines table schemas and data classes for:
- Videos
- Jobs
- Performance metrics
- Channels
- Content templates
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Dict, Any, Optional, List
import json

@dataclass
class Video:
    """Video model"""
    id: str
    title: str
    description: Optional[str] = None
    topic: Optional[str] = None
    category: Optional[str] = None
    script: Optional[str] = None
    thumbnail_path: Optional[str] = None
    video_path: Optional[str] = None
    duration_seconds: Optional[int] = None
    quality_score: Optional[float] = None
    status: str = "pending"  # pending, approved, rejected, uploaded, failed
    created_at: Optional[str] = None
    approved_at: Optional[str] = None
    uploaded_at: Optional[str] = None
    youtube_url: Optional[str] = None
    views: int = 0
    likes: int = 0
    comments: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        data = asdict(self)
        data["metadata"] = json.dumps(data["metadata"])
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Video':
        """Create from database dictionary"""
        if "metadata" in data and isinstance(data["metadata"], str):
            try:
                data["metadata"] = json.loads(data["metadata"])
            except:
                data["metadata"] = {}
        
        # Handle None values for optional fields
        for field_name, field_type in cls.__annotations__.items():
            if field_name in data and data[field_name] is None:
                # Check if it's Optional type
                if hasattr(field_type, '__origin__') and field_type.__origin__ is Optional:
                    pass  # None is valid for Optional
                elif field_name in ["description", "topic", "category", "script", 
                                   "thumbnail_path", "video_path", "youtube_url",
                                   "approved_at", "uploaded_at"]:
                    pass  # These fields can be None
                else:
                    # Set default based on type
                    if field_type is str:
                        data[field_name] = ""
                    elif field_type is int:
                        data[field_name] = 0
                    elif field_type is float:
                        data[field_name] = 0.0
        
        return cls(**data)

@dataclass
class Job:
    """Job model"""
    id: str
    type: str  # trend_research, script_generation, video_creation, upload
    status: str = "pending"  # pending, processing, completed, failed
    channel: Optional[str] = None
    topic: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result_json: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Job':
        """Create from database dictionary"""
        return cls(**data)
    
    def get_result(self) -> Optional[Dict[str, Any]]:
        """Parse result JSON"""
        if self.result_json:
            try:
                return json.loads(self.result_json)
            except:
                return None
        return None
    
    def set_result(self, result: Dict[str, Any]):
        """Set result as JSON"""
        self.result_json = json.dumps(result)

@dataclass
class PerformanceMetric:
    """Performance metric model"""
    id: Optional[int] = None  # AUTOINCREMENT primary key
    metric_name: str = ""
    metric_value: float = 0.0
    channel: Optional[str] = None
    recorded_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        data = asdict(self)
        if data["id"] is None:
            del data["id"]  # Let database auto-generate
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PerformanceMetric':
        """Create from database dictionary"""
        return cls(**data)

@dataclass
class Channel:
    """Channel model"""
    id: Optional[int] = None  # AUTOINCREMENT primary key
    name: str = ""
    youtube_channel_id: Optional[str] = None
    niche: Optional[str] = None
    upload_schedule_json: Optional[str] = None
    branding_json: Optional[str] = None
    created_at: Optional[str] = None
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        data = asdict(self)
        if data["id"] is None:
            del data["id"]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Channel':
        """Create from database dictionary"""
        return cls(**data)
    
    def get_upload_schedule(self) -> Optional[Dict[str, Any]]:
        """Parse upload schedule JSON"""
        if self.upload_schedule_json:
            try:
                return json.loads(self.upload_schedule_json)
            except:
                return None
        return None
    
    def set_upload_schedule(self, schedule: Dict[str, Any]):
        """Set upload schedule as JSON"""
        self.upload_schedule_json = json.dumps(schedule)
    
    def get_branding(self) -> Optional[Dict[str, Any]]:
        """Parse branding JSON"""
        if self.branding_json:
            try:
                return json.loads(self.branding_json)
            except:
                return None
        return None
    
    def set_branding(self, branding: Dict[str, Any]):
        """Set branding as JSON"""
        self.branding_json = json.dumps(branding)

@dataclass
class ContentTemplate:
    """Content template model"""
    id: Optional[int] = None  # AUTOINCREMENT primary key
    name: str = ""
    niche: Optional[str] = None
    template_json: str = "{}"
    success_rate: Optional[float] = None
    usage_count: int = 0
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        data = asdict(self)
        if data["id"] is None:
            del data["id"]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContentTemplate':
        """Create from database dictionary"""
        return cls(**data)
    
    def get_template(self) -> Dict[str, Any]:
        """Parse template JSON"""
        try:
            return json.loads(self.template_json)
        except:
            return {}
    
    def set_template(self, template: Dict[str, Any]):
        """Set template as JSON"""
        self.template_json = json.dumps(template)

# Table creation SQL statements
TABLE_SCHEMAS = {
    "videos": """
        CREATE TABLE IF NOT EXISTS videos (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            topic TEXT,
            category TEXT,
            script TEXT,
            thumbnail_path TEXT,
            video_path TEXT,
            duration_seconds INTEGER,
            quality_score REAL,
            status TEXT CHECK(status IN ('pending', 'approved', 'rejected', 'uploaded', 'failed')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved_at TIMESTAMP,
            uploaded_at TIMESTAMP,
            youtube_url TEXT,
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            metadata TEXT DEFAULT '{}'
        )
    """,
    "jobs": """
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            type TEXT CHECK(type IN ('trend_research', 'script_generation', 'video_creation', 'upload')),
            status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'failed')),
            channel TEXT,
            topic TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            result_json TEXT,
            error_message TEXT
        )
    """,
    "performance_metrics": """
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_name TEXT NOT NULL,
            metric_value REAL NOT NULL,
            channel TEXT,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "channels": """
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            youtube_channel_id TEXT,
            niche TEXT,
            upload_schedule_json TEXT,
            branding_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    """,
    "content_templates": """
        CREATE TABLE IF NOT EXISTS content_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            niche TEXT,
            template_json TEXT NOT NULL,
            success_rate REAL,
            usage_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
}

# Index creation SQL statements
TABLE_INDICES = {
    "videos": [
        "CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status)",
        "CREATE INDEX IF NOT EXISTS idx_videos_created ON videos(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_videos_topic ON videos(topic)"
    ],
    "jobs": [
        "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)",
        "CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(type)",
        "CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at)"
    ],
    "performance_metrics": [
        "CREATE INDEX IF NOT EXISTS idx_performance_metric_name ON performance_metrics(metric_name)",
        "CREATE INDEX IF NOT EXISTS idx_performance_recorded ON performance_metrics(recorded_at)"
    ],
    "channels": [
        "CREATE INDEX IF NOT EXISTS idx_channels_active ON channels(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_channels_name ON channels(name)"
    ],
    "content_templates": [
        "CREATE INDEX IF NOT EXISTS idx_templates_niche ON content_templates(niche)",
        "CREATE INDEX IF NOT EXISTS idx_templates_success ON content_templates(success_rate)"
    ]
}

# Helper functions for database operations
def create_tables_sql() -> List[str]:
    """Get SQL statements for creating all tables"""
    return list(TABLE_SCHEMAS.values())

def create_indices_sql() -> List[str]:
    """Get SQL statements for creating all indices"""
    all_indices = []
    for indices in TABLE_INDICES.values():
        all_indices.extend(indices)
    return all_indices

def get_table_names() -> List[str]:
    """Get list of all table names"""
    return list(TABLE_SCHEMAS.keys())

# Model factory functions
def create_video(**kwargs) -> Video:
    """Create a Video instance with current timestamp"""
    if "created_at" not in kwargs:
        kwargs["created_at"] = datetime.utcnow().isoformat()
    return Video(**kwargs)

def create_job(**kwargs) -> Job:
    """Create a Job instance with current timestamp"""
    if "created_at" not in kwargs:
        kwargs["created_at"] = datetime.utcnow().isoformat()
    return Job(**kwargs)

def create_performance_metric(**kwargs) -> PerformanceMetric:
    """Create a PerformanceMetric instance with current timestamp"""
    if "recorded_at" not in kwargs:
        kwargs["recorded_at"] = datetime.utcnow().isoformat()
    return PerformanceMetric(**kwargs)

def create_channel(**kwargs) -> Channel:
    """Create a Channel instance with current timestamp"""
    if "created_at" not in kwargs:
        kwargs["created_at"] = datetime.utcnow().isoformat()
    return Channel(**kwargs)

def create_content_template(**kwargs) -> ContentTemplate:
    """Create a ContentTemplate instance with current timestamp"""
    if "created_at" not in kwargs:
        kwargs["created_at"] = datetime.utcnow().isoformat()
    return ContentTemplate(**kwargs)
