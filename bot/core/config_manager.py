# bot/core/config_manager.py
"""
Dynamic configuration management with file watching.
"""

import asyncio
import yaml
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigManager:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = {}
        self._callbacks = []
        self.observer = Observer()
    
    def load_config(self):
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
    
    def add_callback(self, callback):
        """Add a callback to be called when config changes."""
        self._callbacks.append(callback)
    
    def _notify_callbacks(self):
        for callback in self._callbacks:
            callback(self.config)
    
    def start_watching(self):
        event_handler = FileSystemEventHandler()
        
        def on_modified(event):
            if event.src_path == str(self.config_path):
                self.load_config()
                self._notify_callbacks()
        
        event_handler.on_modified = on_modified
        self.observer.schedule(event_handler, self.config_path.parent, recursive=False)
        self.observer.start()
    
    def stop_watching(self):
        self.observer.stop()
        self.observer.join()
