# Web Downloader Suite - AI Agent Context

## Project Overview
The **Web Downloader Suite** is a comprehensive Python-based collection of specialized web content downloaders with robust automation, anti-bot bypass mechanisms, and reliable stream extraction capabilities.

**Key Technologies:**
- Python 3.11+
- Playwright (Browser automation and network interception)
- `curl_cffi` (Direct API impersonation & TLS fingerprint bypass)
- Pydantic (Mandatory data structure validation and type safety)
- `aiohttp`, `requests`, `httpx`

**Architecture:**
- **Modular Core:** All "smart" logic belongs in the `lib/` directory (`lib/scrapers/`, `lib/capture/`, `lib/core/`).
- **CLI Wrappers:** User-facing scripts are located in the `scripts/` directory. These should be lightweight wrappers calling modules from `lib/`.

## Building and Running

**Dependencies Installation:**
```bash
pip install -r requirements.txt
playwright install chromium
```

**Running Tools:**
Run the scripts directly from the `scripts/` directory or use the registered CLI commands (if installed as a package):
```bash
python scripts/web-capture-cli.py <URL>
python scripts/grok-imagine.py
python scripts/peeks-downloader.py
python scripts/instagram-downloader.py
```

## Development Conventions & Constraints

- **Type Safety:** `Pydantic BaseModel` is mandatory for all data structures. All functions MUST have type hints.
- **Documentation:** All public classes and methods MUST have docstrings.
- **Error Handling:** Use the custom exception hierarchy located in `lib/core/core/exceptions.py`. Never catch a bare `Exception`.
- **Network Resilience:** Use manual byte-buffering for NDJSON streams to prevent data loss. Prefer stateless REST requests for reliability.
- **Testing Constraints:** Files in `tests/` are frozen and should not be modified unless explicitly requested.
- **Clean Code:** No experimental code, `print()` statements, TODOs, or throwaway scripts should be left in `lib/` or `scripts/`. Use `poc/` for experiments and delete them before merging.
- **Validation Workflow:** After making changes to `lib/`, validate by running the corresponding script in `scripts/` with the `--debug` flag. Commit messages must follow the `Type: Description` format.

## Key References
- `README.md`: General usage guides.
- `docs/INSTRUCTIONS.md`: Full coding standards and philosophy.
- `docs/GROK_GUIDE.md`: Grok Imagine implementation details.
- `docs/PEEKS_GUIDE.md`: Peeks stream downloading logic.
