"""
Simple voiceover provider for ShortSync Pro.

Generates voiceovers using free TTS services (Google TTS) with ElevenLabs fallback.
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
from pathlib import Path
import tempfile
import os
from datetime import datetime
import hashlib
import json

from bot.providers.base import BaseVoiceoverProvider

class SimpleVoiceoverProvider(BaseVoiceoverProvider):
    """Simple voiceover provider using free TTS services"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.elevenlabs_api_key = config.get('elevenlabs_api_key')
        self.google_tts_enabled = config.get('google_tts_enabled', True)
        self.session = None
        self.cache_dir = Path(config.get('cache_dir', 'data/voiceover_cache'))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Voice configurations
        self.voices = {
            'default': {
                'provider': 'google',
                'language': 'en-US',
                'gender': 'neutral',
                'speed': 1.0
            },
            'male': {
                'provider': 'google',
                'language': 'en-US',
                'gender': 'male',
                'speed': 1.0
            },
            'female': {
                'provider': 'google',
                'language': 'en-US',
                'gender': 'female',
                'speed': 1.0
            },
            'elevenlabs_default': {
                'provider': 'elevenlabs',
                'voice_id': '21m00Tcm4TlvDq8ikWAM',
                'stability': 0.5,
                'similarity_boost': 0.75
            }
        }
    
    async def initialize(self):
        """Initialize provider"""
        self.session = aiohttp.ClientSession()
    
    async def generate_voiceover(self, text: str,
                               voice_id: str = "default",
                               output_path: Optional[Path] = None) -> Path:
        """Generate voiceover from text"""
        if not self.session:
            await self.initialize()
        
        # Validate text length (ElevenLabs has limits)
        if len(text) > 5000:
            text = text[:5000] + "..."
        
        # Check cache first
        cache_key = self._generate_cache_key(text, voice_id)
        cached_file = self.cache_dir / f"{cache_key}.mp3"
        
        if cached_file.exists():
            # Return cached file or copy to output path
            if output_path:
                return await self._copy_file(cached_file, output_path)
            return cached_file
        
        # Get voice configuration
        voice_config = self.voices.get(voice_id, self.voices['default'])
        provider = voice_config.get('provider', 'google')
        
        # Generate voiceover based on provider
        if provider == 'elevenlabs' and self.elevenlabs_api_key:
            result = await self._generate_with_elevenlabs(text, voice_config)
        else:
            # Fallback to Google TTS
            result = await self._generate_with_google_tts(text, voice_config)
        
        if not result:
            # Ultimate fallback: use system TTS or create placeholder
            result = await self._generate_fallback(text)
        
        # Cache the result
        if result and result.exists():
            # Copy to cache
            cached_file.parent.mkdir(parents=True, exist_ok=True)
            await self._copy_file(result, cached_file)
            
            # If output_path specified, copy there too
            if output_path and output_path != cached_file:
                return await self._copy_file(cached_file, output_path)
            
            return cached_file if not output_path else output_path
        
        # If all fails, create empty file
        if output_path:
            output_path.touch()
            return output_path
        
        # Create temp file as last resort
        temp_file = Path(tempfile.mktemp(suffix='.mp3'))
        temp_file.touch()
        return temp_file
    
    async def _generate_with_elevenlabs(self, text: str, 
                                       voice_config: Dict[str, Any]) -> Optional[Path]:
        """Generate voiceover using ElevenLabs API"""
        try:
            voice_id = voice_config.get('voice_id', '21m00Tcm4TlvDq8ikWAM')
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": voice_config.get('stability', 0.5),
                    "similarity_boost": voice_config.get('similarity_boost', 0.75)
                }
            }
            
            async with self.session.post(url, headers=headers, json=data, timeout=60) as response:
                if response.status == 200:
                    # Create temp file
                    temp_file = Path(tempfile.mktemp(suffix='.mp3'))
                    
                    # Write audio data to file
                    audio_data = await response.read()
                    with open(temp_file, 'wb') as f:
                        f.write(audio_data)
                    
                    return temp_file
                else:
                    error_text = await response.text()
                    print(f"ElevenLabs API error {response.status}: {error_text}")
                    
        except Exception as e:
            print(f"ElevenLabs error: {e}")
        
        return None
    
    async def _generate_with_google_tts(self, text: str,
                                       voice_config: Dict[str, Any]) -> Optional[Path]:
        """Generate voiceover using Google TTS (gTTS)"""
        try:
            # Import gTTS (optional dependency)
            try:
                from gtts import gTTS
                from gtts.lang import tts_langs
            except ImportError:
                print("gTTS not installed, falling back")
                return None
            
            # Configure language and options
            language = voice_config.get('language', 'en')
            lang_code = language.split('-')[0] if '-' in language else language
            
            # Check if language is supported
            supported_langs = tts_langs()
            if lang_code not in supported_langs:
                print(f"Language {lang_code} not supported by gTTS, using 'en'")
                lang_code = 'en'
            
            # Clean text for TTS
            clean_text = self._clean_text_for_tts(text)
            
            # Generate speech
            tts = gTTS(text=clean_text, lang=lang_code, slow=False)
            
            # Save to temp file
            temp_file = Path(tempfile.mktemp(suffix='.mp3'))
            tts.save(str(temp_file))
            
            return temp_file
            
        except Exception as e:
            print(f"Google TTS error: {e}")
        
        return None
    
    async def _generate_fallback(self, text: str) -> Optional[Path]:
        """Fallback voiceover generation"""
        try:
            # Try using system TTS (platform dependent)
            import platform
            
            if platform.system() == 'Darwin':  # macOS
                return await self._generate_macos_tts(text)
            elif platform.system() == 'Windows':
                return await self._generate_windows_tts(text)
            elif platform.system() == 'Linux':
                return await self._generate_linux_tts(text)
            else:
                print(f"Unsupported platform: {platform.system()}")
                
        except Exception as e:
            print(f"Fallback TTS error: {e}")
        
        return None
    
    async def _generate_macos_tts(self, text: str) -> Optional[Path]:
        """Generate TTS using macOS say command"""
        try:
            import subprocess
            
            temp_file = Path(tempfile.mktemp(suffix='.aiff'))
            
            # Use say command to generate audio
            cmd = [
                'say',
                '-v', 'Alex',  # Default voice
                '-o', str(temp_file),
                text[:1000]  # Limit text length
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            await process.wait()
            
            if temp_file.exists():
                # Convert AIFF to MP3 if needed
                mp3_file = Path(tempfile.mktemp(suffix='.mp3'))
                await self._convert_audio(temp_file, mp3_file)
                temp_file.unlink()  # Remove AIFF file
                return mp3_file
            
        except Exception as e:
            print(f"macOS TTS error: {e}")
        
        return None
    
    async def _generate_windows_tts(self, text: str) -> Optional[Path]:
        """Generate TTS using Windows SAPI"""
        try:
            import win32com.client
            import pythoncom
            
            # Initialize COM in this thread
            pythoncom.CoInitialize()
            
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            
            # Create temp file
            temp_file = Path(tempfile.mktemp(suffix='.wav'))
            
            # Create stream
            stream = win32com.client.Dispatch("SAPI.SpFileStream")
            stream.Open(str(temp_file), 3)  # 3 = SSFMCreateForWrite
            
            # Set output to stream
            speaker.AudioOutputStream = stream
            
            # Speak text
            speaker.Speak(text[:1000])
            
            # Close stream
            stream.Close()
            
            # Convert to MP3 if needed
            if temp_file.exists():
                mp3_file = Path(tempfile.mktemp(suffix='.mp3'))
                await self._convert_audio(temp_file, mp3_file)
                temp_file.unlink()  # Remove WAV file
                return mp3_file
            
        except Exception as e:
            print(f"Windows TTS error: {e}")
        
        return None
    
    async def _generate_linux_tts(self, text: str) -> Optional[Path]:
        """Generate TTS using Linux espeak"""
        try:
            import subprocess
            
            temp_file = Path(tempfile.mktemp(suffix='.wav'))
            
            # Use espeak to generate audio
            cmd = [
                'espeak',
                '-v', 'en-us',
                '-w', str(temp_file),
                text[:1000]
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            await process.wait()
            
            if temp_file.exists():
                # Convert to MP3
                mp3_file = Path(tempfile.mktemp(suffix='.mp3'))
                await self._convert_audio(temp_file, mp3_file)
                temp_file.unlink()
                return mp3_file
            
        except Exception as e:
            print(f"Linux TTS error: {e}")
        
        return None
    
    async def _convert_audio(self, input_path: Path, output_path: Path) -> bool:
        """Convert audio file to MP3 format"""
        try:
            # Try using pydub
            from pydub import AudioSegment
            
            audio = AudioSegment.from_file(str(input_path))
            audio.export(str(output_path), format="mp3")
            return True
            
        except ImportError:
            print("pydub not installed for audio conversion")
            
            # Try using ffmpeg directly
            try:
                import subprocess
                
                cmd = [
                    'ffmpeg',
                    '-i', str(input_path),
                    '-codec:a', 'libmp3lame',
                    '-qscale:a', '2',
                    str(output_path),
                    '-y'  # Overwrite output
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                await process.wait()
                return output_path.exists()
                
            except Exception as e:
                print(f"FFmpeg conversion error: {e}")
        
        return False
    
    def _clean_text_for_tts(self, text: str) -> str:
        """Clean text for better TTS results"""
        # Remove URLs
        import re
        text = re.sub(r'https?://\S+', '', text)
        
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Handle common abbreviations
        replacements = {
            ' vs. ': ' versus ',
            ' etc. ': ' etcetera ',
            ' i.e. ': ' that is ',
            ' e.g. ': ' for example ',
            ' Mr. ': ' Mister ',
            ' Mrs. ': ' Missus ',
            ' Dr. ': ' Doctor ',
            ' St. ': ' Street ',
            ' approx. ': ' approximately ',
        }
        
        for abbr, full in replacements.items():
            text = text.replace(abbr, full)
        
        # Ensure ends with punctuation
        if text and text[-1] not in '.!?':
            text += '.'
        
        return text
    
    def _generate_cache_key(self, text: str, voice_id: str) -> str:
        """Generate cache key for text and voice"""
        # Create hash of text and voice config
        content = f"{text}_{voice_id}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def _copy_file(self, source: Path, destination: Path) -> Path:
        """Copy file asynchronously"""
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        # Use aiofiles for async file operations if available
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
    
    async def list_available_voices(self) -> List[Dict[str, Any]]:
        """List available voices"""
        voices = []
        
        # Add Google TTS voices
        google_voices = [
            {'id': 'default', 'name': 'Default (Google)', 'language': 'en-US', 'gender': 'neutral'},
            {'id': 'male', 'name': 'Male Voice (Google)', 'language': 'en-US', 'gender': 'male'},
            {'id': 'female', 'name': 'Female Voice (Google)', 'language': 'en-US', 'gender': 'female'},
        ]
        voices.extend(google_voices)
        
        # Add ElevenLabs voices if API key available
        if self.elevenlabs_api_key:
            elevenlabs_voices = await self._list_elevenlabs_voices()
            voices.extend(elevenlabs_voices)
        
        return voices
    
    async def _list_elevenlabs_voices(self) -> List[Dict[str, Any]]:
        """List available ElevenLabs voices"""
        try:
            url = "https://api.elevenlabs.io/v1/voices"
            headers = {"xi-api-key": self.elevenlabs_api_key}
            
            async with self.session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    voices = []
                    for voice in data.get('voices', []):
                        voices.append({
                            'id': f"elevenlabs_{voice.get('voice_id')}",
                            'name': voice.get('name', 'Unknown'),
                            'provider': 'elevenlabs',
                            'voice_id': voice.get('voice_id'),
                            'category': voice.get('category', 'premade'),
                            'language': 'en'
                        })
                    
                    return voices
                
        except Exception as e:
            print(f"Error listing ElevenLabs voices: {e}")
        
        return []
    
    async def get_voice_info(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific voice"""
        if voice_id in self.voices:
            voice_config = self.voices[voice_id]
            
            info = {
                'id': voice_id,
                'provider': voice_config.get('provider', 'unknown'),
                'config': voice_config
            }
            
            # Add provider-specific info
            if voice_config.get('provider') == 'elevenlabs' and self.elevenlabs_api_key:
                provider_info = await self._get_elevenlabs_voice_info(voice_config.get('voice_id'))
                if provider_info:
                    info.update(provider_info)
            
            return info
        
        return None
    
    async def _get_elevenlabs_voice_info(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """Get ElevenLabs voice information"""
        try:
            url = f"https://api.elevenlabs.io/v1/voices/{voice_id}"
            headers = {"xi-api-key": self.elevenlabs_api_key}
            
            async with self.session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    return {
                        'name': data.get('name'),
                        'category': data.get('category'),
                        'description': data.get('description'),
                        'labels': data.get('labels', {}),
                        'preview_url': data.get('preview_url')
                    }
                
        except Exception as e:
            print(f"Error getting ElevenLabs voice info: {e}")
        
        return None
    
    async def estimate_duration(self, text: str, voice_id: str = "default") -> float:
        """Estimate voiceover duration in seconds"""
        # Rough estimate: 4 characters per second for normal speech
        # Adjust based on voice speed
        voice_config = self.voices.get(voice_id, self.voices['default'])
        speed = voice_config.get('speed', 1.0)
        
        # Remove punctuation for better estimate
        import string
        clean_text = text.translate(str.maketrans('', '', string.punctuation))
        
        # Estimate: 150 words per minute = 2.5 words per second
        words = len(clean_text.split())
        estimated_seconds = words / 2.5
        
        # Adjust for speed
        estimated_seconds /= speed
        
        return max(1.0, estimated_seconds)  # Minimum 1 second
    
    async def close(self):
        """Close provider resources"""
        if self.session:
            await self.session.close()
