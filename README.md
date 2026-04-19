<p align="center">
  <img src="https://img.shields.io/badge/🎵-SOUNDFORGE_AI-ff6b6b?style=for-the-badge&labelColor=1a1a2e&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJ3aGl0ZSI+PHBhdGggZD0iTTEyIDNMMiAyMWgyMEwxMiAzeiIvPjwvc3ZnPg==" alt="SoundForge AI"/>
</p>

<h1 align="center">🔥 SOUNDFORGE AI</h1>
<h3 align="center">The Autonomous Music Factory — AI Writes, Produces & Distributes Music While You Sleep</h3>

<p align="center">
  <img src="https://img.shields.io/badge/AI-Gemini%20+%20Claude-blueviolet?style=for-the-badge&logo=google" alt="AI"/>
  <img src="https://img.shields.io/badge/Music-Lyria%203%20Pro-ff4757?style=for-the-badge&logo=youtube-music" alt="Music"/>
  <img src="https://img.shields.io/badge/Distribution-YouTube%20+%20Pond5-red?style=for-the-badge&logo=youtube" alt="Distribution"/>
  <img src="https://img.shields.io/badge/Notifications-Telegram-26A5E4?style=for-the-badge&logo=telegram" alt="Telegram"/>
  <img src="https://img.shields.io/badge/Python-3.9+-green?style=for-the-badge&logo=python" alt="Python"/>
</p>

<p align="center">
  <b>An end-to-end AI agent that analyzes Spotify trends, generates original music tracks,<br/>creates YouTube videos with visualizers, and distributes to multiple platforms — fully automated, daily.</b>
</p>

---

## 🧠 What is SoundForge AI?

SoundForge AI is a **fully autonomous music production and distribution pipeline**. Every day at 9:00 AM, it:

1. 🔍 **Analyzes** Spotify trends and competitor patterns to pick the best niche
2. 🎵 **Generates** an original track using AI (with multi-provider fallback)
3. 🎬 **Creates** a YouTube video with audio visualizer + thumbnail
4. 📤 **Uploads** to YouTube (full video + Short) and Pond5 simultaneously
5. 📲 **Notifies** you via Telegram with results

**Zero human intervention.** The agent runs, creates, publishes, and earns — 24/7.

```
Monday: 🔄 Refresh weekly niche pool (4 Spotify trends + 3 evergreen)
        🔍 Analyze competitor winning patterns
Daily:  🎵 Pick today's niche → Generate track → Create video → Publish everywhere
        📲 Telegram report with links
Failed: 🔁 Auto-retry queue (max 2 pending per day)
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      SOUNDFORGE AI                          │
├──────────────┬──────────────────┬───────────────────────────┤
│  🧠 BRAIN     │  🎵 GENERATION    │  📤 DISTRIBUTION          │
│  ──────────   │  ──────────────   │  ────────────────         │
│  Niche Select │  Lyria 3 Pro     │  YouTube Data API v3     │
│  Trend Analyze│  ↓ fallback      │  YouTube Shorts          │
│  Competitor   │  Stable Audio    │  Pond5 FTP               │
│  Patterns     │  ↓ fallback      │  Telegram Notifier       │
│  Prompt Build │  MusicGen Large  │  Retry Queue             │
├──────────────┴──────────────────┴───────────────────────────┤
│  PIPELINE: FFmpeg Visualizer │ Thumbnails │ WAV→MP3 │ CSV   │
│  OBSERVABILITY: OpenTelemetry │ Structured Logging          │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 Multi-Provider Fallback Chain

The system never fails silently. If one AI music provider is down, it automatically falls to the next:

| Priority | Provider | Model | Quality | Latency |
|----------|----------|-------|---------|---------|
| 🥇 Primary | **Google Lyria 3 Pro** | lyria-3-pro-preview | Studio-grade WAV | ~60s |
| 🥈 Fallback 1 | **Stable Audio 2.5** | Stability AI | High-quality WAV | ~45s |
| 🥉 Fallback 2 | **MusicGen Large** | Meta via Replicate | Good WAV | ~90s |

Each provider gets a **prompt optimized for its architecture**:
- **Lyria**: Timestamped sections `[0:00] Intro` → `[0:30] Theme` → `[1:45] Outro`
- **Stable Audio**: BPM-first format with negative prompts
- **MusicGen**: Concise 5-axis prompt (genre + mood + instruments + tempo + quality)

## 🔍 Smart Niche Selection

Every Monday, the agent builds a **weekly pool of 7 niches**:

| Source | Count | Examples |
|--------|-------|---------|
| 📊 Spotify Trends | 4 niches | Whatever's trending that week |
| 🌿 Evergreen Pool | 3 niches | Lo-fi hip hop, ambient, cinematic, jazz... |

Competitor analysis runs weekly to extract:
- Winning title patterns and keywords
- Optimal video length and thumbnail styles
- Tag strategies that maximize discoverability

## 📁 Project Structure

```
soundforge-ai/
├── core/                          # Intelligence layer
│   ├── niche_analyzer.py              # Spotify trends + weekly pool
│   ├── competitor_analyzer.py         # YouTube competitor patterns
│   ├── prompt_builder.py             # Provider-specific prompt engineering
│   ├── provider_orchestrator.py      # Fallback chain orchestrator
│   ├── spotify_trend_analyzer.py     # Spotify API integration
│   ├── trend_analyzer.py            # Cross-platform trend analysis
│   └── retry.py                     # Exponential backoff (tenacity)
│
├── providers/                     # AI music generators
│   ├── lyria_provider.py             # Google Lyria 3 (Clip + Pro)
│   ├── stable_audio_provider.py      # Stability AI
│   └── replicate_provider.py        # Meta MusicGen via Replicate
│
├── pipeline/                      # Production & distribution
│   ├── video_creator.py              # FFmpeg visualizer + thumbnails
│   ├── youtube_uploader.py           # YouTube Data API v3
│   ├── pond5_uploader.py            # Pond5 upload (FTP)
│   └── telegram_notifier.py        # Daily reports
│
├── observability/                 # Monitoring
│   └── tracer.py                    # OpenTelemetry spans
│
├── tests/                         # Test suite
├── main.py                       # Daily orchestrator + scheduler
├── music_generator.py            # WAV→MP3 conversion
└── requirements.txt              # Dependencies
```

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/gastonchevarria/MusicAgent.git
cd MusicAgent/lyria-music-agent

# Configure
cp .env.example .env
# Edit .env with your API keys (see Configuration below)

# Install
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Test run (generates and publishes one track immediately)
python main.py --test

# Production (runs daily at 09:00)
python main.py
```

## 🔧 Configuration

All secrets via environment variables (never committed):

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API (for Lyria 3 + niche analysis) | ✅ |
| `STABILITY_API_KEY` | Stable Audio 2.5 fallback | Optional |
| `REPLICATE_API_TOKEN` | MusicGen fallback via Replicate | Optional |
| `POND5_EMAIL` / `POND5_PASSWORD` | Pond5 contributor account | For Pond5 |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | Notifications | For alerts |
| YouTube OAuth | `client_secrets.json` + `youtube_token.json` | For YouTube |

## 📊 Daily Output Example

Every day, the agent sends you a Telegram report like this:

```
🎵 SoundForge AI — Daily Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━
📀 "Midnight Echoes — Ambient Piano for Deep Focus"
🎹 Niche: ambient relajante para meditar
🤖 Provider: Lyria 3 Pro
🎬 YouTube: https://youtu.be/xxxxx
📱 Short: https://youtu.be/shorts/xxxxx
🛒 Pond5: ✅ Uploaded
━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## ⚠️ Disclaimer

This software is for **educational and research purposes**. Generated music is AI-created. Always verify licensing terms of each AI provider before commercial distribution.

---

<p align="center">
  <b>Built with 🔥 by <a href="https://github.com/gastonchevarria">@gastonchevarria</a></b><br/>
  <sub>Powered by Lyria 3 Pro • Stable Audio • MusicGen • FFmpeg • YouTube API</sub>
</p>
