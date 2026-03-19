# Web Capture Tools

A heavy-duty web research and analysis suite for deep browser session recording, network traffic interception, and scraper design-time development.

## Project Structure

- lib/capture/: Core engine for browser orchestration and session management.
  - rowser/: Low-level Playwright/Chrome profile management.
  - core/engine.py: The WebCaptureEngine, the primary entry point for research sessions.
  - 
etwork/: Interceptors for capturing and analyzing XHR/Fetch traffic.
  - storage/: Handlers for session persistence, cookies, and local profiles.
- scripts/: CLI tools for interactive and automated research.
  - web-capture-cli.py: The main research interface.
  - launch-login.ps1: Utility for managing persistent Chrome logins.
- docs/: Extensive documentation on the Web Capture Framework and Peeks architecture.

## Maintenance Guidelines

1. **Isolation Strategy**: This repository is the \"Source of Truth\" for complex browser interactions. It should remain independent of the runtime scrapers.
2. **Dependency Management**: Uses heavy dependencies (Playwright, Chrome Profiles). Update config/capture-requirements.txt when adding new analysis capabilities.
3. **Chrome Profiles**: Persistent sessions are stored locally. Treat this as sensitive data (contains cookies/auth).

## Development Philosophy

This tool is intended for **Design-Time Research**. It is used to identify API patterns, hidden headers, and network flows. Once a pattern is identified here, the lightweight extraction logic should be ported to the respective runtime scraper in the web-downloader monorepo.

## For Testers (QA)

Tests for this repo are currently exploratory. Use the web-capture-cli.py to verify that sessions can be initialized, traffic can be intercepted, and profiles are correctly persisted across restarts. Use cases for these tools can be found in the web-downloader monorepo's use-cases/capture-tools/ directory.
