# SLAYER - HTTP Load Testing Tool

SLAYER is a command-line HTTP load testing tool written in Python. It drives
configurable amounts of traffic at a target — a fixed rate, a ramp-up, a
short spike, or a weighted mix of endpoints and multi-step user flows — and
reports back latency percentiles, throughput, and error breakdowns so you
can see how a server behaves under load.

## Features

- Interactive configuration wizard with step-by-step guidance, plus a fully non-interactive CLI mode for automation and CI
- Multiple traffic patterns: Constant, Ramp-up, and Spike, scheduled with sub-second precision
- Response validation capabilities: HTTP status code verification and response content matching
- Custom headers, JSON/plain-text request bodies, Bearer token and HTTP Basic authentication
- SSL certificate verification toggle for self-signed/internal targets
- Connection reuse (pooled `requests.Session`) so the tool itself isn't the bottleneck under high concurrency
- Two execution engines: OS threads (default, up to 1000 concurrent) or an aiohttp-based async engine for a
  substantially higher requests/sec ceiling on the same hardware
- Save/load test configuration as JSON, and export the final report as JSON
- Multi-endpoint scenarios with weighted request selection and a per-endpoint report breakdown
- Multi-step, session-aware flows: extract values from one response, reuse them (and cookies) in the next step, abort the flow early on failure
- Parameterized request data (`{{uuid}}`, `{{random_int}}`, `{{timestamp}}`, `{{counter}}`) usable in bodies/headers on any test
- Optional warm-up period excluded from measured statistics
- CI-friendly exit codes (`--fail-on-error-rate`, `--fail-on-p95`, `--fail-on-p99`, `--fail-on-avg-latency`)
- An explicit authorization confirmation before every test run (see "Responsible Use" below)
- Real-time monitoring with reports every 10 seconds, including a live latency/RPS trend sparkline
- Comprehensive statistics including minimum, maximum, average, median, P95, and P99 latencies
- Support for multiple HTTP methods: GET, POST, PUT, PATCH, DELETE
- Concurrent connection control up to 1000 simultaneous threads (or in-flight requests in async mode)
- Detailed error breakdown: timeouts, connection failures, and validation errors

## Responsible Use

SLAYER generates real, sustained HTTP traffic against a target. The exact same
mechanism used for legitimate load testing can be used to disrupt a service
you don't own or don't have permission to test. Only run it against systems
you own or are explicitly authorized to test. Every test run — interactive or
via `--url` — requires an explicit authorization confirmation before any
traffic is sent; pass `--yes` only in automated pipelines where authorization
has already been established out of band.

## Installation

### Requirements

- Python 3.9 or higher
- The requests library
- `aiohttp` (optional, only needed for `--engine async`): `pip install aiohttp`

### Installation Options

**Option 1: Using the Installation Script (Recommended)**

```bash
# Clone the repository
git clone https://github.com/sudoinstallopsecc/slayer.git
cd slayer

# Run the installation script
bash install.sh

# Run the tool
python3 slayer.py
```

**Option 2: Manual Installation**

```bash
# Clone the repository
git clone https://github.com/sudoinstallopsecc/slayer.git
cd slayer

# Install dependencies
pip install requests

# Grant execution permissions
chmod +x slayer.py

# Run the tool
python3 slayer.py
```

**Option 3: Install as Python Module**

```bash
# Clone the repository
git clone https://github.com/sudoinstallopsecc/slayer.git
cd slayer

# Install using pip
pip install .

# Run the tool using the command line entry point
slayer
```

## Usage

### Non-Interactive (CLI) Mode

Passing `--url` (or `--config`) skips the interactive wizard entirely and runs
a single test from command-line flags — ideal for CI pipelines and scripted
runs.

```bash
python3 slayer.py \
  --url https://api.example.com/endpoint \
  --method POST \
  --threads 100 \
  --duration 60 \
  --pattern ramp-up --rps 200 --start-rps 20 \
  --validation status \
  --header "X-Test-Run: nightly" \
  --auth-bearer "$API_TOKEN" \
  --json-body --body '{"ping": true}' \
  --timeout 10 \
  --output report.json \
  --yes
```

Key flags:

| Flag | Purpose |
|------|---------|
| `--url` | Target URL (required, unless supplied via `--config`) |
| `--method` | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` |
| `--threads` | Concurrency (1-1000): OS threads, or in-flight requests with `--engine async` |
| `--engine` | `threads` (default) or `async` (aiohttp, higher RPS ceiling — see below) |
| `--duration` | Test duration in seconds (1-3600) |
| `--pattern` | `constant`, `ramp-up`, or `spike` |
| `--rps` | Target requests per second |
| `--start-rps` / `--spike-duration` | Pattern-specific parameters |
| `--timeout` | Per-request timeout in seconds |
| `--validation` | `none`, `status`, or `content` (with `--validation-keyword`) |
| `--header "Key: Value"` | Custom header, repeatable |
| `--body` / `--body-file` | Request body (use with `--json-body` to parse/send as JSON) |
| `--auth-bearer` | Sets an `Authorization: Bearer <token>` header |
| `--auth-basic user:password` | HTTP Basic authentication |
| `--insecure` | Disable SSL certificate verification |
| `--config path.json` | Load a base configuration (CLI flags override it) |
| `--scenario path.json` | Weighted multi-endpoint targets (see below); takes precedence over `--url` |
| `--warmup` | Seconds of traffic sent before measurements start (excluded from the report) |
| `--save-config path.json` | Save the resulting configuration for reuse |
| `--output report.json` | Export the final report as JSON |
| `--fail-on-error-rate PCT` / `--fail-on-p95 MS` / `--fail-on-p99 MS` / `--fail-on-avg-latency MS` | Exit with status `2` if the finished test breaches a threshold — for CI gating |
| `--yes` / `-y` | Skip the authorization confirmation prompt (automation only) |
| `--log-file` / `--verbose` | Diagnostic logging |
| `--no-color` | Disable ANSI colors (also auto-disabled when not attached to a tty) |

### Multi-Endpoint Scenarios

Real traffic rarely hits one fixed URL. `--scenario scenario.json` points at a
JSON array of weighted request definitions instead of a single `--url`:

```json
[
  {"name": "list-users", "url": "https://api.example.com/users", "method": "GET", "weight": 3},
  {"name": "create-order", "url": "https://api.example.com/orders", "method": "POST", "weight": 1,
   "json_body": {"qty": 1}, "headers": {"X-Test": "1"}}
]
```

Each request during the test picks one entry at random, proportionally to its
`weight` (an entry with `weight: 3` is chosen 3x as often as one with
`weight: 1`). Per-entry `headers`, `json_body`, `raw_body`, `validation_type`,
and `validation_keyword` override the global config for that entry only. The
final report includes a per-endpoint breakdown (requests, successes,
failures) alongside the aggregate statistics.

### Multi-Step Flows (Session-Aware Scenarios)

Real traffic is rarely one isolated request — a user logs in, then acts on
what that returned. A scenario entry can define `steps` instead of a flat
`url`, to run an ordered sequence as a single unit of work:

```json
[
  {
    "name": "login-and-order",
    "weight": 1,
    "steps": [
      {
        "url": "https://api.example.com/login",
        "method": "POST",
        "json_body": {"user": "test"},
        "extract": {"token": "token"}
      },
      {
        "url": "https://api.example.com/orders",
        "method": "POST",
        "headers": {"Authorization": "Bearer {{token}}"},
        "json_body": {"item_id": "{{random_int:1:500}}"}
      }
    ]
  }
]
```

- **`extract`** pulls a value out of the previous step's JSON response body
  using a small dotted/bracket path (`"token"`, `"data.user.id"`,
  `"items[0].id"`) and stores it under the given variable name.
- Later steps reference it with `{{token}}` in the URL, headers, or body.
- **Cookies carry over automatically** between steps in the same flow
  (like a browser session), isolated per flow execution — concurrent
  "virtual users" never see each other's cookies or extracted variables.
- **A step that fails** (non-2xx status, failed validation, or a value that
  couldn't be extracted) **stops the rest of that flow** — a login failure
  means the dependent steps never run, matching how a real client behaves.
- A flat entry (no `steps` key) still works exactly as before — it's treated
  as a one-step flow.
- With multi-step flows, `--rps`/the traffic pattern controls how many new
  flow executions start per second, not raw HTTP requests — a flow with 2
  steps generates roughly 2x as many actual HTTP requests as its start rate.

### Parameterized Request Data

The same `{{...}}` templating used for flow variables also supports built-in
generators, usable in `--body`, `--header`, or any scenario/step field —
including outside multi-step flows, on a plain single-endpoint test:

| Placeholder | Produces |
|-------------|----------|
| `{{uuid}}` | A random UUID4 string |
| `{{random_int}}` | A random integer, 1–1,000,000 |
| `{{random_int:MIN:MAX}}` | A random integer in `[MIN, MAX]` |
| `{{timestamp}}` | The current Unix timestamp |
| `{{counter}}` | A thread-safe, run-wide incrementing integer |

This avoids sending byte-identical repeated requests (which can skew results
via caching) and lets a single endpoint simulate distinct users/records:

```bash
python3 slayer.py --url https://api.example.com/users \
  --method POST --json-body --body '{"external_id": "{{uuid}}", "seq": {{counter}}}' \
  --duration 30 --rps 50 --yes
```

### Warm-Up Period

`--warmup 10` (CLI) or the wizard's "Warm-up period" prompt sends traffic for
that many seconds *before* the measured phase starts, without recording it in
the statistics — useful for letting connection pools, caches, or JIT-warmed
backends reach steady state before you start measuring. Ramp-up tests warm up
at the starting RPS; other patterns warm up at the target RPS.

### CI Gating with Exit Codes

`--fail-on-error-rate`, `--fail-on-p95`, `--fail-on-p99`, and
`--fail-on-avg-latency` let a test act as a pass/fail gate in a pipeline:

```bash
python3 slayer.py --url https://staging.example.com/health \
  --duration 30 --rps 50 --yes \
  --fail-on-error-rate 1 --fail-on-p95 500
```

Exit codes: `0` = test completed and all thresholds passed, `1` = a
configuration/input error prevented the test from running, `2` = the test
ran but breached one or more thresholds. Any thresholds you passed are also
recorded in the exported report under `threshold_failures`.

### Configuration Files

Both modes can save/load configuration as JSON:

- Interactive wizard: choose "Save this configuration to a file" at the end
  of setup, or "Load Configuration From File" from the main menu.
- CLI: `--save-config out.json` writes the config used for a run;
  `--config out.json` loads it back (any CLI flag passed alongside overrides
  the loaded value).

Custom headers, bearer tokens, and Basic Auth credentials are stored in
plaintext in these files since they're needed to replay the test — keep saved
configs out of version control if they contain secrets.

### Exporting Reports

`--output report.json` (CLI) or the "Export this report to a JSON file" prompt
(interactive) writes the final statistics — status code distribution,
latency percentiles, throughput, error breakdown — as JSON for downstream
processing (dashboards, CI gates, historical comparison). Request headers,
auth credentials, and body payloads are intentionally excluded from exported
reports.

### Interactive Mode

```bash
python3 slayer.py
```

The tool will guide you through an interactive menu:

```
======================================================================
SLAYER - HTTP Load Testing Tool
A professional load testing solution
======================================================================

Welcome to SLAYER Load Testing Tool.
Please configure your test to begin.

What would you like to do
  1. Configure New Test
  2. Exit
```

### Configuration Steps

Picking "Configure New Test" walks you through the same options the CLI
flags cover above, in order: target URL, HTTP method, execution engine,
concurrency, duration, warm-up period, traffic pattern (with its
pattern-specific follow-up questions), response validation, request
timeout, custom headers, request body, authentication, and SSL
verification. Every step validates its input before moving on and shows
the allowed range or choices, so it's hard to get stuck.

Once configuration is done, the main menu lets you view or modify it,
run the test, reset it, or exit:

```
What would you like to do
  1. View Configuration
  2. Modify Configuration
  3. Run Test
  4. Reset Configuration
  5. Exit
```

Running the test asks you to confirm you're authorized to load-test the
configured target before it sends a single request.

---

## Understanding Results

### Real-time Report

Every 10 seconds during the test, you will see:

```
[████████░░░░░░░░░░░░░░░░░░░░░░] 30%
Time: 9s / 30s | Requests: 245 | Current RPS: 27

Request Summary
  Total Requests............ 245
  Successful (2xx)......... 243
  Failed (other)........... 2
  Error Rate............... 0.82%

Latency Statistics (ms)
  Minimum.................. 125.45 ms
  Maximum.................. 2340.12 ms
  Average.................. 450.67 ms
  Median (p50)............. 380.23 ms
  95th Percentile (p95).... 1200.34 ms
  99th Percentile (p99).... 2100.45 ms
```

Interpretation:
- Total Requests: Count of HTTP requests made
- Successful: Responses with 2xx status code
- Failed: Errors including 5xx codes, 4xx codes, timeouts, etc.
- Error Rate: Percentage of failed requests
- Latencies: Response times in milliseconds

### Final Report

Upon completion, a comprehensive summary is provided:

```
Test Summary
  Duration.................. 30.0 seconds
  Total Requests............ 812
  Throughput................ 27.06 requests/sec
  Successful Requests....... 799
  Failed Requests........... 13
  Error Rate................ 1.60%

Latency Statistics (ms)
  Minimum.................. 548.75 ms
  Maximum.................. 10470.70 ms
  Average.................. 750.85 ms
  Median (p50)............. 595.75 ms
  95th Percentile (p95).... 1038.38 ms
  99th Percentile (p99).... 4819.31 ms

HTTP Status Codes Distribution
  HTTP 200................. 799 (98.4%)
  HTTP 502................. 7 (0.9%)
  HTTP 0 (Timeout)......... 6 (0.7%)

Error Summary
  Validation Failed.............. 7
  Timeout.............. 6
```

---

## Use Cases

### Basic Load Test

```
URL: https://api.myapp.com/users
Threads: 50
Duration: 60 seconds
RPS: 100
Pattern: Constant
Validation: Check status code
```

### User Growth Simulation

```
URL: https://api.myapp.com/data
Threads: 100
Duration: 300 seconds (5 minutes)
Pattern: Ramp-up
  Starting RPS: 10
  Target RPS: 500
Validation: Validate response content (keyword: "data")
```

### Peak Traffic Testing

```
URL: https://api.myapp.com/orders
Threads: 50
Duration: 120 seconds
Pattern: Spike
  Normal RPS: 50
  Spike RPS: 100
  Spike Duration: 30 seconds
```

### Endurance Testing

```
URL: https://api.myapp.com/reports
Threads: 200
Duration: 1800 seconds (30 minutes)
RPS: 200
Pattern: Constant
Validation: Check status code
```

---

## Metrics Explained

### Latency Metrics

- Minimum: Fastest response time
- Maximum: Slowest response time
- Average: Mean of all response times
- Median (p50): 50 percent of requests were faster than this value
- P95: 95 percent of requests were faster (5 percent were slower)
- P99: 99 percent of requests were faster (1 percent were slower)

What counts as a "good" latency depends entirely on the endpoint you're
testing, so treat these as raw numbers to compare against your own baseline
or SLA rather than a universal scale.

### Throughput

Actual requests per second processed by the server.

```
Throughput = Total Requests / Duration
```

### Error Rate

Percentage of requests that failed.

```
Error Rate = (Failed / Total) * 100
```

Again, an acceptable error rate depends on the service and how it fails
(timeouts vs. clean 4xx/5xx vs. validation mismatches) — check the error
breakdown, not just the percentage.

---

## Troubleshooting

### Connection Refused Error

```
Error: ConnectionError
```

Solution: Verify that the URL is accessible and the server is online

### High Timeout Rate

```
Timeout.............. 50
```

Solutions:
- Increase the timeout value in configuration
- Reduce the number of threads
- Lower the target RPS

### Too Many Requests (429)

```
HTTP 429................. 100
```

Solutions:
- The target server implements rate limiting
- Reduce the RPS value
- Increase the delay between requests

### 502 Bad Gateway

```
HTTP 502................. 15
```

Solutions:
- Backend server is overloaded
- Reduce the number of threads
- Distribute load over a longer duration

---

## Performance Notes

- Requests reuse a pooled, keep-alive `requests.Session` for the whole test
  instead of opening a new TCP/TLS connection per request, so the tool itself
  is far less likely to be the bottleneck at high concurrency.
- Traffic is scheduled in 0.1s sub-intervals rather than dumped once per
  second, which keeps Ramp-up and Spike patterns much closer to their
  intended curve and avoids bursty, uneven request timing.
- If the target RPS exceeds what the configured thread count can sustain, a
  backlog warning is printed during the test, and any requests still queued
  when the test ends are cancelled rather than run to exhaustion — the final
  report shows how many were cancelled.

### Execution Engines: Threads vs. Async

By default SLAYER uses OS threads (`--engine threads`, the default): each
thread blocks on `requests` while waiting for a response. This is simple and
works well up to a few hundred/low thousands of RPS, but every thread carries
real memory and context-switching overhead, which becomes the limiting
factor before most target servers do.

`--engine async` switches to an `aiohttp`-based event loop: a single thread
holds many requests in flight cooperatively, so `--threads` (which becomes
"max concurrent in-flight requests" in this mode, not OS threads) can go much
higher for the same CPU/memory cost. Use it when you need to push
significantly higher RPS than the threads engine sustains on your hardware,
or when profiling shows thread overhead — not connection speed — is capping
your test.

Requires `aiohttp` (`pip install aiohttp`); the tool falls back to a clear
error message (CLI) or a graceful engine fallback (interactive wizard) if
it isn't installed. Behavioral difference to note: at test end, the async
engine cancels *all* outstanding requests — including ones already in
flight — to respect the configured duration exactly, whereas the threads
engine lets already-started requests finish and only cancels queued ones.

## Best Practices

1. Start with small numbers: Begin testing with 10-20 threads before scaling up
2. Review configuration carefully: Double-check all settings before starting
3. Monitor during execution: Observe server response behavior in real-time
4. Analyze patterns: Look for trends in latencies and error rates
5. Iterate and adjust: Modify parameters based on test results
6. Respect rate limits: Always operate within the target service's constraints

---

## Configuration Example

### Manual Configuration

```
URL: https://httpbin.org/get
Method: GET
Threads: 20
Duration: 30 seconds
RPS: 50
Pattern: Constant
Validation: Check status code
Timeout: 10 seconds
```

Expected Result: Approximately 1500 requests over 30 seconds

---

## Reporting Issues

If you encounter a bug or have suggestions:

1. Open an issue on GitHub
2. Provide a detailed description of the problem
3. Include your test configuration
4. Share the results and error messages

---

## License

No license has been chosen for this project yet. Until one is added, all
rights are reserved by the author.

---

For questions or additional support, review the examples above or open an
issue on GitHub.
