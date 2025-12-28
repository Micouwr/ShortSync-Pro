"""
Database manager for ShortSync Pro
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
import aiosqlite
import json
from datetime import datetime

from .models import (
    Video, Job, PerformanceMetric, Channel, ContentTemplate,
    create_video, create_job, create_performance_metric,
    create_channel, create_content_template,
    create_tables_sql, create_indices_sql
)

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
        
        # Initialize default data if needed
        await self.initialize_default_data()
        
        return self
    
    async def create_tables(self):
        """Create all necessary tables using model schemas"""
        
        # Get table creation SQL from models
        table_sqls = create_tables_sql()
        
        for sql in table_sqls:
            await self.db.execute(sql)
        
        await self.db.commit()
        logger.info("Database tables created")
    
    async def create_indices(self):
        """Create database indices for performance"""
        
        # Get index creation SQL from models
        index_sqls = create_indices_sql()
        
        for sql in index_sqls:
            await self.db.execute(sql)
        
        await self.db.commit()
        logger.info("Database indices created")
    
    async def initialize_default_data(self):
        """Initialize default channels and templates if database is empty"""
        try:
            # Check if channels table is empty
            cursor = await self.db.execute('SELECT COUNT(*) as count FROM channels')
            row = await cursor.fetchone()
            channel_count = row['count'] if row else 0
            
            if channel_count == 0:
                # Create default channel
                default_channel = create_channel(
                    name="Default Channel",
                    niche="education",
                    is_active=True
                )
                await self.save_channel(default_channel)
                logger.info("Created default channel")
            
            # Check if templates table is empty
            cursor = await self.db.execute('SELECT COUNT(*) as count FROM content_templates')
            row = await cursor.fetchone()
            template_count = row['count'] if row else 0
            
            if template_count == 0:
                # Create default templates
                templates = [
                    create_content_template(
                        name="Educational Explainer",
                        niche="education",
                        template_json=json.dumps({
                            "structure": "hook-explanation-examples-conclusion",
                            "tone": "informative",
                            "target_duration": 45
                        })
                    ),
                    create_content_template(
                        name="Tech News Summary",
                        niche="technology",
                        template_json=json.dumps({
                            "structure": "news-intro-details-impact-takeaway",
                            "tone": "news",
                            "target_duration": 50
                        })
                    )
                ]
                
                for template in templates:
                    await self.save_content_template(template)
                
                logger.info(f"Created {len(templates)} default content templates")
                
        except Exception as e:
            logger.warning(f"Could not initialize default data: {e}")
    
    async def save_video(self, video_data: dict) -> str:
        """Save video information to database using Video model"""
        try:
            # Create Video instance
            video = create_video(**video_data)
            
            # Convert to dict for database
            video_dict = video.to_dict()
            
            # Build SQL dynamically based on fields
            columns = []
            placeholders = []
            values = []
            
            for col, val in video_dict.items():
                columns.append(col)
                placeholders.append('?')
                values.append(val)
            
            sql = f'''
                INSERT OR REPLACE INTO videos 
                ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
            '''
            
            await self.db.execute(sql, values)
            await self.db.commit()
            
            logger.debug(f"Saved video {video.id} to database")
            return video.id
            
        except Exception as e:
            logger.error(f"Error saving video: {e}")
            raise
    
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
        
        if 'quality_score' in kwargs:
            updates.append('quality_score = ?')
            params.append(kwargs['quality_score'])
        
        update_sql = f'''
            UPDATE videos 
            SET {', '.join(updates)}
            WHERE id = ?
        '''
        
        params.append(video_id)
        
        await self.db.execute(update_sql, params)
        await self.db.commit()
        
        logger.debug(f"Updated video {video_id} status to {status}")
    
    async def get_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get video information by ID"""
        cursor = await self.db.execute('''
            SELECT * FROM videos 
            WHERE id = ?
        ''', (video_id,))
        
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    async def get_video_model(self, video_id: str) -> Optional[Video]:
        """Get video as Video model object"""
        cursor = await self.db.execute('SELECT * FROM videos WHERE id = ?', (video_id,))
        row = await cursor.fetchone()
        
        if row:
            # Convert row to dict
            video_dict = dict(row)
            return Video.from_dict(video_dict)
        
        return None
    
    async def get_pending_videos(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get pending videos for approval"""
        cursor = await self.db.execute('''
            SELECT * FROM videos 
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT ?
        ''', (limit,))
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def get_pending_videos_models(self, limit: int = 10) -> List[Video]:
        """Get pending videos as Video models"""
        cursor = await self.db.execute('''
            SELECT * FROM videos 
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT ?
        ''', (limit,))
        
        rows = await cursor.fetchall()
        videos = []
        for row in rows:
            video_dict = dict(row)
            videos.append(Video.from_dict(video_dict))
        
        return videos
    
    async def save_job(self, job_data: dict) -> str:
        """Save job information to database using Job model"""
        try:
            # Create Job instance
            job = create_job(**job_data)
            
            # Convert to dict for database
            job_dict = job.to_dict()
            
            # Build SQL
            columns = []
            placeholders = []
            values = []
            
            for col, val in job_dict.items():
                columns.append(col)
                placeholders.append('?')
                values.append(val)
            
            sql = f'''
                INSERT INTO jobs 
                ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
            '''
            
            await self.db.execute(sql, values)
            await self.db.commit()
            
            logger.debug(f"Saved job {job.id} to database")
            return job.id
            
        except Exception as e:
            logger.error(f"Error saving job: {e}")
            raise
    
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
        logger.debug(f"Updated job {job_id} status to {status}")
    
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job information by ID"""
        cursor = await self.db.execute('''
            SELECT * FROM jobs 
            WHERE id = ?
        ''', (job_id,))
        
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    async def get_job_model(self, job_id: str) -> Optional[Job]:
        """Get job as Job model object"""
        cursor = await self.db.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
        row = await cursor.fetchone()
        
        if row:
            job_dict = dict(row)
            return Job.from_dict(job_dict)
        
        return None
    
    async def record_metric(self, metric_name: str, metric_value: float, channel: str = None):
        """Record a performance metric using PerformanceMetric model"""
        try:
            metric = create_performance_metric(
                metric_name=metric_name,
                metric_value=metric_value,
                channel=channel
            )
            
            metric_dict = metric.to_dict()
            
            columns = []
            placeholders = []
            values = []
            
            for col, val in metric_dict.items():
                columns.append(col)
                placeholders.append('?')
                values.append(val)
            
            sql = f'''
                INSERT INTO performance_metrics 
                ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
            '''
            
            await self.db.execute(sql, values)
            await self.db.commit()
            
            logger.debug(f"Recorded metric {metric_name}: {metric_value}")
            
        except Exception as e:
            logger.error(f"Error recording metric: {e}")
    
    async def get_metrics(self, metric_name: str, hours: int = 24, channel: str = None) -> List[Dict[str, Any]]:
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
    
    async def get_metrics_models(self, metric_name: str, hours: int = 24, channel: str = None) -> List[PerformanceMetric]:
        """Get metrics as PerformanceMetric models"""
        cursor = await self.db.execute('''
            SELECT * FROM performance_metrics
            WHERE metric_name = ?
                AND recorded_at >= datetime('now', ?)
                AND (? IS NULL OR channel = ?)
            ORDER BY recorded_at ASC
        ''', (metric_name, f'-{hours} hours', channel, channel))
        
        rows = await cursor.fetchall()
        metrics = []
        for row in rows:
            metric_dict = dict(row)
            metrics.append(PerformanceMetric.from_dict(metric_dict))
        
        return metrics
    
    async def save_channel(self, channel: Channel) -> int:
        """Save channel to database"""
        try:
            channel_dict = channel.to_dict()
            
            columns = []
            placeholders = []
            values = []
            
            for col, val in channel_dict.items():
                columns.append(col)
                placeholders.append('?')
                values.append(val)
            
            if 'id' in channel_dict:
                # Update existing
                set_clause = ', '.join([f'{col} = ?' for col in columns])
                sql = f'''
                    UPDATE channels 
                    SET {set_clause}
                    WHERE id = ?
                '''
                values.append(channel.id)
            else:
                # Insert new
                sql = f'''
                    INSERT INTO channels 
                    ({', '.join(columns)})
                    VALUES ({', '.join(placeholders)})
                '''
            
            await self.db.execute(sql, values)
            await self.db.commit()
            
            # Get the ID if it was an insert
            if not channel.id:
                cursor = await self.db.execute('SELECT last_insert_rowid() as id')
                row = await cursor.fetchone()
                channel.id = row['id']
            
            logger.debug(f"Saved channel {channel.name} to database")
            return channel.id
            
        except Exception as e:
            logger.error(f"Error saving channel: {e}")
            raise
    
    async def get_channel(self, channel_id: int) -> Optional[Channel]:
        """Get channel by ID"""
        cursor = await self.db.execute('SELECT * FROM channels WHERE id = ?', (channel_id,))
        row = await cursor.fetchone()
        
        if row:
            channel_dict = dict(row)
            return Channel.from_dict(channel_dict)
        
        return None
    
    async def get_channel_by_name(self, name: str) -> Optional[Channel]:
        """Get channel by name"""
        cursor = await self.db.execute('SELECT * FROM channels WHERE name = ?', (name,))
        row = await cursor.fetchone()
        
        if row:
            channel_dict = dict(row)
            return Channel.from_dict(channel_dict)
        
        return None
    
    async def get_active_channels(self) -> List[Channel]:
        """Get all active channels"""
        cursor = await self.db.execute('SELECT * FROM channels WHERE is_active = 1')
        rows = await cursor.fetchall()
        
        channels = []
        for row in rows:
            channel_dict = dict(row)
            channels.append(Channel.from_dict(channel_dict))
        
        return channels
    
    async def save_content_template(self, template: ContentTemplate) -> int:
        """Save content template to database"""
        try:
            template_dict = template.to_dict()
            
            columns = []
            placeholders = []
            values = []
            
            for col, val in template_dict.items():
                columns.append(col)
                placeholders.append('?')
                values.append(val)
            
            if 'id' in template_dict:
                # Update existing
                set_clause = ', '.join([f'{col} = ?' for col in columns])
                sql = f'''
                    UPDATE content_templates 
                    SET {set_clause}
                    WHERE id = ?
                '''
                values.append(template.id)
            else:
                # Insert new
                sql = f'''
                    INSERT INTO content_templates 
                    ({', '.join(columns)})
                    VALUES ({', '.join(placeholders)})
                '''
            
            await self.db.execute(sql, values)
            await self.db.commit()
            
            # Get the ID if it was an insert
            if not template.id:
                cursor = await self.db.execute('SELECT last_insert_rowid() as id')
                row = await cursor.fetchone()
                template.id = row['id']
            
            logger.debug(f"Saved content template {template.name} to database")
            return template.id
            
        except Exception as e:
            logger.error(f"Error saving content template: {e}")
            raise
    
    async def get_content_template(self, template_id: int) -> Optional[ContentTemplate]:
        """Get content template by ID"""
        cursor = await self.db.execute('SELECT * FROM content_templates WHERE id = ?', (template_id,))
        row = await cursor.fetchone()
        
        if row:
            template_dict = dict(row)
            return ContentTemplate.from_dict(template_dict)
        
        return None
    
    async def get_templates_by_niche(self, niche: str) -> List[ContentTemplate]:
        """Get content templates by niche"""
        cursor = await self.db.execute('SELECT * FROM content_templates WHERE niche = ?', (niche,))
        rows = await cursor.fetchall()
        
        templates = []
        for row in rows:
            template_dict = dict(row)
            templates.append(ContentTemplate.from_dict(template_dict))
        
        return templates
    
    async def increment_template_usage(self, template_id: int, success: bool = True):
        """Increment template usage count and update success rate"""
        # Get current template
        template = await self.get_content_template(template_id)
        if not template:
            return
        
        # Update usage count
        template.usage_count += 1
        
        # Update success rate
        if template.success_rate is None:
            template.success_rate = 100.0 if success else 0.0
        else:
            # Simple moving average
            current_success_rate = template.success_rate
            new_success = 1.0 if success else 0.0
            # Weight recent results more heavily
            template.success_rate = (current_success_rate * 0.7) + (new_success * 100 * 0.3)
        
        # Save updated template
        await self.save_content_template(template)
    
    async def get_statistics(self) -> Dict[str, Any]:
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
        
        # Recent performance metrics (last 7 days)
        cursor = await self.db.execute('''
            SELECT metric_name, AVG(metric_value) as avg_value
            FROM performance_metrics
            WHERE recorded_at >= datetime('now', '-7 days')
            GROUP BY metric_name
        ''')
        metrics = await cursor.fetchall()
        stats['metrics'] = {row['metric_name']: row['avg_value'] for row in metrics}
        
        # Channel statistics
        cursor = await self.db.execute('''
            SELECT 
                COUNT(*) as total_channels,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_channels
            FROM channels
        ''')
        channel_stats = await cursor.fetchone()
        stats['channels'] = dict(channel_stats) if channel_stats else {}
        
        # Content template statistics
        cursor = await self.db.execute('''
            SELECT 
                COUNT(*) as total_templates,
                AVG(success_rate) as avg_success_rate,
                SUM(usage_count) as total_usage
            FROM content_templates
        ''')
        template_stats = await cursor.fetchone()
        stats['templates'] = dict(template_stats) if template_stats else {}
        
        return stats
    
    async def save_metrics(self, metrics_data: Dict[str, Any]):
        """Save metrics snapshot"""
        for metric_name, metric_value in metrics_data.items():
            if metric_name != 'timestamp':
                await self.record_metric(metric_name, metric_value)
    
    async def get_recent_videos(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get most recent videos"""
        cursor = await self.db.execute('''
            SELECT * FROM videos 
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def search_videos(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search videos by title or topic"""
        search_term = f'%{query}%'
        cursor = await self.db.execute('''
            SELECT * FROM videos 
            WHERE title LIKE ? OR topic LIKE ? OR description LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (search_term, search_term, search_term, limit))
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def close(self):
        """Close database connection"""
        if self.db:
            await self.db.close()
            logger.info("Database connection closed")
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

# Add logger at module level
import logging
logger = logging.getLogger(__name__)
