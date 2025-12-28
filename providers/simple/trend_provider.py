# bot/providers/simple/trend_provider.py
"""
Simple trend provider using free APIs
"""

import asyncio
import aiohttp
from typing import List, Optional
import json
from datetime import datetime, timedelta

from bot.providers.base import BaseTrendProvider, Trend

class SimpleTrendProvider(BaseTrendProvider):
    """Simple trend provider using free APIs"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.session = None
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
    
    async def initialize(self):
        """Initialize provider"""
        self.session = aiohttp.ClientSession()
    
    async def get_trends(self, category: Optional[str] = None, 
                        limit: int = 10) -> List[Trend]:
        """Get trends from multiple free sources"""
        if not self.session:
            await self.initialize()
        
        # Check cache first
        cache_key = f"trends_{category}_{datetime.now().hour}"
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_ttl:
                return cached_data[:limit]
        
        # Gather from multiple sources concurrently
        tasks = [
            self._get_reddit_trends(category),
            self._get_google_trends(category),
            self._get_wikipedia_trends(),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine and deduplicate
        all_trends = []
        for result in results:
            if isinstance(result, list):
                all_trends.extend(result)
        
        # Score and sort trends
        scored_trends = self._score_trends(all_trends)
        
        # Cache results
        self.cache[cache_key] = (datetime.now(), scored_trends)
        
        return scored_trends[:limit]
    
    async def _get_reddit_trends(self, category: Optional[str] = None) -> List[Trend]:
        """Get trends from Reddit"""
        subreddits = {
            'science': 'science',
            'technology': 'technology',
            'history': 'history',
            'psychology': 'psychology',
            None: 'todayilearned'  # Default
        }
        
        subreddit = subreddits.get(category, 'todayilearned')
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=15"
        
        try:
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    posts = data['data']['children']
                    
                    trends = []
                    for post in posts:
                        post_data = post['data']
                        title = post_data.get('title', '')
                        
                        # Filter out meta-posts
                        if any(x in title.lower() for x in ['meta', 'modpost', 'weekly']):
                            continue
                        
                        score = min(100, (post_data.get('score', 0) / 1000) * 100)
                        
                        trend = Trend(
                            topic=self._clean_title(title),
                            score=score,
                            category=category or 'general',
                            source=f"reddit_r/{subreddit}",
                            metadata={
                                'url': f"https://reddit.com{post_data.get('permalink', '')}",
                                'upvotes': post_data.get('score', 0),
                                'comments': post_data.get('num_comments', 0)
                            }
                        )
                        trends.append(trend)
                    
                    return trends
        except Exception as e:
            print(f"Reddit trend error: {e}")
        
        return []
    
    async def _get_google_trends(self, category: Optional[str] = None) -> List[Trend]:
        """Get trends using Google Trends (via pytrends async)"""
        try:
            # Run pytrends in thread pool to avoid blocking
            return await asyncio.get_event_loop().run_in_executor(
                None, self._sync_google_trends, category
            )
        except Exception as e:
            print(f"Google Trends error: {e}")
            return []
    
    def _sync_google_trends(self, category: Optional[str] = None) -> List[Trend]:
        """Synchronous Google Trends fetching"""
        try:
            from pytrends.request import TrendReq
            
            pytrends = TrendReq(hl='en-US', tz=360, timeout=(10,25))
            
            # Build payload
            timeframe = 'now 7-d'
            cat = self._category_to_google_cat(category)
            
            # Get trending searches
            df = pytrends.trending_searches(pn='united_states')
            
            trends = []
            for idx, topic in enumerate(df[0].head(10).tolist()):
                score = 100 - (idx * 10)  # Higher position = higher score
                
                trend = Trend(
                    topic=str(topic),
                    score=score,
                    category=category or 'general',
                    source="google_trends",
                    metadata={
                        'position': idx + 1,
                        'timeframe': timeframe
                    }
                )
                trends.append(trend)
            
            return trends
        except ImportError:
            print("pytrends not installed")
            return []
    
    async def _get_wikipedia_trends(self) -> List[Trend]:
        """Get trending Wikipedia articles"""
        try:
            # Use Wikipedia API to get random featured articles
            url = "https://en.wikipedia.org/api/rest_v1/page/random/summary"
            
            trends = []
            for _ in range(5):  # Get 5 random articles
                async with self.session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Skip non-content pages
                        if data.get('type') != 'standard':
                            continue
                        
                        title = data.get('title', '')
                        extract = data.get('extract', '')
                        
                        # Score based on extract length (proxy for interest)
                        score = min(100, len(extract) / 10)
                        
                        trend = Trend(
                            topic=f"The story of {title}",
                            score=score,
                            category=self._categorize_text(title + ' ' + extract),
                            source="wikipedia",
                            metadata={
                                'url': data.get('content_urls', {}).get('desktop', {}).get('page', ''),
                                'extract': extract[:200] + '...' if len(extract) > 200 else extract
                            }
                        )
                        trends.append(trend)
                
                await asyncio.sleep(0.5)  # Rate limiting
            
            return trends
        except Exception as e:
            print(f"Wikipedia error: {e}")
            return []
    
    async def validate_trend(self, trend: Trend) -> Dict[str, Any]:
        """Simple validation - just check basic criteria"""
        # In MCP version, this would query multiple sources
        # For simple version, just do basic checks
        
        validation = {
            'is_valid': True,
            'confidence': 0.7,
            'checks_passed': [],
            'checks_failed': [],
            'suggestions': []
        }
        
        # Basic checks
        if len(trend.topic) < 10:
            validation['is_valid'] = False
            validation['checks_failed'].append('topic_too_short')
        
        if len(trend.topic) > 200:
            validation['checks_failed'].append('topic_too_long')
            validation['suggestions'].append('Consider shortening the topic')
        
        # Check for controversial keywords
        controversial = ['proven', 'secret', 'they dont want', 'shocking']
        if any(word in trend.topic.lower() for word in controversial):
            validation['checks_failed'].append('controversial_language')
            validation['confidence'] *= 0.8
        
        # Update confidence
        if validation['checks_failed']:
            validation['confidence'] *= 0.9
        
        return validation
    
    def _clean_title(self, title: str) -> str:
        """Clean Reddit/TIL titles"""
        # Remove TIL prefix
        for prefix in ['TIL', 'Til', 'til', 'Today I learned']:
            if title.startswith(prefix + ' '):
                title = title[len(prefix):].strip()
                if title.lower().startswith('that '):
                    title = title[5:].strip()
                if title.lower().startswith('about '):
                    title = title[6:].strip()
        
        # Remove brackets and extra punctuation
        title = title.replace('[', '').replace(']', '')
        title = title.strip(' :.-')
        
        # Capitalize first letter
        if title and title[0].islower():
            title = title[0].upper() + title[1:]
        
        return title
    
    def _category_to_google_cat(self, category: Optional[str] = None) -> int:
        """Convert category to Google Trends category code"""
        categories = {
            'science': 396,
            'technology': 188,
            'history': 67,
            'psychology': 1082,
            'space': 191,
            'health': 45
        }
        return categories.get(category, 0)
    
    def _categorize_text(self, text: str) -> str:
        """Categorize text based on keywords"""
        text_lower = text.lower()
        
        categories = {
            'science': ['scientist', 'research', 'study', 'experiment', 
                       'discovery', 'physics', 'chemistry', 'biology'],
            'technology': ['tech', 'computer', 'software', 'app', 'phone',
                          'internet', 'digital', 'code', 'programming'],
            'history': ['history', 'historical', 'ancient', 'century', 'war',
                       'empire', 'civilization', 'medieval'],
            'space': ['space', 'nasa', 'planet', 'star', 'galaxy', 'universe',
                     'astronaut', 'orbit', 'solar system'],
        }
        
        for category, keywords in categories.items():
            if any(keyword in text_lower for keyword in keywords):
                return category
        
        return 'general'
    
    def _score_trends(self, trends: List[Trend]) -> List[Trend]:
        """Score and sort trends"""
        # Simple scoring algorithm
        scored = []
        for trend in trends:
            # Base score from source
            base_score = trend.score
            
            # Boost for certain sources
            source_boost = {
                'google_trends': 1.2,
                'wikipedia': 1.1,
                'reddit': 1.0
            }.get(trend.source, 1.0)
            
            # Penalize very short/long topics
            length = len(trend.topic)
            if length < 15:
                length_penalty = 0.8
            elif length > 100:
                length_penalty = 0.9
            else:
                length_penalty = 1.0
            
            # Calculate final score
            final_score = base_score * source_boost * length_penalty
            trend.score = min(100, final_score)
            
            scored.append(trend)
        
        # Sort by score descending
        return sorted(scored, key=lambda x: x.score, reverse=True)
