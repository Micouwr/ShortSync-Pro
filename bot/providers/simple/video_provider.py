"""
Simple video provider for ShortSync Pro.

Assembles videos from scripts, voiceovers, and assets using MoviePy.
Creates YouTube Shorts formatted videos (9:16 aspect ratio).
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import tempfile
import random
from datetime import datetime
import hashlib
import json

from bot.providers.base import BaseVideoProvider, Script, Asset

class SimpleVideoProvider(BaseVideoProvider):
    """Simple video provider using MoviePy for assembly"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cache_dir = Path(config.get('cache_dir', 'data/video_cache'))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Video configuration
        self.video_config = {
            'resolution': (1080, 1920),  # 9:16 vertical
            'fps': 30,
            'codec': 'libx264',
            'audio_codec': 'aac',
            'temp_dir': Path(config.get('temp_dir', 'temp/video')),
            'max_video_duration': 58,  # YouTube Shorts limit
            'min_video_duration': 15,   # Minimum for engagement
        }
        
        # Style templates
        self.templates = {
            'educational': {
                'background_color': (10, 20, 30),  # Dark blue
                'text_color': (255, 255, 255),     # White
                'highlight_color': (0, 200, 255),  # Cyan
                'font_size': 70,
                'animation_style': 'fade',
                'transition_duration': 0.5
            },
            'news': {
                'background_color': (20, 20, 20),  # Dark gray
                'text_color': (255, 255, 255),     # White
                'highlight_color': (255, 50, 50),  # Red
                'font_size': 65,
                'animation_style': 'slide',
                'transition_duration': 0.3
            },
            'entertainment': {
                'background_color': (30, 10, 20),  # Dark purple
                'text_color': (255, 255, 255),     # White
                'highlight_color': (255, 200, 0),  # Yellow
                'font_size': 75,
                'animation_style': 'zoom',
                'transition_duration': 0.7
            }
        }
    
    async def initialize(self):
        """Initialize provider (check dependencies)"""
        # Check if MoviePy is available
        try:
            import moviepy.editor as mp
            self.moviepy_available = True
        except ImportError:
            print("MoviePy not installed. Video assembly will be limited.")
            self.moviepy_available = False
        
        # Check if PIL is available
        try:
            from PIL import Image, ImageDraw, ImageFont
            self.pil_available = True
        except ImportError:
            print("PIL not installed. Text rendering will be limited.")
            self.pil_available = False
        
        # Create temp directory
        self.video_config['temp_dir'].mkdir(parents=True, exist_ok=True)
    
    async def assemble_video(self, script: Script,
                           voiceover_path: Path,
                           assets: List[Asset],
                           output_path: Optional[Path] = None) -> Path:
        """Assemble video from components"""
        if not self.moviepy_available:
            raise ImportError("MoviePy is required for video assembly")
        
        # Create output path if not provided
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = self.video_config['temp_dir'] / f"video_{timestamp}.mp4"
        
        # Check cache first
        cache_key = self._generate_cache_key(script, voiceover_path, assets)
        cached_file = self.cache_dir / f"{cache_key}.mp4"
        
        if cached_file.exists():
            # Return cached file or copy to output path
            if output_path != cached_file:
                return await self._copy_file(cached_file, output_path)
            return cached_file
        
        print(f"Assembling video: {output_path}")
        
        try:
            import moviepy.editor as mp
            from moviepy.video.fx.all import resize, fadein, fadeout
            
            # Create temporary working directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Load voiceover audio
                print("Loading voiceover...")
                audio_clip = mp.AudioFileClip(str(voiceover_path))
                
                # Get voiceover duration
                voiceover_duration = audio_clip.duration
                
                # Ensure video duration is within limits
                target_duration = min(
                    max(voiceover_duration, self.video_config['min_video_duration']),
                    self.video_config['max_video_duration']
                )
                
                # Trim or extend audio if needed
                if voiceover_duration != target_duration:
                    if voiceover_duration > target_duration:
                        audio_clip = audio_clip.subclip(0, target_duration)
                    else:
                        # Add silence to end (not ideal but works)
                        from moviepy.audio.AudioClip import CompositeAudioClip
                        from moviepy.audio.io.AudioFileClip import AudioFileClip
                        
                        silence = mp.AudioClip(lambda t: 0, duration=target_duration - voiceover_duration)
                        audio_clip = CompositeAudioClip([audio_clip, silence])
                
                # Prepare visual assets
                print("Preparing visual assets...")
                video_clips = await self._prepare_visual_clips(
                    script, assets, target_duration, temp_path
                )
                
                if not video_clips:
                    # Create simple text-based video as fallback
                    video_clips = await self._create_text_video(
                        script, target_duration, temp_path
                    )
                
                # Combine video clips
                print("Combining video clips...")
                if len(video_clips) > 1:
                    final_video = mp.concatenate_videoclips(
                        video_clips,
                        method="compose",
                        padding=0
                    )
                else:
                    final_video = video_clips[0]
                
                # Add audio
                print("Adding audio...")
                final_video = final_video.set_audio(audio_clip)
                
                # Set duration exactly
                final_video = final_video.set_duration(target_duration)
                
                # Resize to target resolution
                print("Resizing to target resolution...")
                target_width, target_height = self.video_config['resolution']
                final_video = resize(final_video, (target_width, target_height))
                
                # Write output file
                print(f"Writing video to {output_path}...")
                final_video.write_videofile(
                    str(output_path),
                    fps=self.video_config['fps'],
                    codec=self.video_config['codec'],
                    audio_codec=self.video_config['audio_codec'],
                    threads=4,
                    preset='medium',
                    ffmpeg_params=['-movflags', '+faststart']  # For web playback
                )
                
                # Clean up clips
                for clip in video_clips:
                    clip.close()
                audio_clip.close()
                final_video.close()
                
                # Cache the result
                await self._copy_file(output_path, cached_file)
                
                print(f"Video assembly complete: {output_path}")
                return output_path
                
        except Exception as e:
            print(f"Video assembly error: {e}")
            raise
    
    async def _prepare_visual_clips(self, script: Script,
                                  assets: List[Asset],
                                  duration: float,
                                  temp_path: Path) -> List[Any]:
        """Prepare visual clips from assets and script"""
        import moviepy.editor as mp
        
        clips = []
        
        # Group assets by type
        video_assets = [a for a in assets if a.type == 'video']
        image_assets = [a for a in assets if a.type == 'image']
        
        # Calculate timing
        total_segments = len(script.content.split('.')) + len(video_assets) + max(1, len(image_assets))
        segment_duration = duration / max(1, total_segments)
        
        current_time = 0
        
        # Add intro segment
        if current_time < duration:
            intro_clip = await self._create_intro_clip(script.title, segment_duration, temp_path)
            if intro_clip:
                clips.append(intro_clip)
                current_time += segment_duration
        
        # Add video assets
        for video_asset in video_assets:
            if current_time >= duration:
                break
                
            video_clip = await self._create_video_asset_clip(video_asset, segment_duration, temp_path)
            if video_clip:
                clips.append(video_clip)
                current_time += segment_duration
        
        # Add image assets with text
        for i, sentence in enumerate(self._split_script(script.content)):
            if current_time >= duration or i >= len(image_assets):
                break
                
            image_asset = image_assets[i % len(image_assets)]
            text_clip = await self._create_text_image_clip(
                sentence, image_asset, segment_duration, temp_path
            )
            if text_clip:
                clips.append(text_clip)
                current_time += segment_duration
        
        # Add outro segment
        if current_time < duration:
            outro_duration = min(segment_duration, duration - current_time)
            outro_clip = await self._create_outro_clip(script.title, outro_duration, temp_path)
            if outro_clip:
                clips.append(outro_clip)
        
        return clips
    
    async def _create_intro_clip(self, title: str, duration: float, temp_path: Path) -> Optional[Any]:
        """Create intro clip with title"""
        try:
            import moviepy.editor as mp
            from moviepy.video.VideoClip import TextClip, ColorClip
            
            # Choose template
            template = self.templates['educational']
            
            # Create background
            bg_clip = ColorClip(
                size=self.video_config['resolution'],
                color=template['background_color'],
                duration=duration
            )
            
            # Create title text (if PIL available)
            if self.pil_available:
                text_clip = await self._create_text_overlay(
                    title, duration, template, is_title=True
                )
                
                # Composite text over background
                from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
                final_clip = CompositeVideoClip([bg_clip, text_clip])
                
                # Add fade in
                final_clip = final_clip.fadein(template['transition_duration'])
                
                return final_clip
            
            return bg_clip
            
        except Exception as e:
            print(f"Intro clip error: {e}")
            return None
    
    async def _create_video_asset_clip(self, asset: Asset, duration: float, temp_path: Path) -> Optional[Any]:
        """Create clip from video asset"""
        try:
            import moviepy.editor as mp
            
            # Download video if URL
            if asset.url.startswith('http'):
                video_path = await self._download_asset(asset, temp_path)
                if not video_path or not video_path.exists():
                    return None
            else:
                video_path = Path(asset.url)
                if not video_path.exists():
                    return None
            
            # Load video clip
            video_clip = mp.VideoFileClip(str(video_path))
            
            # Trim to desired duration
            if video_clip.duration > duration:
                # Use middle portion
                start_time = (video_clip.duration - duration) / 2
                video_clip = video_clip.subclip(start_time, start_time + duration)
            elif video_clip.duration < duration:
                # Loop the video
                loops_needed = int(duration / video_clip.duration) + 1
                clips = [video_clip] * loops_needed
                video_clip = mp.concatenate_videoclips(clips).subclip(0, duration)
            
            # Resize to fit
            target_width, target_height = self.video_config['resolution']
            video_clip = mp.resize(video_clip, (target_width, target_height))
            
            # Add fade effects
            video_clip = video_clip.fadein(0.5).fadeout(0.5)
            
            return video_clip
            
        except Exception as e:
            print(f"Video asset clip error: {e}")
            return None
    
    async def _create_text_image_clip(self, text: str, asset: Asset, duration: float, temp_path: Path) -> Optional[Any]:
        """Create clip with image background and text overlay"""
        try:
            import moviepy.editor as mp
            
            # Download image if URL
            if asset.url.startswith('http'):
                image_path = await self._download_asset(asset, temp_path)
                if not image_path or not image_path.exists():
                    return await self._create_text_clip(text, duration, temp_path)
            else:
                image_path = Path(asset.url)
                if not image_path.exists():
                    return await self._create_text_clip(text, duration, temp_path)
            
            # Create image clip
            image_clip = mp.ImageClip(str(image_path), duration=duration)
            
            # Resize to fit
            target_width, target_height = self.video_config['resolution']
            image_clip = mp.resize(image_clip, (target_width, target_height))
            
            # Add text overlay if PIL available
            if self.pil_available:
                template = self.templates['educational']
                text_clip = await self._create_text_overlay(text, duration, template)
                
                from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
                final_clip = CompositeVideoClip([image_clip, text_clip])
                
                # Add fade effects
                final_clip = final_clip.fadein(0.3).fadeout(0.3)
                
                return final_clip
            
            return image_clip
            
        except Exception as e:
            print(f"Text image clip error: {e}")
            return await self._create_text_clip(text, duration, temp_path)
    
    async def _create_text_clip(self, text: str, duration: float, temp_path: Path) -> Optional[Any]:
        """Create simple text-only clip"""
        try:
            import moviepy.editor as mp
            from moviepy.video.VideoClip import ColorClip
            
            template = self.templates['educational']
            
            # Create background
            bg_clip = ColorClip(
                size=self.video_config['resolution'],
                color=template['background_color'],
                duration=duration
            )
            
            # Add text if PIL available
            if self.pil_available:
                text_clip = await self._create_text_overlay(text, duration, template)
                
                from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
                final_clip = CompositeVideoClip([bg_clip, text_clip])
                
                return final_clip
            
            return bg_clip
            
        except Exception as e:
            print(f"Text clip error: {e}")
            return None
    
    async def _create_text_overlay(self, text: str, duration: float, 
                                 template: Dict[str, Any], is_title: bool = False) -> Optional[Any]:
        """Create text overlay using PIL"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import numpy as np
            import moviepy.editor as mp
            
            # Create image with text
            width, height = self.video_config['resolution']
            image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            
            # Try to load font
            try:
                font_size = template['font_size'] * (1.5 if is_title else 1.0)
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                # Fallback to default font
                font = ImageFont.load_default()
            
            # Wrap text
            words = text.split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=font)
                text_width = bbox[2] - bbox[0]
                
                if text_width < width * 0.8:  # 80% of screen width
                    current_line.append(word)
                else:
                    lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line))
            
            # Draw text lines
            line_height = font_size * 1.2
            total_height = len(lines) * line_height
            start_y = (height - total_height) // 2
            
            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (width - text_width) // 2
                y = start_y + i * line_height
                
                # Draw text with shadow for readability
                shadow_color = (0, 0, 0, 180)
                text_color = template['text_color'] + (255,)
                
                # Shadow
                draw.text((x+2, y+2), line, font=font, fill=shadow_color)
                # Main text
                draw.text((x, y), line, font=font, fill=text_color)
            
            # Convert PIL image to numpy array
            np_image = np.array(image)
            
            # Create MoviePy clip
            text_clip = mp.ImageClip(np_image, duration=duration)
            
            # Add animation
            if template['animation_style'] == 'fade':
                text_clip = text_clip.fadein(0.5).fadeout(0.5)
            elif template['animation_style'] == 'slide':
                # Simple slide animation
                text_clip = text_clip.set_position(lambda t: (0, 100 * t))
            
            return text_clip
            
        except Exception as e:
            print(f"Text overlay error: {e}")
            return None
    
    async def _create_outro_clip(self, title: str, duration: float, temp_path: Path) -> Optional[Any]:
        """Create outro clip with call to action"""
        try:
            import moviepy.editor as mp
            from moviepy.video.VideoClip import ColorClip
            
            template = self.templates['educational']
            
            # Create background
            bg_clip = ColorClip(
                size=self.video_config['resolution'],
                color=template['background_color'],
                duration=duration
            )
            
            # Create outro text
            outro_text = f"Thanks for watching!\nLike & Subscribe for more\nabout {title}"
            
            if self.pil_available:
                text_clip = await self._create_text_overlay(
                    outro_text, duration, template, is_title=False
                )
                
                from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
                final_clip = CompositeVideoClip([bg_clip, text_clip])
                
                # Add fade out
                final_clip = final_clip.fadeout(template['transition_duration'])
                
                return final_clip
            
            return bg_clip
            
        except Exception as e:
            print(f"Outro clip error: {e}")
            return None
    
    async def _create_text_video(self, script: Script, duration: float, temp_path: Path) -> List[Any]:
        """Create simple text-only video as fallback"""
        try:
            import moviepy.editor as mp
            
            # Split script into segments
            sentences = self._split_script(script.content)
            if not sentences:
                sentences = [script.title]
            
            # Calculate segment duration
            segment_duration = duration / len(sentences)
            
            clips = []
            template = self.templates['educational']
            
            for sentence in sentences:
                text_clip = await self._create_text_clip(sentence, segment_duration, temp_path)
                if text_clip:
                    clips.append(text_clip)
            
            return clips
            
        except Exception as e:
            print(f"Text video error: {e}")
            return []
    
    async def _download_asset(self, asset: Asset, temp_path: Path) -> Optional[Path]:
        """Download asset from URL"""
        try:
            import aiohttp
            
            # Create filename from URL hash
            url_hash = hashlib.md5(asset.url.encode()).hexdigest()
            extension = '.mp4' if asset.type == 'video' else '.jpg'
            file_path = temp_path / f"{url_hash}{extension}"
            
            if file_path.exists():
                return file_path
            
            async with aiohttp.ClientSession() as session:
                async with session.get(asset.url, timeout=30) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        with open(file_path, 'wb') as f:
                            f.write(content)
                        
                        return file_path
            
        except Exception as e:
            print(f"Asset download error: {e}")
        
        return None
    
    def _split_script(self, script_content: str) -> List[str]:
        """Split script into sentences for display"""
        import re
        
        # Split by punctuation
        sentences = re.split(r'[.!?]+', script_content)
        
        # Clean up sentences
        clean_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 10:  # Minimum length
                clean_sentences.append(sentence)
        
        # Limit to 5 sentences max
        return clean_sentences[:5]
    
    def _generate_cache_key(self, script: Script, voiceover_path: Path, assets: List[Asset]) -> str:
        """Generate cache key for video assembly"""
        content = f"{script.title}_{voiceover_path}"
        
        for asset in assets[:3]:  # Use first 3 assets for key
            content += f"_{asset.url}"
        
        return hashlib.md5(content.encode()).hexdigest()
    
    async def _copy_file(self, source: Path, destination: Path) -> Path:
        """Copy file asynchronously"""
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            import aiofiles
            
            async with aiofiles.open(source, 'rb') as src:
                async with aiofiles.open(destination, 'wb') as dst:
                    content = await src.read()
                    await dst.write(content)
                    
        except ImportError:
            # Fallback to synchronous copy
            import shutil
            shutil.copy2(source, destination)
        
        return destination
    
    async def estimate_assembly_time(self, script: Script, 
                                   assets: List[Asset]) -> float:
        """Estimate video assembly time in seconds"""
        # Base time for processing
        base_time = 30.0
        
        # Add time based on number of assets
        asset_time = len(assets) * 5.0
        
        # Add time based on script length
        script_time = len(script.content) / 100.0  # 0.01 seconds per character
        
        return base_time + asset_time + script_time
    
    async def validate_output(self, video_path: Path) -> Dict[str, Any]:
        """Validate generated video file"""
        validation = {
            'valid': False,
            'duration': 0.0,
            'resolution': (0, 0),
            'file_size': 0,
            'errors': []
        }
        
        try:
            if not video_path.exists():
                validation['errors'].append('File does not exist')
                return validation
            
            # Check file size
            file_size = video_path.stat().st_size
            validation['file_size'] = file_size
            
            if file_size < 1024:  # 1KB minimum
                validation['errors'].append('File too small')
            
            # Check duration using MoviePy
            if self.moviepy_available:
                import moviepy.editor as mp
                
                try:
                    clip = mp.VideoFileClip(str(video_path))
                    validation['duration'] = clip.duration
                    validation['resolution'] = clip.size
                    clip.close()
                    
                    # Check duration limits
                    if validation['duration'] < self.video_config['min_video_duration']:
                        validation['errors'].append(f'Duration too short: {validation["duration"]}s')
                    
                    if validation['duration'] > self.video_config['max_video_duration']:
                        validation['errors'].append(f'Duration too long: {validation["duration"]}s')
                    
                    # Check resolution
                    target_res = self.video_config['resolution']
                    if validation['resolution'] != target_res:
                        validation['errors'].append(f'Wrong resolution: {validation["resolution"]}')
                
                except Exception as e:
                    validation['errors'].append(f'Video validation error: {e}')
            
            validation['valid'] = len(validation['errors']) == 0
            
        except Exception as e:
            validation['errors'].append(f'Validation error: {e}')
        
        return validation
    
    async def close(self):
        """Close provider resources"""
        # MoviePy doesn't require explicit closing
        pass
