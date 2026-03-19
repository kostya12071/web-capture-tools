# Web Content Downloader Suite

A comprehensive collection of specialized web content downloaders with robust automation and reliable stream extraction capabilities.

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Install Chromium for browser automation
playwright install chromium

# 3. Use a tool (e.g., capture a webpage)
python scripts/web-capture-cli.py https://example.com
```

## 🛠️ Available Tools

### 🎨 Grok Imagine Suite
Full control over Grok-3 image and video generation.
- **[Grok Usage Guide](docs/GROK_GUIDE.md)** - Images, videos, and gallery management.
- `scripts/grok-imagine.py`: Main CLI tool.
- `scripts/grok-cookie-monitor.py`: Automated auth capture.

### 🎯 Peeks.com Downloader
High-performance HLS stream downloader with metadata support.
- **[Peeks Usage Guide](docs/PEEKS_GUIDE.md)** - Individual and bulk downloads.
- `scripts/peeks-downloader.py`: Reliable single-stream downloads.
- `scripts/peeks-bulk-downloader.py`: Batch processing.

### 🌐 Web Capture Framework
Advanced web content capture with HTML storage and network monitoring.
- **[Framework Guide](docs/WEB_CAPTURE_FRAMEWORK.md)** - Deep dive into core features.
- `scripts/web-capture-cli.py`: The Swiss Army knife for web scraping.

### 📸 Instagram Downloader
Download reels, posts, and stories.
- **[Instagram Guide](docs/INSTAGRAM_DEVELOPMENT_PLAN.md)** - Setup and usage.
- `scripts/instagram-downloader.py`: Direct content fetching.

## 🏗️ Architecture & Development

This project follows a modular architecture where user-facing scripts in `scripts/` utilize reusable logic from the `lib/` directory.

- **`lib/scrapers/`**: Site-specific extraction and generation logic.
- **`lib/capture/`**: General-purpose browser automation and network monitoring.
- **`lib/core/`**: Shared networking, models, and utilities.

For detailed coding standards and architectural rules, see **[AI Agent Instructions](docs/INSTRUCTIONS.md)**.

## 🧪 Verification & Testing

The codebase is backed by an extensive test suite.
- **[Testing Guide](docs/TESTING.md)** - How to run and validate changes.

---
*Educational and personal use only. Please respect the terms of service of the target websites.*
