# SLAYER Usage Guide

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Operating Modes](#operating-modes)
5. [CLI Commands](#cli-commands)
6. [Interactive Mode](#interactive-mode)
7. [Testing Engines](#testing-engines)
8. [Enterprise Features](#enterprise-features)
9. [Configuration Reference](#configuration-reference)
10. [Examples](#examples)
11. [Troubleshooting](#troubleshooting)

---

## Overview

SLAYER is a unified HTTP load testing and request framework. It combines a
simple interactive interface with enterprise-grade capabilities such as async
I/O, connection pooling, circuit breakers, rate limiting, and real-time
metrics collection.

The tool operates in two primary modes:

- **Interactive mode** -- a command-line shell for configuring and running
  tests interactively.
- **CLI mode** -- direct command execution for scripted and automated
  workflows.

Two load testing engines are available:

| Engine | Library  | Concurrency Model | Best For                     |
|--------|----------|--------------------|------------------------------|
| sync   | requests | Threading          | Simple tests, low concurrency|
| async  | aiohttp  | asyncio            | High concurrency, throughput |

---

## Installation

### Requirements

- Python 3.8 or later.
- `pip` package manager.

### Steps

```bash
git clone https://github.com/sudoinstallopsecc/slayer.git
cd slayer
pip install -r requirements.txt
```

If you only need basic functionality (sync engine), install the minimal
dependencies:

```bash
pip install -r requirements-basic.txt
pip install click rich
```

### Verify Installation

```bash
python slayer.py --version
python slayer.py info
```

---

## Quick Start

### Run a load test from the command line

```bash
python slayer.py test -u https://httpbin.org/get -n 200 -c 20
```

This sends 200 GET requests to the target URL with 20 concurrent threads.

### Make a single request

```bash
python slayer.py request -u https://httpbin.org/get -v
```

### Launch interactive mode

```bash
python slayer.py
```

---

## Operating Modes

### CLI Mode

Invoke SLAYER with a subcommand to execute operations directly:

```bash
python slayer.py <command> [options]
```

Available commands:

| Command   | Description                                  |
|-----------|----------------------------------------------|
| `test`    | Run an HTTP load test against a target URL.  |
| `request` | Make a single HTTP request.                  |
| `config`  | Generate a sample configuration file.        |
| `info`    | Display version and system information.      |

### Interactive Mode

When invoked without a subcommand, SLAYER enters an interactive shell:

```bash
python slayer.py
```

The shell provides a prompt (`slayer>`) where you can configure parameters
and run tests without restarting the tool.

---

## CLI Commands

### test

Run an HTTP load test.

```
python slayer.py test [OPTIONS]
```

| Option            | Short | Default | Description                              |
|-------------------|-------|---------|------------------------------------------|
| `--url`           | `-u`  |         | Target URL (required).                   |
| `--requests`      | `-n`  | 100     | Total number of requests.                |
| `--concurrency`   | `-c`  | 10      | Number of concurrent threads/connections.|
| `--method`        | `-m`  | GET     | HTTP method.                             |
| `--delay`         | `-d`  | 0.0     | Delay between requests per thread (s).   |
| `--duration`      | `-t`  |         | Max duration in seconds (overrides -n).  |
| `--data`          |       |         | Request body.                            |
| `--header`        | `-H`  |         | Custom header (key:value). Repeatable.   |
| `--timeout`       |       | 10      | Request timeout in seconds.              |
| `--engine`        |       | sync    | Engine: `sync` or `async`.               |
| `--output`        | `-o`  |         | Save results to a JSON file.             |

**Examples:**

```bash
# 500 GET requests, 50 concurrent threads
python slayer.py test -u https://example.com -n 500 -c 50

# POST with custom header and body
python slayer.py test -u https://api.example.com/data \
    -m POST \
    -H "Authorization:Bearer TOKEN" \
    --data '{"key":"value"}' \
    -n 100

# Run for 30 seconds instead of a fixed request count
python slayer.py test -u https://example.com -t 30 -c 20

# Use the async engine for higher throughput
python slayer.py test -u https://example.com -n 1000 -c 100 --engine async

# Save results to file
python slayer.py test -u https://example.com -n 500 -o results.json
```

### request

Make a single HTTP request and display the response.

```
python slayer.py request [OPTIONS]
```

| Option     | Short | Default | Description                            |
|------------|-------|---------|----------------------------------------|
| `--url`    | `-u`  |         | Target URL (required).                 |
| `--method` | `-m`  | GET     | HTTP method.                           |
| `--header` | `-H`  |         | Custom header (key:value). Repeatable. |
| `--data`   | `-d`  |         | Request body (JSON or plain text).     |
| `--output` | `-o`  |         | Save response body to file.            |
| `--verbose`| `-v`  | false   | Show response body.                    |

**Examples:**

```bash
# Simple GET
python slayer.py request -u https://httpbin.org/get

# POST with JSON body
python slayer.py request -u https://httpbin.org/post \
    -m POST \
    -d '{"name":"test"}' \
    -v

# Save response to file
python slayer.py request -u https://httpbin.org/get -o response.txt
```

### config

Generate a sample configuration file.

```bash
python slayer.py config -o my_config.json
```

### info

Display version and system information.

```bash
python slayer.py info
```

---

## Interactive Mode

After launching `python slayer.py`, the following commands are available at
the `slayer>` prompt:

| Command                    | Description                        |
|----------------------------|------------------------------------|
| `target <url>`             | Set the target URL.                |
| `method <GET\|POST\|...>`  | Set the HTTP method.               |
| `threads <n>`              | Set the number of concurrent threads.|
| `requests <n>`             | Set the total request count.       |
| `duration <seconds>`       | Set the test duration.             |
| `delay <seconds>`          | Set per-thread delay between requests.|
| `data <text>`              | Set the request body.              |
| `header <key:value>`       | Add a custom header.               |
| `engine <sync\|async>`     | Select the testing engine.         |
| `timeout <seconds>`        | Set the request timeout.           |
| `run`                      | Start the load test.               |
| `request`                  | Send a single request to the target.|
| `status`                   | Display the current configuration. |
| `clear`                    | Clear the screen.                  |
| `help`                     | Show the help message.             |
| `exit`                     | Quit the interactive shell.        |

### Example Session

```
slayer> target https://httpbin.org/get
Target set: https://httpbin.org/get

slayer> threads 20
Threads set: 20

slayer> requests 500
Requests set: 500

slayer> run
```

---

## Testing Engines

### Sync Engine (default)

The sync engine uses Python `threading` and the `requests` library. It
creates a pool of worker threads that issue HTTP requests concurrently.

- Suitable for moderate concurrency levels (up to ~100 threads).
- Simple and reliable.
- Supports per-thread delay between requests.

### Async Engine

The async engine uses `asyncio` and `aiohttp` for non-blocking I/O. A
single event loop manages all connections via an `asyncio.Semaphore`.

- Recommended for high-concurrency scenarios (100+ connections).
- Lower memory overhead per connection.
- Higher throughput on I/O-bound workloads.

Select the engine with:

```bash
python slayer.py test -u <url> --engine async
```

Or in interactive mode:

```
slayer> engine async
```

---

## Enterprise Features

SLAYER integrates with the `slayer_enterprise` package, which provides
production-grade components:

| Module       | Features                                         |
|--------------|--------------------------------------------------|
| `core`       | Async HTTP client, session management, config.   |
| `security`   | SSRF protection, input validation, rate limiting, authentication. |
| `performance`| Response caching (memory/Redis), circuit breakers, connection pooling. |
| `monitoring` | Prometheus metrics, structured logging, distributed tracing (W3C). |
| `middleware`  | Plugin system for request/response processing.  |
| `testing`    | Traffic patterns, intelligent throttling, load test metrics. |

These features are used automatically when the package is installed. If the
enterprise package is not present, SLAYER falls back to the basic sync and
async engines without any loss of core functionality.

---

## Configuration Reference

### JSON Configuration File

Generate a template with:

```bash
python slayer.py config -o slayer_config.json
```

The generated file contains the following fields:

```json
{
  "target_url": "https://httpbin.org/get",
  "method": "GET",
  "requests": 500,
  "concurrency": 20,
  "delay": 0.0,
  "timeout": 10,
  "engine": "sync",
  "headers": {},
  "data": null
}
```

### Environment Variables

The enterprise features can be configured via environment variables:

| Variable                | Description                  | Default      |
|-------------------------|------------------------------|--------------|
| `SLAYER_ENV`            | Environment name.            | production   |
| `SLAYER_DEBUG`          | Enable debug mode.           | false        |
| `SLAYER_VERIFY_SSL`     | Verify SSL certificates.     | true         |
| `SLAYER_AUTH_TOKEN`     | Bearer authentication token. |              |
| `SLAYER_REDIS_URL`      | Redis URL for caching.       |              |
| `SLAYER_CACHE_TTL`      | Cache TTL in seconds.        | 300          |
| `SLAYER_REQUEST_TIMEOUT`| Request timeout in seconds.  | 30           |
| `SLAYER_LOG_LEVEL`      | Log level (DEBUG, INFO, ...).| INFO         |
| `SLAYER_METRICS_PORT`   | Prometheus metrics port.     | 9090         |

---

## Examples

### Basic Load Test

```bash
python slayer.py test -u https://httpbin.org/get -n 100 -c 10
```

### High-Concurrency Async Test

```bash
python slayer.py test -u https://httpbin.org/get -n 5000 -c 200 --engine async
```

### Duration-Based Test

```bash
python slayer.py test -u https://httpbin.org/get -t 60 -c 50
```

### POST Test with JSON Body

```bash
python slayer.py test \
    -u https://httpbin.org/post \
    -m POST \
    --data '{"key":"value"}' \
    -H "Content-Type:application/json" \
    -n 200 -c 10
```

### Save and Analyze Results

```bash
python slayer.py test -u https://example.com -n 1000 -c 50 -o results.json
cat results.json | python -m json.tool
```

---

## Troubleshooting

### "No module named 'click'" or "No module named 'rich'"

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### "No module named 'aiohttp'" when using --engine async

Install the async dependencies:

```bash
pip install aiohttp
```

### Connection errors or timeouts

- Verify the target URL is reachable: `curl <url>`.
- Increase the timeout: `--timeout 30`.
- Reduce concurrency if the server is overloaded.

### High error rate

- Check the HTTP status codes in the results table.
- The target server may be rate-limiting your requests.
- Add a delay between requests: `--delay 0.1`.

### KeyboardInterrupt during a test

Press `Ctrl+C` to stop a running test. Partial results will be displayed.

---

## License

MIT License. See the LICENSE file for details.
