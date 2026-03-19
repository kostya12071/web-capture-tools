# Instructions for AI Coding Agents

Welcome to the **Web Downloader Suite** codebase. To work effectively and safely in this environment, you MUST follow these instructions.

## 🏁 Phase 1: Mandatory Reading
Before proposing or implementing ANY changes, you must read the following documents in order:
1.  **[README.md](../README.md)**: Overall project scope and tools.
2.  **[GROK_GUIDE.md](GROK_GUIDE.md)**: Specifics on the Grok Imagine implementation (highly complex).
3.  **[PEEKS_GUIDE.md](PEEKS_GUIDE.md)**: Peeks stream downloading logic.
4.  **[.github/copilot-instructions.md](../.github/copilot-instructions.md)**: Critical coding standards and core philosophy.

## 🏗️ Architecture & Philosophy
- **Modular Core**: All "smart" logic belongs in `lib/`. User-facing scripts in `scripts/` should be lightweight wrappers that call `lib/` modules.
- **Stateless REST + Optional WS**: For Grok, we use stateless REST requests for reliability, using a background WebSocket ONLY when required by the server for session anchoring.
- **Robustness Over Speed**: We use manual byte-buffering for NDJSON streams to ensure zero data loss during network jitter or abrupt connection closes.
- **Anti-Bot Bypass**: We use `curl_cffi` with Chrome impersonation for API calls and `curl` binaries for large file downloads to avoid TLS fingerprinting issues.

## 📏 Coding Standards
- **Type Safety**: Pydantic `BaseModel` is mandatory for all data structures. All functions MUST have type hints.
- **Documentation**: All public classes and methods MUST have docstrings.
- **Error Handling**: Use the custom exception hierarchy in `lib/core/core/exceptions.py`. Never catch a bare `Exception`.
- **Validation**: After every change, you must verify the tool with a real-world CLI command.

## ⚠️ Critical Constraints
- **Tests are Frozen**: Do not modify files in `tests/` unless explicitly requested.
- **No Experimental Code**: Do not leave `print()` statements, TODOs, or throwaway scripts in the `lib/` or `scripts/` directories. Use the `poc/` directory for experiments and delete them before merging.
- **Browser Automation**: Prefer Playwright for network interception and `curl_cffi` for direct API impersonation.

## 🛠️ Verification Workflow
1.  **Strategize**: Formulate a plan based on the existing guides.
2.  **Act**: Apply targeted changes to `lib/` first.
3.  **Validate**: Run the corresponding script in `scripts/` with the `--debug` flag to confirm behavior.
4.  **Sync**: Commit with clear, descriptive messages following the `Type: Description` format.
