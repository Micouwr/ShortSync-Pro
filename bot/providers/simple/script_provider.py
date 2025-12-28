# bot/providers/simple/script_provider.py
"""
Simple script generator using free AI APIs
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional
import re

from bot.providers.base import BaseScriptProvider, Script

class SimpleScriptProvider(BaseScriptProvider):
    """Simple script generator using Cohere/HuggingFace"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cohere_api_key = config.get('cohere_api_key')
        self.hf_api_key = config.get('hf_api_key')
        self.session = None
    
    async def initialize(self):
        """Initialize provider"""
        self.session = aiohttp.ClientSession()
    
    async def generate_script(self, topic: str, 
                            duration_seconds: int = 45) -> Script:
        """Generate script for topic"""
        if not self.session:
            await self.initialize()
        
        # Try Cohere first (free tier available)
        if self.cohere_api_key:
            script = await self._generate_with_cohere(topic, duration_seconds)
            if script:
                return script
        
        # Fallback to HuggingFace
        if self.hf_api_key:
            script = await self._generate_with_huggingface(topic, duration_seconds)
            if script:
                return script
        
        # Ultimate fallback: template-based generation
        return self._generate_with_template(topic, duration_seconds)
    
    async def _generate_with_cohere(self, topic: str, 
                                  duration_seconds: int) -> Optional[Script]:
        """Generate script using Cohere API"""
        try:
            url = "https://api.cohere.ai/v1/generate"
            headers = {
                "Authorization": f"Bearer {self.cohere_api_key}",
                "Content-Type": "application/json"
            }
            
            # Estimate words needed (~2 words per second)
            target_words = duration_seconds * 2
            
            prompt = f"""Create a short, engaging educational script for a YouTube Short.
Topic: {topic}
Requirements:
- Maximum {target_words} words
- Clear, simple language
- Hook in first 3 seconds
- 3 key points maximum
- Call to action at end
- Optimized for vertical video

Format:
[Title]: Catchy title
[Hook]: Attention-grabbing opening
[Point 1]: First key point
[Point 2]: Second key point
[Point 3]: Third key point
[CTA]: Call to action
[Hashtags]: 3 relevant hashtags

Script:"""
            
            data = {
                "model": "command",
                "prompt": prompt,
                "max_tokens": 500,
                "temperature": 0.7,
                "k": 0,
                "stop_sequences": [],
                "return_likelihoods": "NONE"
            }
            
            async with self.session.post(url, headers=headers, 
                                       json=data, timeout=30) as response:
                if response.status == 200:
                    result = await response.json()
                    text = result['generations'][0]['text']
                    return self._parse_script(text, topic, duration_seconds)
        
        except Exception as e:
            print(f"Cohere error: {e}")
        
        return None
    
    async def _generate_with_huggingface(self, topic: str,
                                       duration_seconds: int) -> Optional[Script]:
        """Generate script using HuggingFace API"""
        try:
            url = "https://api-inference.huggingface.co/models/gpt2"
            headers = {"Authorization": f"Bearer {self.hf_api_key}"}
            
            prompt = f"Educational script about {topic} for YouTube Short:\n"
            
            data = {
                "inputs": prompt,
                "parameters": {
                    "max_length": 300,
                    "temperature": 0.9,
                    "do_sample": True
                }
            }
            
            async with self.session.post(url, headers=headers,
                                       json=data, timeout=30) as response:
                if response.status == 200:
                    result = await response.json()
                    if isinstance(result, list) and 'generated_text' in result[0]:
                        text = result[0]['generated_text']
                        return self._parse_script(text, topic, duration_seconds)
        
        except Exception as e:
            print(f"HuggingFace error: {e}")
        
        return None
    
    def _generate_with_template(self, topic: str,
                              duration_seconds: int) -> Script:
        """Template-based fallback script generation"""
        
        templates = [
            f"Did you know about {topic}? It's more fascinating than you think. "
            f"Here are 3 quick facts that will surprise you. "
            f"Number 1... Number 2... And number 3... "
            f"Like for more amazing facts!",
            
            f"The surprising truth about {topic}. "
            f"Most people get this wrong. Here's what actually happens. "
            f"First... Second... And here's the most important part... "
            f"Subscribe for more insights!",
            
            f"Here's a quick explainer about {topic}. "
            f"In just 45 seconds, you'll understand it completely. "
            f"Let's break it down. Step one... Step two... Step three... "
            f"Got it? Like if you learned something new!"
        ]
        
        import random
        content = random.choice(templates)
        
        # Simple title generation
        title = f"About {topic}" if len(topic) < 30 else "Quick Facts"
        
        return Script(
            title=title,
            content=content,
            duration_seconds=duration_seconds,
            metadata={
                'generator': 'template',
                'words': len(content.split()),
                'template_used': templates.index(content) if content in templates else -1
            }
        )
    
    def _parse_script(self, text: str, topic: str,
                    duration_seconds: int) -> Script:
        """Parse generated text into Script object"""
        # Extract title
        title_match = re.search(r'\[Title\]:\s*(.+?)(?=\n|$)', text)
        title = title_match.group(1).strip() if title_match else f"About {topic}"
        
        # Extract content (everything after [Script]: or use full text)
        script_match = re.search(r'\[Script\]:\s*(.+?)(?=\n\[|$)', text, re.DOTALL)
        if script_match:
            content = script_match.group(1).strip()
        else:
            # Try to extract just the script part
            lines = text.split('\n')
            script_lines = []
            in_script = False
            for line in lines:
                if '[Script]:' in line:
                    in_script = True
                    continue
                if in_script and line.strip() and not line.startswith('['):
                    script_lines.append(line.strip())
            content = ' '.join(script_lines) if script_lines else text
        
        # Clean up content
        content = re.sub(r'\[.*?\]', '', content)  # Remove brackets
        content = content.replace('\n', ' ').strip()
        
        # Ensure word count is reasonable
        words = content.split()
        if len(words) > 200:
            content = ' '.join(words[:200]) + '...'
        
        return Script(
            title=title[:100],  # Truncate if too long
            content=content,
            duration_seconds=duration_seconds,
            metadata={
                'generator': 'ai',
                'words': len(content.split()),
                'original_text': text[:500]  # Store for debugging
            }
        )
    
    async def improve_script(self, script: Script) -> Script:
        """Simple script improvement - just clean up"""
        # Remove excessive punctuation
        content = script.content
        content = re.sub(r'\.{3,}', '...', content)  # Normalize ellipsis
        content = re.sub(r'\!{2,}', '!', content)    # Normalize exclamation
        content = re.sub(r'\?{2,}', '?', content)    # Normalize question
        
        # Ensure ends with punctuation
        if not content[-1] in '.!?':
            content += '.'
        
        script.content = content
        script.metadata['improved'] = True
        return script
