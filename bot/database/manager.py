# bot/database/manager.py
"""
Database manager for content and performance data.
"""

import asyncio
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from bot.database.models import Base, GeneratedVideo, ContentBlacklist

class DatabaseManager:
    def __init__(self, config):
        self.config = config
        self.db_path = config.dirs['data'] / 'content.db'
        self.engine = None
        self.session_factory = None
    
    def initialize(self):
        """Initialize database connection and create tables."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            f'sqlite:///{self.db_path}',
            connect_args={'check_same_thread': False},
            poolclass=StaticPool,
            echo=False  # Set to True for debugging
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = scoped_session(
            sessionmaker(bind=self.engine, expire_on_commit=False)
        )
    
    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def add_video(self, job_id: str, trend_topic: str, script: str, video_path: str):
        """Add a generated video to the database."""
        with self.session_scope() as session:
            video = GeneratedVideo(
                job_id=job_id,
                trend_topic=trend_topic,
                script=script,
                video_path=video_path
            )
            session.add(video)
            return video.id
    
    def update_youtube_details(self, job_id: str, youtube_video_id: str, youtube_url: str):
        """Update video with YouTube details after upload."""
        with self.session_scope() as session:
            video = session.query(GeneratedVideo).filter_by(job_id=job_id).first()
            if video:
                video.youtube_video_id = youtube_video_id
                video.youtube_url = youtube_url
                video.uploaded_at = sa.func.now()
    
    def blacklist_topic(self, topic: str, reason: str = None):
        """Add a topic to the blacklist."""
        with self.session_scope() as session:
            blacklist = ContentBlacklist(topic=topic, reason=reason)
            session.add(blacklist)
    
    def is_topic_blacklisted(self, topic: str) -> bool:
        """Check if a topic is blacklisted."""
        with self.session_scope() as session:
            count = session.query(ContentBlacklist).filter_by(topic=topic).count()
            return count > 0
