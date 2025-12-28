SHORTSYNC PRO - YouTube Shorts Automation Bot
==============================================

A professional system for creating YouTube Shorts with AI and human quality control.

INSTALLATION
============

1. Clone repository
2. Create virtual environment: python -m venv venv
3. Activate: source venv/bin/activate (Windows: venv\Scripts\activate)
4. Install: pip install -r requirements.txt
5. Copy .env.example to .env and add your API keys

REQUIRED API KEYS
=================

- YOUTUBE_API_KEY
- COHERE_API_KEY
- PEXELS_API_KEY
- ELEVENLABS_API_KEY

OPTIONAL API KEYS
=================

- HF_API_KEY (Hugging Face)
- OPENAI_API_KEY
- UNSPLASH_API_KEY
- NEWSAPI_KEY

RUNNING THE BOT
===============

Development: python -m bot.main --dev
Production: python -m bot.main
One-time: python -m bot.main --oneshot
Health check: python -m bot.main --health

FEATURES
========

- AI Script Generation (Cohere, Hugging Face, OpenAI, Claude)
- Trend Detection with free APIs
- Professional Thumbnail Creation
- Voiceover Generation (ElevenLabs/Google TTS)
- Video Assembly from stock footage
- Human Approval System
- Anti-AI-Slop Quality Checks
- Docker & Kubernetes Deployment
- Multi-Channel Support

PROJECT STRUCTURE
=================

youtube_bot/
  bot/ - Main Python package
  docker/ - Docker configurations
  k8s/ - Kubernetes manifests
  data/ - Persistent data
  logs/ - Application logs
  output/ - Generated content
  .env - Environment variables
  requirements.txt - Dependencies

DOCKER DEPLOYMENT
=================

Build: docker build -t shortsync-pro .
Run: docker run -d --name shortsync -p 8081:8081 -v $(pwd)/data:/app/data --env-file .env shortsync-pro
Compose: docker-compose up -d

KUBERNETES DEPLOYMENT
=====================

Apply: kubectl apply -f k8s/deployment.yml
Check: kubectl get pods -l app=shortsync-pro

CONFIGURATION FILES
===================

1. .env - Environment variables (see above)
2. data/channels.json - Channel configurations
3. config/settings.yml - YAML settings

Example channels.json:
[
  {
    "name": "Tech Channel",
    "niche": "technology",
    "quality_standard": "standard"
  }
]

CLI COMMANDS
============

python -m bot.cli channels list
python -m bot.cli channels create --name "Science" --niche science
python -m bot.cli videos generate --topic "AI"
python -m bot.cli videos approve --id video_123
python -m bot.cli videos upload --limit 2
python -m bot.cli stats

PYTHON API
==========

from bot.config import get_config
from bot.main import ShortSyncBot

config = get_config()
bot = ShortSyncBot(config)
job_id = await bot.create_video_job(topic="AI", channel="Tech")

QUALITY SYSTEM
==============

- Minimum Quality Score: 70/100
- Human Approval Required
- Auto-Improvement for Low-Quality Content
- Content Blacklisting
- Fact Checking Available

MONITORING
==========

Health dashboard: http://localhost:8081
Endpoints:
- /health - System health
- /ready - Readiness check
- /metrics - Performance metrics
- /info - System information

TROUBLESHOOTING
===============

1. Missing dependencies: pip install moviepy pillow
2. API rate limits: Reduce MAX_DAILY_UPLOADS in .env
3. YouTube quota: Request quota increase from Google
4. Video assembly: Check ffmpeg installation
5. Debug mode: export LOG_LEVEL=DEBUG; python -m bot.main --dev

LICENSE
=======

Business Source License 1.1 (BSL 1.1)
- Free for channels with <10,000 subscribers
- Commercial license required for larger channels
- See LICENSE file for complete terms

SUPPORT
=======

- GitHub Issues for bug reports
- Email: support@shortsync.pro

DISCLAIMER
==========

For educational purposes only. Always follow YouTube's Terms of Service
and Community Guidelines. Developers are not responsible for content
created using this tool.
