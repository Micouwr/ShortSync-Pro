# Add this import at the top of bot/database/manager.py
from .models import (
    Video, Job, PerformanceMetric, Channel, ContentTemplate,
    create_video, create_job, create_performance_metric,
    create_channel, create_content_template,
    create_tables_sql, create_indices_sql
)

# In the create_tables method, replace the SQL with:
async def create_tables(self):
    """Create all necessary tables using model schemas"""
    
    # Get table creation SQL from models
    table_sqls = create_tables_sql()
    
    for sql in table_sqls:
        await self.db.execute(sql)
    
    await self.db.commit()

# In the create_indices method, replace with:
async def create_indices(self):
    """Create database indices for performance"""
    
    # Get index creation SQL from models
    index_sqls = create_indices_sql()
    
    for sql in index_sqls:
        await self.db.execute(sql)
    
    await self.db.commit()

# Update save_video method to use Video model:
async def save_video(self, video_data: dict) -> str:
    """Save video information to database using Video model"""
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
    
    return video.id

# Add helper method to get video as model object:
async def get_video_model(self, video_id: str) -> Optional[Video]:
    """Get video as Video model object"""
    cursor = await self.db.execute('SELECT * FROM videos WHERE id = ?', (video_id,))
    row = await cursor.fetchone()
    
    if row:
        # Convert row to dict
        video_dict = dict(row)
        return Video.from_dict(video_dict)
    
    return None
