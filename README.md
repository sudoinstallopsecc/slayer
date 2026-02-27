# SLAYER -- HTTP Load Testing and Request Framework

SLAYER is a unified HTTP load testing tool that combines a simple interactive
interface with enterprise-grade features. It supports both synchronous
(threading) and asynchronous (aiohttp) engines, connection pooling, circuit
breakers, rate limiting, caching, and real-time metrics.

## Installation

### Requirements

- Python 3.8 or later
- pip

### Setup

```bash
git clone https://github.com/sudoinstallopsecc/slayer.git
cd slayer
pip install -r requirements.txt
```

### Verify

```bash
python slayer.py info
```

## Quick Start

### Load Test

```bash
python slayer.py test -u https://httpbin.org/get -n 200 -c 20
```

### Single Request

```bash
python slayer.py request -u https://httpbin.org/get -v
```

### Interactive Mode

```bash
python slayer.py
```

## CLI Commands

| Command   | Description                                |
|-----------|--------------------------------------------|
| `test`    | Run a load test against a target URL.      |
| `request` | Make a single HTTP request.                |
| `config`  | Generate a sample configuration file.      |
| `info`    | Display version and system information.    |

### Examples

```bash
# 1000 requests, 100 concurrent, async engine
python slayer.py test -u https://httpbin.org/get -n 1000 -c 100 --engine async

# POST with custom headers
python slayer.py test -u https://api.example.com/data \
    -m POST \
    -H "Content-Type:application/json" \
    --data '{"key":"value"}' \
    -n 200 -c 20

# Duration-based test (60 seconds)
python slayer.py test -u https://example.com -t 60 -c 50

# Save results to JSON
python slayer.py test -u https://example.com -n 500 -o results.json
```

## Engines

| Engine | Library  | Concurrency    | Best For                      |
|--------|----------|----------------|-------------------------------|
| sync   | requests | Threading      | Moderate concurrency (<100)   |
| async  | aiohttp  | asyncio        | High concurrency (100+)       |

## Enterprise Features

When the `slayer_enterprise` package is installed, the following features are
available automatically:

- **Security** -- SSRF protection, input validation, rate limiting, JWT/API key auth.
- **Performance** -- Multi-level caching (memory + Redis), circuit breakers, connection pooling.
- **Monitoring** -- Prometheus metrics, structured logging, distributed tracing.
- **Middleware** -- Plugin system for request/response processing.
- **Testing** -- Traffic patterns, intelligent throttling, distributed coordination.

If the enterprise package is not present, SLAYER falls back to the basic
engines without loss of core functionality.

## Project Structure

```
slayer/
  slayer.py                  # Unified entry point (CLI + interactive)
  slayer_enterprise/         # Enterprise feature library
    core/                    # Async client, config, sessions
    security/                # SSRF, validation, auth, rate limiting
    performance/             # Cache, circuit breaker, connection pool
    monitoring/              # Metrics, logging, tracing
    middleware/              # Plugin system
    testing/                 # Traffic patterns, throttling
  tests/                     # Test suite
  config/                    # Configuration files
  docs/                      # Documentation
```

## Documentation

- [USAGE.md](USAGE.md) -- Complete usage guide with all options and examples.
- [docs/EXECUTIVE_REPORT.md](docs/EXECUTIVE_REPORT.md) -- Technical report.
- [examples/](examples/) -- Code examples.

## License

MIT License. See the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is intended for authorized testing and performance analysis only.
Users are responsible for ensuring they have proper authorization before
testing any system.
