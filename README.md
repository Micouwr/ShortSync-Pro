# ShortSync Pro - Professional YouTube Shorts Automation Bot

A modular, scalable system for creating and managing YouTube Shorts content with human quality control and anti-AI-slop protection.

## 🎯 Features

### 🤖 AI-Powered Content Creation
- **Multi-AI Script Generation**: Cohere, Hugging Face, OpenAI, Claude with fallback logic
- **Trend Detection**: Free APIs (no scraping) for trending topics
- **Professional Thumbnails**: Auto-generated with branding templates
- **Voiceover Generation**: ElevenLabs & Google TTS integration
- **Video Assembly**: Stock footage + voiceover + thumbnails

### 🛡️ Quality Assurance
- **Anti-AI-Slop System**: Detects and improves low-quality content
- **Human Approval Required**: One-click approve/reject workflow
- **Minimum Quality Score**: 70/100 threshold for auto-approval
- **Fact Checking**: MCP-ready verification system

### 🚀 Production Ready
- **Docker & Kubernetes**: Full production deployment
- **Health Monitoring**: Built-in health check server (port 8081)
- **Web Dashboard**: Optional management interface
- **Notifications**: Email/Discord/Telegram alerts

### 📊 Management
- **Multi-Channel Support**: Manage multiple YouTube channels
- **Content Calendar**: Automated scheduling
- **Analytics**: Performance tracking and optimization
- **License Management**: BSL 1.1 with free tier (<10k subs)

## 📁 Project Structure
youtube_bot/
├── bot/ # Main Python package
│ ├── init.py # Package initialization
│ ├── main.py # Entry point with CLI
│ ├── config.py # Configuration management
│ ├── cli.py # Command line interface
│ ├── core/ # Core framework
│ │ ├── init.py
│ │ ├── state_manager.py # State management
│ │ ├── job_queue.py # Async job processing
│ │ ├── enhanced_pipeline.py # Main pipeline
│ │ ├── health.py # Health checks
│ │ ├── circuit_breaker.py # API failure protection
│ │ └── config_manager.py # Dynamic config
│ ├── database/ # Data persistence
│ │ ├── init.py
│ │ ├── manager.py # Database operations
│ │ └── models.py # Data models
│ ├── providers/ # AI and service providers
│ │ ├── init.py
│ │ ├── base.py # Abstract provider classes
│ │ ├── factory.py # Provider factory
│ │ └── simple/ # Simple implementations
│ │ ├── init.py
│ │ ├── script_provider.py
│ │ ├── trend_provider.py
│ │ ├── asset_provider.py
│ │ ├── voiceover_provider.py
│ │ └── video_provider.py
│ └── utils/ # Utilities
│ ├── init.py
│ ├── cleanup.py
│ └── youtube_api.py
├── docker/ # Docker configurations
│ ├── Dockerfile
│ └── entrypoint.sh
├── k8s/ # Kubernetes manifests
│ └── deployment.yml
├── data/ # Persistent data
├── logs/ # Application logs
├── assets/ # Static assets
├── output/ # Generated content
├── .env # Environment variables
├── .gitignore
├── LICENSE
├── requirements.txt # Python dependencies
├── docker-compose.yml # Development
├── docker-compose.prod.yml # Production
└── Makefile # Common tasks

text

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Docker (optional)
- API Keys (see Configuration)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd youtube_bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your API keys
Configuration
Create .env file:

env
# API Keys
YOUTUBE_API_KEY=your_youtube_api_key
COHERE_API_KEY=your_cohere_key
PEXELS_API_KEY=your_pexels_key
ELEVENLABS_API_KEY=your_elevenlabs_key
HF_API_KEY=your_huggingface_key
OPENAI_API_KEY=your_openai_key

# Bot Settings
ENVIRONMENT=development
MAX_DAILY_UPLOADS=3
LOG_LEVEL=INFO

# Optional APIs
UNSPLASH_API_KEY=your_unsplash_key
NEWSAPI_KEY=your_newsapi_key
Running the Bot
bash
# Development mode
python -m bot.main --dev

# Production mode
python -m bot.main

# Run once and exit
python -m bot.main --oneshot

# Health check only
python -m bot.main --health

# Start web dashboard
python -m bot.main --dashboard
Docker Deployment
bash
# Build image
docker build -t shortsync-pro .

# Run container
docker run -d \
  --name shortsync \
  -p 8081:8081 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/output:/app/output \
  --env-file .env \
  shortsync-pro

# Docker Compose
docker-compose up -d
Kubernetes Deployment
bash
# Apply deployment
kubectl apply -f k8s/deployment.yml

# Check status
kubectl get pods -l app=shortsync-pro
⚙️ Configuration Files
Channel Configuration (data/channels.json)
json
[
  {
    "name": "Tech Explained",
    "niche": "technology",
    "quality_standard": "premium",
    "upload_schedule": {
      "monday": ["09:00", "13:00", "18:00"],
      "tuesday": ["09:00", "13:00", "18:00"],
      "wednesday": ["09:00", "13:00", "18:00"],
      "thursday": ["09:00", "13:00", "18:00"],
      "friday": ["09:00", "13:00", "18:00"],
      "saturday": ["10:00", "14:00"],
      "sunday": ["10:00", "14:00"]
    },
    "branding": {
      "intro_template": "tech_intro.mp4",
      "outro_template": "tech_outro.png",
      "watermark": "tech_logo.png",
      "color_scheme": "#FF6B6B",
      "voice_id": "tech_male"
    }
  }
]
YAML Configuration (config/settings.yml)
yaml
environment: production
debug: false

modules:
  trend_detection:
    enabled: true
    provider_type: simple
    timeout_seconds: 30
  
  script_generation:
    enabled: true
    provider_type: hybrid
    mcp_server_url: http://localhost:8000
    fallback_to_simple: true

pipeline:
  max_concurrent_jobs: 3
  job_timeout_minutes: 15
  retry_attempts: 3

youtube:
  max_daily_uploads: 3
  min_upload_interval: 14400
  default_privacy: private

content:
  default_duration: 45
  min_quality_score: 70.0
  max_title_length: 100
📋 Usage Examples
CLI Commands
bash
# Show help
python -m bot.cli --help

# List channels
python -m bot.cli channels list

# Create new channel
python -m bot.cli channels create --name "Science Facts" --niche science

# Generate single video
python -m bot.cli videos generate --topic "Quantum Computing"

# Approve pending videos
python -m bot.cli videos approve --id video_123

# Upload approved videos
python -m bot.cli videos upload --limit 2

# Show statistics
python -m bot.cli stats
Python API
python
from bot.config import get_config
from bot.main import ShortSyncBot

# Initialize bot
config = get_config()
bot = ShortSyncBot(config)

# Create video job
job_id = await bot.create_video_job(
    topic="Artificial Intelligence",
    channel="Tech Explained"
)

# Check status
status = await bot.get_job_status(job_id)
print(f"Job {job_id}: {status['status']}")

# Get statistics
stats = await bot.get_statistics()
print(f"Videos created: {stats['total_videos_created']}")
🔧 Provider System
Available Providers
Provider	Type	Dependencies	Status
Script Generation	Cohere, Hugging Face, OpenAI, Claude	cohere, transformers, openai	✅
Trend Detection	Reddit, Google Trends, Wikipedia	pytrends, aiohttp	✅
Asset Gathering	Pexels, Unsplash, Pixabay	pexels-api, unsplashpy	✅
Voiceover	ElevenLabs, Google TTS, System TTS	elevenlabs, gTTS	✅
Video Assembly	MoviePy, PIL	moviepy, pillow	✅
Adding Custom Providers
Create provider class:

python
from bot.providers.base import BaseScriptProvider

class CustomScriptProvider(BaseScriptProvider):
    async def generate_script(self, topic: str, duration_seconds: int):
        # Your implementation
        pass
    
    async def improve_script(self, script):
        # Your implementation
        pass
Register in factory:

python
from bot.providers.factory import register_provider

register_provider('custom_script', CustomScriptProvider)
🛡️ Quality System
Anti-AI-Slop Features
Content Scoring: Each script receives quality score (0-100)

Minimum Threshold: Default 70/100 required for approval

Auto-Improvement: Low-quality scripts are automatically enhanced

Human Review: All content requires one-click human approval

Blacklist System: Block low-quality topics and patterns

Quality Metrics
Readability Score: Flesch-Kincaid grade level

Engagement Score: Hook strength, pacing, CTA effectiveness

Accuracy Score: Fact verification (when MCP enabled)

Production Quality: Audio clarity, visual appeal

📊 Monitoring & Analytics
Health Checks
Access health dashboard at http://localhost:8081:

/health - Overall system health

/ready - Readiness for traffic

/metrics - Performance metrics

/info - System information

Logging
python
import logging
logging.basicConfig(level=logging.INFO)

# Structured logging
logger = logging.getLogger(__name__)
logger.info("Job completed", extra={"job_id": job_id, "duration": duration})
Metrics Collection
Job Processing Time: Average time per job type

Success Rate: Percentage of successful completions

API Usage: Provider API call statistics

Resource Usage: CPU, memory, disk utilization

🐛 Troubleshooting
Common Issues
Issue: "ModuleNotFoundError: No module named 'moviepy'"
Solution: Install missing dependencies: pip install moviepy pillow

Issue: "API rate limit exceeded"
Solution: Configure rate limits in provider settings or use API keys with higher limits

Issue: "YouTube API quota exceeded"
Solution: Reduce MAX_DAILY_UPLOADS or request quota increase from Google

Issue: "Video assembly failed"
Solution: Check ffmpeg installation: ffmpeg -version

Debug Mode
bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python -m bot.main --dev

# Check logs
tail -f logs/bot.log
🔒 Security & Privacy
Data Protection
API Keys: Stored in .env file (never in source code)

Database: SQLite with encrypted sensitive fields

Logs: No personal data in logs

Temporary Files: Auto-cleanup after processing

YouTube Compliance
Rate Limiting: Respects YouTube API quotas

Content Guidelines: Quality system enforces community guidelines

Transparency: Clearly labels AI-generated content when required

Copyright: Uses only licensed/royalty-free assets

📄 License
ShortSync Pro is licensed under the Business Source License 1.1 (BSL 1.1).

Key Points:

Free: For channels with <10,000 subscribers

Commercial: Requires license for larger channels

Source Available: Full source code provided

No Reselling: Cannot resell or provide as service without license

See LICENSE file for complete terms.

🤝 Contributing
Fork the repository

Create feature branch: git checkout -b feature/amazing-feature

Commit changes: git commit -m 'Add amazing feature'

Push to branch: git push origin feature/amazing-feature

Open Pull Request

Development Setup
bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Format code
black bot/
isort bot/

# Type checking
mypy bot/
Code Style
Follow PEP 8

Use type hints

Write docstrings

Add tests for new features

📞 Support
Documentation: docs.shortsync.pro

Issues: GitHub Issues

Discord: Community Server

Email: support@shortsync.pro

🙏 Acknowledgments
MoviePy: Video processing library

Cohere: AI text generation

ElevenLabs: Voice synthesis

Pexels/Unsplash: Stock media

YouTube API: Platform integration

Disclaimer: This tool is for educational purposes. Always follow YouTube's Terms of Service and Community Guidelines. The developers are not responsible for any content created using this tool.
