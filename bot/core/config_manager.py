"""
Configuration manager for dynamic configuration updates
"""

import yaml
import json
from pathlib import Path
from typing import Dict, Any
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigManager:
    """Manage dynamic configuration updates"""
    
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = {}
        self.callbacks = []
        self.observer = None
        
    def load_config(self):
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
            return self.config
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}
    
    def save_config(self):
        """Save configuration to YAML file"""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        
        # Save and notify
        self.save_config()
        self.notify_callbacks(key, value)
    
    def add_callback(self, callback):
        """Add callback for configuration changes"""
        self.callbacks.append(callback)
    
    def notify_callbacks(self, key: str, value: Any):
        """Notify all callbacks of configuration change"""
        for callback in self.callbacks:
            try:
                callback(key, value)
            except Exception as e:
                print(f"Error in config callback: {e}")
    
    def start_watching(self):
        """Start watching for configuration file changes"""
        class ConfigHandler(FileSystemEventHandler):
            def __init__(self, manager):
                self.manager = manager
            
            def on_modified(self, event):
                if event.src_path == str(self.manager.config_path):
                    print(f"Config file modified: {event.src_path}")
                    old_config = self.manager.config.copy()
                    self.manager.load_config()
                    
                    # Find changed keys
                    changed_keys = self.find_changed_keys(old_config, self.manager.config)
                    for key in changed_keys:
                        self.manager.notify_callbacks(key, self.manager.get(key))
        
        self.observer = Observer()
        event_handler = ConfigHandler(self)
        self.observer.schedule(event_handler, path=str(self.config_path.parent), recursive=False)
        self.observer.start()
    
    def stop_watching(self):
        """Stop watching for configuration file changes"""
        if self.observer:
            self.
