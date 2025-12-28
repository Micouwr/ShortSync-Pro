#!/usr/bin/env python3
"""
Test script for ShortSync Pro
"""

import sys
import os
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

print("🧪 Testing ShortSync Pro setup...")
print("="*60)

# Test 1: Check basic imports
print("\n1. Testing imports...")
try:
    import bot
    print(f"✅ Imported bot package (v{bot.__version__})")
except ImportError as e:
    print(f"❌ Failed to import bot: {e}")
    sys.exit(1)

# Test 2: Check config
print("\n2. Testing configuration...")
try:
    from bot.config import get_config
    config = get_config()
    print(f"✅ Config loaded successfully")
    print(f"   Environment: {config.environment}")
    print(f"   Base dir: {config.base_dir}")
except ImportError as e:
    print(f"❌ Failed to import config: {e}")
except Exception as e:
    print(f"❌ Config error: {e}")

# Test 3: Check main
print("\n3. Testing main module...")
try:
    from bot import main
    print("✅ Main module can be imported")
except ImportError as e:
    print(f"❌ Failed to import main: {e}")

# Test 4: Check directories
print("\n4. Checking directory structure...")
required_dirs = ['data', 'logs', 'output']
for dir_name in required_dirs:
    dir_path = current_dir / dir_name
    if dir_path.exists():
        print(f"✅ {dir_name}/ directory exists")
    else:
        print(f"⚠️  {dir_name}/ directory missing (will be created on first run)")

# Test 5: Check .env
print("\n5. Checking environment...")
env_file = current_dir / '.env'
if env_file.exists():
    print("✅ .env file exists")
    # Read and check for basic keys
    with open(env_file, 'r') as f:
        content = f.read()
        if 'YOUTUBE_API_KEY' in content:
            print("   YouTube API key configured")
        else:
            print("   ⚠️  YouTube API key not found in .env")
else:
    print("⚠️  .env file not found (create it from .env.example)")

print("\n" + "="*60)
print("🎉 Basic setup looks good!")
print("\nTo run the bot:")
print("  python -m bot.main --dev --test")
print("\nTo run normally:")
print("  python -m bot.main")
