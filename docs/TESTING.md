# Testing Guide

## ✅ Test Status Overview (All Passing)

- **32+ Integration Tests**: All passing with verified reliability
- **Network Tests**: 21/21 successful with real website capture
- **HTML Capture Tests**: 26 HTML files successfully created during testing
- **Browser Automation**: Both headless and interactive modes verified

## Quick Reference

### Run All Tests
```bash
# Complete test suite (recommended)
python -m pytest tests/ -v

# Web capture integration tests
python -m pytest tests/integration/ -v

# Network-dependent tests
python -m pytest tests/network/ -v

# Peeks-specific tests  
python -m pytest tests/test_peeks_download_integration.py -v
```

### Pre-Development Checks (Fast - ~30 seconds)
```bash
# Basic functionality validation
python -m pytest tests/test_peeks_download_integration.py::TestPeeksVideoDownload::test_1_stream_lookup_api_accessibility -v
python -m pytest tests/test_peeks_download_integration.py::TestPeeksVideoDownload::test_5_ffmpeg_availability -v
python -m pytest tests/test_peeks_download_integration.py::TestPeeksVideoDownload::test_6_ffmpeg_command_building -v
```

### Web Capture Framework Tests
```bash
# HTML capture and storage (11 tests)
python -m pytest tests/integration/test_website_integration.py -v
python -m pytest tests/integration/test_local_website_integration.py -v

# Interactive browser automation  
python -m pytest tests/integration/test_non_headless_interaction.py -v

# API endpoint testing
python -m pytest tests/integration/test_api_integration.py -v
```

### After Code Changes (Medium - ~1 minute)
```bash
# Validation + URL extraction
python -m pytest tests/test_peeks_download_integration.py::TestPeeksVideoDownload::test_1_stream_lookup_api_accessibility tests/test_peeks_download_integration.py::TestPeeksVideoDownload::test_2_browser_url_extraction tests/test_peeks_download_integration.py::TestPeeksVideoDownload::test_5_ffmpeg_availability -v
```

### Full Integration (Slow - ~3 minutes)
```bash
# Complete end-to-end testing with downloads
python -m pytest tests/test_peeks_download_integration.py::TestPeeksVideoDownload::test_8_hls_downloader_integration tests/test_peeks_download_integration.py::TestPeeksVideoDownload::test_9_full_integration_test -v
```

## Test Categories

### Web Capture Framework Tests ✅
- **Website Integration**: Tests against real websites (Google, BBC, Amazon, DuckDuckGo)
- **Local File Testing**: Fast tests using local HTML files
- **Browser Interaction**: Visible browser automation testing
- **API Integration**: RESTful service endpoint testing
- **HTML Storage**: Automatic file creation and content persistence (26 files verified)
- **Network Monitoring**: Request/response interception and analysis

### Peeks Downloader Tests ✅
- **Lightweight Tests (No Downloads)**
  - **test_1**: API accessibility check
  - **test_3**: M3U8 playlist validation  
  - **test_4**: HLS segment accessibility
  - **test_5**: FFmpeg availability
  - **test_6**: FFmpeg command building

- **Browser Tests (URL Extraction)**
  - **test_2**: Browser automation and M3U8 extraction

- **Download Tests (Actual File Downloads)**
  - **test_7**: Direct FFmpeg test (5-second clip)
  - **test_8**: HLS downloader integration (full video)
  - **test_9**: Complete end-to-end integration (full video)

## Custom Stream Testing

Use different stream IDs for testing:

```bash
# Test with specific stream
export PEEKS_TEST_STREAM_ID=1234567
python -m pytest tests/test_peeks_download_integration.py -v

# Or for Windows PowerShell
$env:PEEKS_TEST_STREAM_ID="1234567"
python -m pytest tests/test_peeks_download_integration.py -v
```

## Troubleshooting

### Common Issues

**FFmpeg not found:**
```bash
# Run test 5 to diagnose
python -m pytest tests/test_peeks_download_integration.py::TestPeeksVideoDownload::test_5_ffmpeg_availability -v
```

**URL extraction failing:**
```bash
# Check browser automation
python -m pytest tests/test_peeks_download_integration.py::TestPeeksVideoDownload::test_2_browser_url_extraction -v -s
```

**Download timeouts:**
```bash
# Test with shorter clip first
python -m pytest tests/test_peeks_download_integration.py::TestPeeksVideoDownload::test_7_direct_ffmpeg_test -v
```

**Stream access issues:**
```bash
# Validate stream and API access
python -m pytest tests/test_peeks_download_integration.py::TestPeeksVideoDownload::test_1_stream_lookup_api_accessibility -v
```

## Development Workflow

1. **Before starting work**: Run pre-development checks
2. **After each change**: Run relevant component tests
3. **Before committing**: Run full test suite
4. **Before releases**: Run full suite multiple times to ensure reliability

## Test Environment

- **Default stream**: 5735957 (6:48 video, known working)
- **Download location**: Temporary directories (auto-cleaned)
- **Requirements**: Internet connection, FFmpeg, Playwright browser
- **Duration**: 1-3 minutes for full suite depending on network speed
