# bot/database/models.py
"""
Database models for storing content and performance data.
"""

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

Base = declarative_base()

class GeneratedVideo(Base):
    __tablename__ = 'generated_videos'
    
    id = sa.Column(sa.Integer, primary_key=True)
    job_id = sa.Column(sa.String, unique=True, nullable=False)
    trend_topic = sa.Column(sa.String, nullable=False)
    script = sa.Column(sa.Text, nullable=False)
    video_path = sa.Column(sa.String, nullable=False)
    youtube_video_id = sa.Column(sa.String, unique=True)
    youtube_url = sa.Column(sa.String)
    uploaded_at = sa.Column(sa.DateTime)
    privacy_status = sa.Column(sa.String, default='private')
    # Performance metrics (to be updated after video is published)
    views = sa.Column(sa.Integer, default=0)
    likes = sa.Column(sa.Integer, default=0)
    comments = sa.Column(sa.Integer, default=0)
    # Timestamps
    created_at = sa.Column(sa.DateTime, default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, default=sa.func.now(), onupdate=sa.func.now())

class ContentBlacklist(Base):
    __tablename__ = 'content_blacklist'
    
    id = sa.Column(sa.Integer, primary_key=True)
    topic = sa.Column(sa.String, unique=True, nullable=False)
    reason = sa.Column(sa.String)
    created_at = sa.Column(sa.DateTime, default=sa.func.now())
