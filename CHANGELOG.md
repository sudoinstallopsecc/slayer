# Changelog

All notable changes to SLAYER will be documented in this file.

## [4.0.0] - 2026-02-27

### Changed
- Merged standard and enterprise versions into a single unified entry point (slayer.py).
- Single CLI with four commands: test, request, config, info.
- Interactive shell mode when invoked without arguments.
- Two load testing engines: sync (threading + requests) and async (asyncio + aiohttp).
- Enterprise features load automatically with graceful fallback.
- Removed all redundant files, scripts, and documentation.
- Rewrote README.md and created USAGE.md in formal English.
- Cleaned up dependencies in requirements.txt.
- Added full project metadata to pyproject.toml.

### Removed
- slayer_enterprise_cli.py (merged into slayer.py).
- slayer_enterprise_enhanced.py (merged into slayer.py).
- demo.py (merged into slayer.py).
- Bash wrapper script (slayer).
- Redundant install scripts (install.sh, install.bat, setup.sh, kali_quickstart.sh, verify_kali.sh).
- Redundant documentation (GUIA_USO.md, KALI_GUIDE.md, KALI_INSTALL.md, QUICKSTART.md, README_ENTERPRISE.md).
- Internal reports (DELIVERY_REPORT.txt, PROJECT_COMPLETE.txt, EXECUTIVE_REPORT.md).
- Bundled wrk source tree (wrk-4.2.0/).

## [3.0.0] - 2026-01-01

### Added
- Async/await architecture using aiohttp.
- Modular enterprise package with 7 sub-modules.
- SSRF protection, input validation, rate limiting, JWT/API key auth.
- Multi-level caching (memory + Redis), circuit breakers, connection pooling.
- Prometheus metrics, structured logging, distributed tracing.
- Plugin/middleware system.
- Rich CLI output.

## [2.0.0] - 2025-12-01

### Added
- Basic HTTP request functionality.
- Threading support.
- Simple statistics.
- Color output.

## [1.0.0] - 2025-01-01

### Added
- Initial release.
- Basic GET/POST support.
