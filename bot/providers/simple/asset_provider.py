"""
Simple asset provider for ShortSync Pro.

Gathers stock videos and images from free APIs (Pexels, Unsplash, Pixabay).
"""

import asyncio
import aiohttp
from typing import List, Dict, Any, Optional, Tuple
import random
from datetime import datetime
import json

from bot.providers.base import BaseAssetProvider, Asset

class SimpleAssetProvider(BaseAssetProvider):
    """Simple asset provider using free stock media APIs"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pexels_api_key = config.get('pexels_api_key')
        self.unsplash_api_key = config.get('unsplash_api_key')
        self.pixabay_api_key = config.get('pixabay_api_key')
        self.session = None
        self.cache = {}
        self.cache_ttl = 1800  # 30 minutes
        
        # API rate limits (requests per hour)
        self.rate_limits = {
            'pexels': 200,
            'unsplash': 50,
            'pixabay': 100
        }
        
        # API usage tracking
        self.api_usage = {
            'pexels': {'count': 0, 'reset_time': None},
            'unsplash': {'count': 0, 'reset_time': None},
            'pixabay': {'count': 0, 'reset_time': None}
        }
    
    async def initialize(self):
        """Initialize provider"""
        self.session = aiohttp.ClientSession()
    
    async def search_videos(self, query: str, 
                          duration_range: Tuple[int, int] = (3, 10),
                          limit: int = 5) -> List[Asset]:
        """Search for video assets matching query and duration"""
        if not self.session:
            await self.initialize()
        
        # Check cache first
        cache_key = f"videos_{query}_{duration_range}_{limit}"
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_ttl:
                return cached_data[:limit]
        
        all_videos = []
        
        # Try Pexels first (best for videos)
        if self.pexels_api_key and self._can_make_request('pexels'):
            videos = await self._search_pexels_videos(query, duration_range, limit)
            all_videos.extend(videos)
            self._record_api_usage('pexels')
        
        # Try Pixabay as fallback
        if len(all_videos) < limit and self.pixabay_api_key and self._can_make_request('pixabay'):
            videos = await self._search_pixabay_videos(query, duration_range, limit - len(all_videos))
            all_videos.extend(videos)
            self._record_api_usage('pixabay')
        
        # Filter by duration
        filtered_videos = []
        min_duration, max_duration = duration_range
        
        for video in all_videos:
            video_duration = video.metadata.get('duration', 0)
            if min_duration <= video_duration <= max_duration:
                filtered_videos.append(video)
        
        # Cache results
        self.cache[cache_key] = (datetime.now(), filtered_videos)
        
        return filtered_videos[:limit]
    
    async def search_images(self, query: str, 
                          limit: int = 10) -> List[Asset]:
        """Search for image assets matching query"""
        if not self.session:
            await self.initialize()
        
        # Check cache first
        cache_key = f"images_{query}_{limit}"
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_ttl:
                return cached_data[:limit]
        
        all_images = []
        
        # Try Unsplash first (best for high-quality photos)
        if self.unsplash_api_key and self._can_make_request('unsplash'):
            images = await self._search_unsplash_images(query, limit)
            all_images.extend(images)
            self._record_api_usage('unsplash')
        
        # Try Pexels as fallback
        if len(all_images) < limit and self.pexels_api_key and self._can_make_request('pexels'):
            remaining = limit - len(all_images)
            images = await self._search_pexels_images(query, remaining)
            all_images.extend(images)
            self._record_api_usage('pexels')
        
        # Try Pixabay as last resort
        if len(all_images) < limit and self.pixabay_api_key and self._can_make_request('pixabay'):
            remaining = limit - len(all_images)
            images = await self._search_pixabay_images(query, remaining)
            all_images.extend(images)
            self._record_api_usage('pixabay')
        
        # Cache results
        self.cache[cache_key] = (datetime.now(), all_images)
        
        return all_images[:limit]
    
    async def _search_pexels_videos(self, query: str, 
                                  duration_range: Tuple[int, int],
                                  limit: int) -> List[Asset]:
        """Search for videos on Pexels"""
        try:
            url = "https://api.pexels.com/videos/search"
            headers = {
                "Authorization": self.pexels_api_key,
                "Content-Type": "application/json"
            }
            
            params = {
                "query": query,
                "per_page": min(limit, 15),
                "page": 1,
                "orientation": "portrait"  # For YouTube Shorts
            }
            
            async with self.session.get(url, headers=headers, params=params, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    videos = data.get('videos', [])
                    
                    assets = []
                    for video in videos:
                        # Get the best quality video file
                        video_files = video.get('video_files', [])
                        if not video_files:
                            continue
                        
                        # Prefer HD quality
                        hd_files = [f for f in video_files if f.get('quality') == 'hd']
                        if hd_files:
                            best_file = hd_files[0]
                        else:
                            best_file = video_files[0]
                        
                        # Get duration
                        duration = video.get('duration', 0)
                        
                        asset = Asset(
                            url=best_file.get('link', ''),
                            type='video',
                            license='pexels',
                            duration_seconds=duration,
                            metadata={
                                'id': video.get('id'),
                                'width': best_file.get('width', 0),
                                'height': best_file.get('height', 0),
                                'duration': duration,
                                'user': video.get('user', {}).get('name', ''),
                                'url': video.get('url', ''),
                                'tags': [tag.get('title', '') for tag in video.get('tags', [])],
                                'source': 'pexels'
                            }
                        )
                        assets.append(asset)
                    
                    return assets
                
        except Exception as e:
            print(f"Pexels videos error: {e}")
        
        return []
    
    async def _search_pixabay_videos(self, query: str,
                                   duration_range: Tuple[int, int],
                                   limit: int) -> List[Asset]:
        """Search for videos on Pixabay"""
        try:
            url = "https://pixabay.com/api/videos/"
            params = {
                "key": self.pixabay_api_key,
                "q": query,
                "per_page": min(limit, 20),
                "page": 1,
                "orientation": "vertical",
                "video_type": "film"  # Avoid animations
            }
            
            async with self.session.get(url, params=params, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    hits = data.get('hits', [])
                    
                    assets = []
                    for hit in hits:
                        # Get video URL
                        videos = hit.get('videos', {})
                        if not videos:
                            continue
                        
                        # Prefer medium size
                        video_info = videos.get('medium', {})
                        if not video_info:
                            # Try large or small
                            video_info = videos.get('large', videos.get('small', {}))
                        
                        if not video_info:
                            continue
                        
                        duration = hit.get('duration', 0)
                        
                        asset = Asset(
                            url=video_info.get('url', ''),
                            type='video',
                            license='pixabay',
                            duration_seconds=duration,
                            metadata={
                                'id': hit.get('id'),
                                'width': video_info.get('width', 0),
                                'height': video_info.get('height', 0),
                                'duration': duration,
                                'user': hit.get('user', ''),
                                'tags': hit.get('tags', '').split(', '),
                                'views': hit.get('views', 0),
                                'downloads': hit.get('downloads', 0),
                                'source': 'pixabay'
                            }
                        )
                        assets.append(asset)
                    
                    return assets
                
        except Exception as e:
            print(f"Pixabay videos error: {e}")
        
        return []
    
    async def _search_unsplash_images(self, query: str, limit: int) -> List[Asset]:
        """Search for images on Unsplash"""
        try:
            url = "https://api.unsplash.com/search/photos"
            headers = {
                "Authorization": f"Client-ID {self.unsplash_api_key}",
                "Accept-Version": "v1"
            }
            
            params = {
                "query": query,
                "per_page": min(limit, 30),
                "page": 1,
                "orientation": "portrait"
            }
            
            async with self.session.get(url, headers=headers, params=params, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get('results', [])
                    
                    assets = []
                    for result in results:
                        urls = result.get('urls', {})
                        
                        asset = Asset(
                            url=urls.get('regular', ''),
                            type='image',
                            license='unsplash',
                            metadata={
                                'id': result.get('id'),
                                'width': result.get('width', 0),
                                'height': result.get('height', 0),
                                'user': result.get('user', {}).get('name', ''),
                                'user_url': result.get('user', {}).get('links', {}).get('html', ''),
                                'description': result.get('description', ''),
                                'alt_description': result.get('alt_description', ''),
                                'color': result.get('color', ''),
                                'likes': result.get('likes', 0),
                                'downloads': result.get('downloads', 0),
                                'raw_url': urls.get('raw', ''),
                                'full_url': urls.get('full', ''),
                                'small_url': urls.get('small', ''),
                                'thumb_url': urls.get('thumb', ''),
                                'source': 'unsplash'
                            }
                        )
                        assets.append(asset)
                    
                    return assets
                
        except Exception as e:
            print(f"Unsplash images error: {e}")
        
        return []
    
    async def _search_pexels_images(self, query: str, limit: int) -> List[Asset]:
        """Search for images on Pexels"""
        try:
            url = "https://api.pexels.com/v1/search"
            headers = {
                "Authorization": self.pexels_api_key,
                "Content-Type": "application/json"
            }
            
            params = {
                "query": query,
                "per_page": min(limit, 15),
                "page": 1,
                "orientation": "portrait"
            }
            
            async with self.session.get(url, headers=headers, params=params, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    photos = data.get('photos', [])
                    
                    assets = []
                    for photo in photos:
                        src = photo.get('src', {})
                        
                        asset = Asset(
                            url=src.get('large', ''),
                            type='image',
                            license='pexels',
                            metadata={
                                'id': photo.get('id'),
                                'width': photo.get('width', 0),
                                'height': photo.get('height', 0),
                                'photographer': photo.get('photographer', ''),
                                'photographer_url': photo.get('photographer_url', ''),
                                'avg_color': photo.get('avg_color', ''),
                                'original_url': src.get('original', ''),
                                'large2x_url': src.get('large2x', ''),
                                'medium_url': src.get('medium', ''),
                                'small_url': src.get('small', ''),
                                'portrait_url': src.get('portrait', ''),
                                'landscape_url': src.get('landscape', ''),
                                'tiny_url': src.get('tiny', ''),
                                'alt': photo.get('alt', ''),
                                'source': 'pexels'
                            }
                        )
                        assets.append(asset)
                    
                    return assets
                
        except Exception as e:
            print(f"Pexels images error: {e}")
        
        return []
    
    async def _search_pixabay_images(self, query: str, limit: int) -> List[Asset]:
        """Search for images on Pixabay"""
        try:
            url = "https://pixabay.com/api/"
            params = {
                "key": self.pixabay_api_key,
                "q": query,
                "per_page": min(limit, 20),
                "page": 1,
                "orientation": "vertical",
                "image_type": "photo"
            }
            
            async with self.session.get(url, params=params, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    hits = data.get('hits', [])
                    
                    assets = []
                    for hit in hits:
                        asset = Asset(
                            url=hit.get('largeImageURL', ''),
                            type='image',
                            license='pixabay',
                            metadata={
                                'id': hit.get('id'),
                                'width': hit.get('imageWidth', 0),
                                'height': hit.get('imageHeight', 0),
                                'user': hit.get('user', ''),
                                'tags': hit.get('tags', '').split(', '),
                                'views': hit.get('views', 0),
                                'downloads': hit.get('downloads', 0),
                                'likes': hit.get('likes', 0),
                                'comments': hit.get('comments', 0),
                                'preview_url': hit.get('previewURL', ''),
                                'webformat_url': hit.get('webformatURL', ''),
                                'fullhd_url': hit.get('fullHDURL', ''),
                                'image_url': hit.get('imageURL', ''),
                                'source': 'pixabay'
                            }
                        )
                        assets.append(asset)
                    
                    return assets
                
        except Exception as e:
            print(f"Pixabay images error: {e}")
        
        return []
    
    def _can_make_request(self, api_name: str) -> bool:
        """Check if we can make a request to the API based on rate limits"""
        usage = self.api_usage.get(api_name)
        if not usage:
            return True
        
        # Check if hour has passed since last reset
        reset_time = usage.get('reset_time')
        if reset_time and (datetime.now() - reset_time).seconds >= 3600:
            usage['count'] = 0
            usage['reset_time'] = datetime.now()
            return True
        
        # Check if under limit
        limit = self.rate_limits.get(api_name, 50)
        return usage.get('count', 0) < limit
    
    def _record_api_usage(self, api_name: str):
        """Record API usage for rate limiting"""
        usage = self.api_usage.get(api_name)
        if usage:
            if not usage.get('reset_time'):
                usage['reset_time'] = datetime.now()
            
            usage['count'] = usage.get('count', 0) + 1
    
    async def get_asset_by_id(self, asset_id: str, source: str) -> Optional[Asset]:
        """Get specific asset by ID and source"""
        if not self.session:
            await self.initialize()
        
        cache_key = f"asset_{source}_{asset_id}"
        if cache_key in self.cache:
            cached_time, cached_asset = self.cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_ttl:
                return cached_asset
        
        asset = None
        
        if source == 'pexels' and self.pexels_api_key:
            asset = await self._get_pexels_asset(asset_id)
        elif source == 'unsplash' and self.unsplash_api_key:
            asset = await self._get_unsplash_asset(asset_id)
        elif source == 'pixabay' and self.pixabay_api_key:
            asset = await self._get_pixabay_asset(asset_id)
        
        if asset:
            self.cache[cache_key] = (datetime.now(), asset)
        
        return asset
    
    async def _get_pexels_asset(self, asset_id: str) -> Optional[Asset]:
        """Get Pexels asset by ID"""
        try:
            # Determine if it's a photo or video
            # This is simplified - in reality you'd need to know the type
            # For now, try photo first
            url = f"https://api.pexels.com/v1/photos/{asset_id}"
            headers = {"Authorization": self.pexels_api_key}
            
            async with self.session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    photo = await response.json()
                    src = photo.get('src', {})
                    
                    return Asset(
                        url=src.get('large', ''),
                        type='image',
                        license='pexels',
                        metadata={
                            'id': photo.get('id'),
                            'width': photo.get('width', 0),
                            'height': photo.get('height', 0),
                            'photographer': photo.get('photographer', ''),
                            'source': 'pexels'
                        }
                    )
                
        except Exception as e:
            print(f"Pexels asset error: {e}")
        
        return None
    
    async def _get_unsplash_asset(self, asset_id: str) -> Optional[Asset]:
        """Get Unsplash asset by ID"""
        try:
            url = f"https://api.unsplash.com/photos/{asset_id}"
            headers = {"Authorization": f"Client-ID {self.unsplash_api_key}"}
            
            async with self.session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    photo = await response.json()
                    urls = photo.get('urls', {})
                    
                    return Asset(
                        url=urls.get('regular', ''),
                        type='image',
                        license='unsplash',
                        metadata={
                            'id': photo.get('id'),
                            'width': photo.get('width', 0),
                            'height': photo.get('height', 0),
                            'user': photo.get('user', {}).get('name', ''),
                            'source': 'unsplash'
                        }
                    )
                
        except Exception as e:
            print(f"Unsplash asset error: {e}")
        
        return None
    
    async def _get_pixabay_asset(self, asset_id: str) -> Optional[Asset]:
        """Get Pixabay asset by ID"""
        try:
            url = f"https://pixabay.com/api/"
            params = {
                "key": self.pixabay_api_key,
                "id": asset_id
            }
            
            async with self.session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    hits = data.get('hits', [])
                    if hits:
                        hit = hits[0]
                        
                        return Asset(
                            url=hit.get('largeImageURL', ''),
                            type='image',
                            license='pixabay',
                            metadata={
                                'id': hit.get('id'),
                                'width': hit.get('imageWidth', 0),
                                'height': hit.get('imageHeight', 0),
                                'user': hit.get('user', ''),
                                'source': 'pixabay'
                            }
                        )
                
        except Exception as e:
            print(f"Pixabay asset error: {e}")
        
        return None
    
    async def close(self):
        """Close provider resources"""
        if self.session:
            await self.session.close()
