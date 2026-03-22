# Web Capture Tools

A heavy-duty web research and analysis suite for deep browser session recording, network traffic interception, cookie capture, and scraper design-time development.

## Project Structure

- **lib/capture/**: Core engine for browser orchestration and session management.
  - browser/: Low-level Playwright/Chrome profile management.
  - core/engine.py: The WebCaptureEngine, the primary entry point for research sessions.
  - network/: Interceptors for capturing and analyzing XHR/Fetch traffic.
  - storage/: Handlers for session persistence, cookies, and local profiles.
- **lib/cookies/**: Lightweight CDP-based cookie extraction (no Playwright dependency).
  - cdp_client.py: Async Chrome DevTools Protocol client via WebSocket.
  - browser_launcher.py: Cross-platform Chrome launch with CDP debugging.
  - profile_manager.py: JSON profile I/O with key-based matching and auto-naming.
  - cli.py: Command-line interface for cookie capture.
- **scripts/**: CLI tools for interactive and automated research.
  - web-capture-cli.py: The main research interface (Playwright-based).
  - capture-cookies.py: Generic cookie capture tool (CDP-based, no Playwright).
  - launch-login.ps1: Utility for managing persistent Chrome logins.
- **docs/**: Extensive documentation on the Web Capture Framework and Peeks architecture.

## Cookie Capture Tool

The `capture-cookies.py` script is a lightweight, Playwright-free tool for extracting browser cookies via Chrome DevTools Protocol.

### Usage

```bash
python scripts/capture-cookies.py <domain> <output_file> --cookies <names> --key <field> [options]
```

### Examples

```bash
# Grok cookies (with field mapping)
python scripts/capture-cookies.py grok.com config/grok_profiles.json \
    --cookies cf_clearance,sso,x-userid --key user_id --mapping x-userid:user_id --launch

# Instagram cookies (auto-name new profiles)
python scripts/capture-cookies.py instagram.com config/instagram_profiles.json \
    --cookies sessionid,csrftoken,ds_user_id --key ds_user_id --launch --auto

# Peeks cookies (connect to existing browser)
python scripts/capture-cookies.py peeks.com config/peeks_profiles.json \
    --cookies session --key user_id
```

### Options

| Flag | Description |
|------|-------------|
| `--cookies` | Required. Comma-separated cookie names to capture |
| `--key` | Required. Field that identifies unique users (for profile matching) |
| `--launch` | Launch Chrome if not running |
| `--auto` | Auto-assign profile names (profile1, profile2...) for new users |
| `--close` | Close browser after capturing cookies |
| `--mapping` | Cookie-to-field name mapping (e.g., `x-userid:user_id`) |
| `--port` | CDP port (default: 9222) |
| `--profile-dir` | Chrome user data directory |

### Profile Format

Profiles are saved as a JSON array:

```json
[
  {
    "name": "profile1",
    "cf_clearance": "...",
    "sso": "...",
    "user_id": "abc-123",
    "last_updated": "2026-03-21 15:30:00"
  }
]
```

## Maintenance Guidelines

1. **Isolation Strategy**: This repository is the \"Source of Truth\" for complex browser interactions. It should remain independent of the runtime scrapers.
2. **Dependency Management**: Uses heavy dependencies (Playwright, Chrome Profiles). Update config/capture-requirements.txt when adding new analysis capabilities.
3. **Chrome Profiles**: Persistent sessions are stored locally. Treat this as sensitive data (contains cookies/auth).

## Development Philosophy

This tool is intended for **Design-Time Research**. It is used to identify API patterns, hidden headers, and network flows. Once a pattern is identified here, the lightweight extraction logic should be ported to the respective runtime scraper in the web-downloader monorepo.

## For Testers (QA)

Tests for this repo are currently exploratory. Use the web-capture-cli.py to verify that sessions can be initialized, traffic can be intercepted, and profiles are correctly persisted across restarts. Use cases for these tools can be found in the web-downloader monorepo's use-cases/capture-tools/ directory.
