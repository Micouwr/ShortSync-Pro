"""
Database manager for ShortSync Pro
"""

import asyncio
from pathlib import Path
from typing import Optional
import aiosqlite
import json
from datetime import datetime

class DatabaseManager:
    """Manage SQLite database for ShortSync Pro"""
    
    def __init__(self, config):
        self.config = config
        self.db_path = config.dirs['data'] / 'shortsync.db'
        self.db = None
    
    async def initialize(self):
        """Initialize database and create tables"""
        # Ensure data directory exists
        self.config.dirs['data'].mkdir(parents=True, exist_ok=True)
        
        # Connect to database
        self.db = await aiosqlite.connect(str(self.db_path))
        self.db.row_factory = aiosqlite.Row
        
        # Create tables
        await self.create_tables()
        
        # Create indices
        await self.create_indices()
        
        return self
    
    async def create_tables(self):
        """Create all necessary tables"""
        
        # Videos table
        await self.db.execute('''
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
                metadata JSON
            )
        ''')
        
        # Jobs table
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                type TEXT CHECK(type IN ('trend_research', 'script_generation', 'video_creation', 'upload')),
                status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'failed')),
                channel TEXT,
                topic TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                result_json JSON,
                error_message TEXT
            )
        ''')
        
        # Performance metrics table
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                channel TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Channel configurations
        await self.db.execute('''
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
        ''')
        
        # Content templates
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS content_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                niche TEXT,
                template_json TEXT NOT NULL,
                success_rate REAL,
                usage_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await self.db.commit()
    
    async def create_indices(self):
        """Create database indices for performance"""
        
        indices = [
            'CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status)',
            'CREATE INDEX IF NOT EXISTS idx_videos_created ON videos(created_at)',
            'CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)',
            'CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(type)',
            'CREATE INDEX IF NOT EXISTS idx_performance_metric ON performance_metrics(metric_name, recorded_at)',
            'CREATE INDEX IF NOT EXISTS idx_channels_active ON channels(is_active)'
        ]
        
        for index_sql in indices:
            await self.db.execute(index_sql)
        
        await self.db.commit()
    
    async def save_video(self, video_data: dict) -> str:
        """Save video information to database"""
        video_id = video_data.get('id', datetime.now().strftime('%Y%m%d_%H%M%S'))
        
        await self.db.execute('''
            INSERT OR REPLACE INTO videos 
            (id, title, description, topic, category, script, thumbnail_path, 
             video_path, duration_seconds, quality_score, status, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            video_id,
            video_data.get('title'),
            video_data.get('description'),
            video_data.get('topic'),
            video_data.get('category'),
            video_data.get('script'),
            video_data.get('thumbnail_path'),
            video_data.get('video_path'),
            video_data.get('duration_seconds'),
            video_data.get('quality_score'),
            video_data.get('status', 'pending'),
            json.dumps(video_data.get('metadata', {}))
        ))
        
        await self.db.commit()
        return video_id
    
    async def update_video_status(self, video_id: str, status: str, **kwargs):
        """Update video status and optional fields"""
        updates = []
        params = []
        
        updates.append('status = ?')
        params.append(status)
        
        if 'youtube_url' in kwargs:
            updates.append('youtube_url = ?')
            params.append(kwargs['youtube_url'])
            updates.append('uploaded_at = CURRENT_TIMESTAMP')
        
        if 'approved_at' in kwargs:
            updates.append('approved_at = ?')
            params.append(kwargs['approved_at'])
        
        update_sql = f'''
            UPDATE videos 
            SET {', '.join(updates)}
            WHERE id = ?
        '''
        
        params.append(video_id)
        
        await self.db.execute(update_sql, params)
        await self.db.commit()
    
    async def get_pending_videos(self, limit: int = 10) -> list:
        """Get pending videos for approval"""
        cursor = await self.db.execute('''
            SELECT * FROM videos 
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT ?
        ''', (limit,))
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def save_job(self, job_data: dict) -> str:
        """Save job information to database"""
        job_id = job_data.get('id', datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
        
        await self.db.execute('''
            INSERT INTO jobs 
            (id, type, status, channel, topic, result_json)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            job_id,
            job_data.get('type'),
            job_data.get('status', 'pending'),
            job_data.get('channel'),
            job_data.get('topic'),
            json.dumps(job_data.get('result', {}))
        ))
        
        await self.db.commit()
        return job_id
    
    async def update_job_status(self, job_id: str, status: str, result: dict = None, error: str = None):
        """Update job status"""
        if status == 'completed':
            await self.db.execute('''
                UPDATE jobs 
                SET status = ?, completed_at = CURRENT_TIMESTAMP, 
                    result_json = ?, error_message = ?
                WHERE id = ?
            ''', (status, json.dumps(result) if result else None, error, job_id))
        elif status == 'processing':
            await self.db.execute('''
                UPDATE jobs 
                SET status = ?, started_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, job_id))
        else:
            await self.db.execute('''
                UPDATE jobs 
                SET status = ?, error_message = ?
                WHERE id = ?
            ''', (status, error, job_id))
        
        await self.db.commit()
    
    async def record_metric(self, metric_name: str, metric_value: float, channel: str = None):
        """Record a performance metric"""
        await self.db.execute('''
            INSERT INTO performance_metrics 
            (metric_name, metric_value, channel)
            VALUES (?, ?, ?)
        ''', (metric_name, metric_value, channel))
        
        await self.db.commit()
    
    async def get_metrics(self, metric_name: str, hours: int = 24, channel: str = None) -> list:
        """Get metrics for a specific time period"""
        cursor = await self.db.execute('''
            SELECT metric_value, recorded_at
            FROM performance_metrics
            WHERE metric_name = ?
                AND recorded_at >= datetime('now', ?)
                AND (? IS NULL OR channel = ?)
            ORDER BY recorded_at ASC
        ''', (metric_name, f'-{hours} hours', channel, channel))
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def get_statistics(self) -> dict:
        """Get overall bot statistics"""
        stats = {}
        
        # Video statistics
        cursor = await self.db.execute('''
            SELECT 
                COUNT(*) as total_videos,
                SUM(CASE WHEN status = 'uploaded' THEN 1 ELSE 0 END) as uploaded_videos,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_videos,
                AVG(quality_score) as avg_quality_score,
                AVG(duration_seconds) as avg_duration
            FROM videos
        ''')
        video_stats = await cursor.fetchone()
        stats['videos'] = dict(video_stats) if video_stats else {}
        
        # Job statistics
        cursor = await self.db.execute('''
            SELECT 
                COUNT(*) as total_jobs,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_jobs,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_jobs,
                AVG(
                    (julianday(completed_at) - julianday(started_at)) * 24 * 60 * 60
                ) as avg_job_duration_seconds
            FROM jobs
            WHERE started_at IS NOT NULL AND completed_at IS NOT NULL
        ''')
        job_stats = await cursor.fetchone()
        stats['jobs'] = dict(job_stats) if job_stats else {}
        
        # Recent performance metrics
        cursor = await self.db.execute('''
            SELECT metric_name, AVG(metric_value) as avg_value
            FROM performance_metrics
            WHERE recorded_at >= datetime('now', '-7 days')
            GROUP BY metric_name
        ''')
        metrics = await cursor.fetchall()
        stats['metrics'] = {row['metric_name']: row['avg_value'] for row in metrics}
        
        return stats
    
    async def close(self):
        """Close database connection"""
        if self.db:
            await self.db.close()
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
