# Instagram Downloader Development Plan

## Project Overview

Build a reliable Instagram video downloader with a clean and testable architecture. The runtime focuses on navigation, network capture, selecting the best progressive video URL, and downloading. Research-oriented capture and analysis live in the separate `instagram_research` project.

## Development Phases

### Phase 1: Research & Foundation ✅ (Completed)
- [x] Set up project structure with modular architecture
- [x] Create basic data models and configuration
- [x] Set up integration test framework
- [x] Create research tools for API analysis
- [x] Analyze Instagram's network requests and API structure (GraphQL + CDN URL patterns confirmed)

### Phase 2: Core Components (In Progress)
- [x] URL parsing and validation (implemented in CLI)
- [x] Browser automation for content extraction (Playwright integrated)
- [x] File management and naming (handled in downloader; safe, simple filenames)
- [ ] Basic API helper for public content (optional – GraphQL read helper in research or thin client)
- [N/A] Separate network client with session management (using Playwright for session + aiohttp for download)

### Phase 3: Download Engine (In Progress)
- [x] Content downloader (progressive MP4 complete; best-quality selection)
- [N/A] FFmpeg integration (not required for progressive; consider only if adding DASH)
- [x] Progress tracking and error handling (chunked progress logs, statuses)
- [ ] Retry logic and rate limiting (config present; needs wiring)

### Phase 4: Authentication & Advanced Features (Planned)
- [x] Session management and authentication (reuses existing Instagram browser session via Playwright)
- [ ] Private content access (requires authenticated flow hardening)
- [ ] Stories and temporary content handling
- [ ] Batch downloading capabilities

### Phase 5: Testing & Polish (Planned)
- [ ] Comprehensive integration tests (add more failure-mode coverage)
- [ ] Performance optimization (download throughput and page timing)
- [ ] Error handling improvements (targeted edge cases)
- [ ] Documentation and user guide (expand CLI usage and troubleshooting)

## Research Tasks (Ongoing in `instagram_research`)

### 1. Network Request Analysis
Use the research tooling to analyze and document:
- [x] Public post loading (`/p/[ID]/`)
- [x] Reel loading (`/reel/[ID]/`)
- [x] GraphQL endpoints and queries (owner.username confirmed from GraphQL JSON)
- [x] Video URL extraction patterns (progressive URLs from cdninstagram; efg parsing)
- [ ] Authentication flow (documented partially; formalize steps and selectors)

### 2. API Structure Documentation
Document:
- [ ] GraphQL query hashes and parameters (note they change over time)
- [ ] Response data structures (map fields used for owner.username, video versions)
- [ ] Video quality options and URLs (progressive vs DASH)
- [ ] Rate limiting behavior
- [ ] CSRF token handling

### 3. Authentication Research
Understand:
- [ ] Login flow and session cookies
- [ ] CSRF token generation
- [ ] Session persistence
- [ ] Access restrictions and permissions

## Technical Challenges

### High Priority
1. **Authentication Complexity**: Instagram requires login for most content
2. **Bot Detection**: Aggressive anti-automation measures
3. **Rate Limiting**: Request throttling and IP blocking
4. **Dynamic Content**: Heavy JavaScript rendering required

### Medium Priority
1. **GraphQL Complexity**: Complex API structure with evolving query hashes
2. **Video Format Variations**: Multiple qualities and delivery methods
3. **Content Type Differences**: Posts, reels, stories, IGTV have different structures
4. **Mobile vs Web**: Different APIs and response formats

### Low Priority
1. **Filename Conflicts**: Handling duplicate content
2. **Storage Management**: Large file handling
3. **Progress Reporting**: Real-time download status

## Architecture Notes

Benefits:
1. Clean separation between runtime downloader and research tooling
2. Easy testing with focused units and integration flows
3. Maintainable structure with centralized config and models
4. Extensible: can add DASH merging and batch flows later
5. Consistent error and status handling via enums/models

## Development Workflow

### Daily Development
1. Run a small set of integration tests to verify environment
2. Develop targeted changes (runtime or research), keep scope small
3. Run relevant tests (unit/integration) and a quick CLI smoke test
4. Update plan/docs with findings as needed

### Research Sessions
1. Network Analysis: Use DevTools + research tooling
2. Data Collection: Save request/response samples (in research project)
3. Pattern Analysis: Document findings (username source, quality tags)
4. Test Updates: Update tests based on validated patterns

### Testing Strategy
- Unit Tests: Individual component testing
- Integration Tests: Component interaction testing
- End-to-End Tests: CLI-based download smoke tests
- Research Tests: API structure validation (in research project)

## Success Metrics

### Phase 1 Success (Research)
- [x] Successful network request capture
- [x] Basic Instagram connectivity
- [x] Public content URL parsing
- [x] Initial API response analysis

### Phase 2 Success (Core Components)
- [x] URL parsing for supported content types (post/reel)
- [x] Successful public content extraction (via Playwright + network capture)
- [x] Basic file download capability (aiohttp progressive)
- [ ] Working integration tests (expand failure-mode coverage)

### Phase 3 Success (Download Engine)
- [x] Complete video downloads (progressive)
- [x] Best-quality selection logic
- [ ] Error recovery (retries/backoff)
- [ ] Performance benchmarks

### Final Success
- [ ] Reliable downloads for all public content types
- [ ] Authentication for private content
- [ ] Comprehensive error handling
- [ ] User-friendly interface
- [ ] Complete documentation

## Getting Started

### Immediate Next Steps
1. Add basic retry/backoff for file downloads and network capture
2. Expand integration tests to include failure modes (auth fail, no video found, CDN 403)
3. In `instagram_research`: add a small extractor that reads page/GraphQL JSON and outputs owner.username; wire CLI to optionally include username in output/filename once verified
4. Optional: add a thin GraphQL helper (read-only) to fetch owner.username when a session is present

### Development Environment Setup
```bash
# Install automation and research helpers
pip install playwright requests beautifulsoup4 lxml

# Install browser for automation
playwright install chromium

# Run tests
python -m pytest -q
```

This plan keeps runtime minimal and robust, with deeper analysis moved to the research project. As patterns stabilize (e.g., reliable username extraction), we can safely upstream them to the runtime and CLI.
