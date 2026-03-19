# Peeks.com Stream Downloader - Usage Guide

A clean, efficient downloader for Peeks.com streams using browser automation to capture stream URLs and FFmpeg for downloading.

## 🚀 Quick Start

```bash
# Download a stream by ID
python scripts/peeks-downloader.py 5978057

# Monitor and download a live stream
python scripts/peeks-downloader.py 5978057 live
```

## 📋 Available Commands

### 🎯 Individual Downloader (`peeks-downloader.py`)
The primary tool for reliable single-stream downloads.

```bash
# Basic usage
python scripts/peeks-downloader.py <stream-id>

# With full URL
python scripts/peeks-downloader.py "https://www.peeks.com/streams/stream-view?id=5978057"

# Enable debug logging
python scripts/peeks-downloader.py 5978057 --debug
```

### 🚀 Bulk Downloader (`peeks-bulk-downloader.py`)
Download multiple streams automatically from a JSON metadata file.

```bash
# Bulk download from user streams data
python scripts/peeks-bulk-downloader.py downloads/peeks_api/20011810843.json

# Limit number of downloads and add delay between them
python scripts/peeks-bulk-downloader.py <json-file> --limit 10 --delay 30
```

### 📊 Metadata Fetcher (`peeks-api-downloader.py`)
Fetch stream lists and metadata for a specific user.

```bash
# Get metadata for a user's streams
python scripts/peeks-api-downloader.py <user-id>

# Custom limit and pagination
python scripts/peeks-api-downloader.py <user-id> 50 0
```

### 🌊 Recent Streams (`peeks-recent-streams.py`)
Download the latest public streams from the main channel.

```bash
# Get 500 latest streams
python scripts/peeks-recent-streams.py
```

## 📂 Download Location
All files are saved to: `downloads/peeks_videos/`

## 🛠️ Requirements
- **FFmpeg**: Must be installed and available in your system PATH.
- **Chromium**: Installed via `playwright install chromium`.

## 💡 Pro Tips
- **Lossless Downloads**: The tool uses `ffmpeg -c copy` ensuring zero quality loss and maximum speed.
- **Smart Filenames**: Files are automatically named `{username}_{stream_id}_{description}.mp4`.
- **Duplicate Prevention**: The bulk downloader automatically skips files that have already been downloaded.
