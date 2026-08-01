# SLAYER - HTTP Load Testing Tool

SLAYER is a command-line HTTP load testing tool written in Python. It drives
configurable amounts of traffic at a target — a fixed rate, a ramp-up, a
short spike, or a weighted mix of endpoints and multi-step user flows — and
reports back latency percentiles, throughput, and error breakdowns so you
can see how a server behaves under load.

## Features

- Interactive configuration wizard, plus a non-interactive CLI mode for automation and CI
- Three traffic patterns: constant rate, gradual ramp-up, and short spikes
- Response validation: check the status code, or search the response body for a keyword
- Custom headers, JSON/plain-text request bodies, Bearer token and HTTP Basic authentication
- SSL certificate verification toggle for self-signed/internal targets
- Two execution modes: the default, and a higher-throughput mode (`--engine async`) for pushing significantly more requests per second
- Save and load test configurations as JSON, and export the final report as JSON
- Multi-endpoint scenarios: hit several URLs in one test, weighted however you like
- Multi-step flows: log in, carry the resulting token/cookie into the next request, stop early if a step fails
- Parameterized request data (random IDs, timestamps, counters) so repeated requests aren't byte-identical
- Optional warm-up period that isn't counted in the results
- Exit codes tied to pass/fail thresholds, for use as a CI gate
- An explicit authorization confirmation before every test run (see "Responsible Use" below)
- Real-time reports every 10 seconds, including a small trend chart for latency and RPS
- A final report with request counts, status code distribution, and latency percentiles (min, max, average, median, p95, p99)
- Support for GET, POST, PUT, PATCH, and DELETE
- Up to 1000 concurrent connections
- A detailed error breakdown: timeouts, connection failures, and validation failures

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
- The `requests` library
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

There are two ways to run a test: the interactive wizard (just run
`python3 slayer.py` with no arguments) or the non-interactive CLI mode
(pass `--url`, `--scenario`, or `--config`). Both configure and run the
exact same underlying test — pick whichever fits what you're doing.

### Interactive Mode

```bash
python3 slayer.py
```

You'll see a menu:

```
SLAYER

Welcome to SLAYER Load Testing Tool.
Please configure your test to begin.

What would you like to do
  1. Configure New Test
  2. Exit
```

Choosing "Configure New Test" walks you through, in order: the target URL,
HTTP method, execution engine, concurrency, duration, warm-up period,
traffic pattern (with its own follow-up questions), response validation,
request timeout, custom headers, request body, authentication, and SSL
verification. Every step tells you the valid range or choices and won't
let you continue until you enter something valid, so it's hard to get
stuck.

Once configuration is done, the menu changes:

```
What would you like to do
  1. View Configuration
  2. Modify Configuration
  3. Run Test
  4. Reset Configuration
  5. Exit
```

- **View Configuration** shows everything you've set (secrets like tokens
  and passwords are hidden).
- **Modify Configuration** re-runs the wizard so you can change settings.
- **Run Test** asks you to confirm you're authorized to load-test the
  target, then runs it and shows a live report every 10 seconds, followed
  by the final report. You'll also be offered the chance to export that
  report to a JSON file.
- **Reset Configuration** clears everything so you can start over.

At the end of the wizard you're also offered the chance to save your
configuration to a JSON file, so you can reload it later instead of
re-entering everything (see "Configuration Files" below).

### Non-Interactive (CLI) Mode

Passing `--url` (or `--scenario`/`--config`) skips the wizard entirely and
runs a single test straight from command-line flags — this is the mode to
use in scripts, cron jobs, or CI pipelines.

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

Every flag:

| Flag | What it does |
|------|--------------|
| `--url` | The target URL (required, unless you supply `--scenario` or `--config` instead) |
| `--method` | HTTP method: `GET`, `POST`, `PUT`, `PATCH`, or `DELETE` |
| `--threads` | How many requests run at once, from 1 to 1000 |
| `--engine` | `threads` (default) or `async` — see "Which engine should I use?" below |
| `--duration` | How long the test runs, in seconds (1-3600) |
| `--pattern` | Traffic shape: `constant`, `ramp-up`, or `spike` |
| `--rps` | Target requests per second |
| `--start-rps` | Starting RPS for `--pattern ramp-up` |
| `--spike-duration` | How long the spike lasts, for `--pattern spike` |
| `--timeout` | How long to wait for a response before giving up, in seconds |
| `--validation` | `none`, `status` (require a 2xx response), or `content` (require a keyword in the body) |
| `--validation-keyword` | The keyword to look for, with `--validation content` |
| `--header "Key: Value"` | Add a custom header; repeat the flag to add more than one |
| `--body` | The request body to send |
| `--body-file` | Read the request body from a file instead of typing it inline |
| `--json-body` | Send `--body`/`--body-file` as JSON instead of plain text |
| `--auth-bearer` | Adds an `Authorization: Bearer <token>` header for you |
| `--auth-basic user:password` | Use HTTP Basic authentication |
| `--insecure` | Skip SSL certificate verification (for self-signed certs) |
| `--config path.json` | Load settings from a saved configuration file |
| `--scenario path.json` | Test multiple endpoints or multi-step flows instead of one URL — see below |
| `--warmup` | Send traffic for this many seconds before the test starts counting results |
| `--save-config path.json` | Save the settings from this run to a file, to reuse later |
| `--output report.json` | Write the final report to a JSON file |
| `--fail-on-error-rate PCT` | Exit with an error if the error rate goes above `PCT` percent |
| `--fail-on-p95 MS` | Exit with an error if the 95th percentile latency goes above `MS` milliseconds |
| `--fail-on-p99 MS` | Exit with an error if the 99th percentile latency goes above `MS` milliseconds |
| `--fail-on-avg-latency MS` | Exit with an error if the average latency goes above `MS` milliseconds |
| `--yes` / `-y` | Skip the authorization confirmation prompt (use only in automated pipelines) |
| `--log-file` | Write detailed logs to this file |
| `--verbose` | Print detailed logs to the screen as the test runs |
| `--no-color` | Turn off colored output |

#### Which engine should I use?

Leave `--engine` on its default (`threads`) unless you've tried a test and
it's not reaching the RPS you asked for even with the target server
responding fine — that's the sign you need more raw throughput than the
default mode can produce on your machine. In that case, install `aiohttp`
(`pip install aiohttp`) and add `--engine async`. Everything else about the
test (flags, scenario files, reports) works exactly the same either way.
One thing to know: with `--engine async`, `--threads` means "how many
requests can be in flight at once" rather than literal OS threads, and any
requests still running when the test's duration ends are stopped
immediately rather than allowed to finish (the default `threads` mode lets
them finish).

### Testing More Than One Endpoint

Real traffic rarely hits one fixed URL. Instead of `--url`, point
`--scenario` at a JSON file listing several endpoints:

```json
[
  {"name": "list-users", "url": "https://api.example.com/users", "method": "GET", "weight": 3},
  {"name": "create-order", "url": "https://api.example.com/orders", "method": "POST", "weight": 1,
   "json_body": {"qty": 1}, "headers": {"X-Test": "1"}}
]
```

Each request during the test picks one entry at random, in proportion to
its `weight` — here, `list-users` is picked three times as often as
`create-order`. Each entry can have its own `headers`, `json_body`,
`raw_body`, `validation_type`, and `validation_keyword`; anything you don't
set for an entry falls back to the value from your regular flags. The
final report breaks results down per endpoint as well as showing the
combined totals.

```bash
python3 slayer.py --scenario endpoints.json --threads 50 --duration 60 --rps 100 --yes
```

### Multi-Step Flows

Real usage is rarely a single isolated request — someone logs in, then
does something with what that returned. A scenario entry can define
`steps` instead of a flat `url`, to run a sequence of requests together as
one unit:

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

How to read this:

- `"extract": {"token": "token"}` on the first step takes the `token` field
  out of that step's JSON response and remembers it.
- The second step uses `{{token}}` to insert that remembered value into its
  own header. You can use `{{token}}` the same way in a URL or body.
- Cookies set by one step are automatically sent with the next step, so a
  login that sets a session cookie "just works" for the following requests
  — you don't need to configure that yourself.
- If a step fails (a non-2xx response, a failed validation, or a value
  that couldn't be found to extract), the rest of that flow is skipped for
  that run — a failed login means the order request is never attempted.
- A scenario entry without `steps` still works exactly like before; it's
  just treated as a one-step flow.
- One thing worth knowing when you set `--rps`: with multi-step flows, that
  number controls how many *flows* start per second, not how many raw HTTP
  requests are sent. A 2-step flow will produce roughly twice as many
  actual requests as the number you set.

`extract` paths support nesting and array indexes, e.g. `"data.user.id"`
or `"items[0].id"`.

### Parameterized Request Data

You can also insert generated values into `--body`, `--header`, or any
scenario/step field, without needing a multi-step flow:

| Placeholder | Produces |
|-------------|----------|
| `{{uuid}}` | A random unique ID |
| `{{random_int}}` | A random whole number between 1 and 1,000,000 |
| `{{random_int:MIN:MAX}}` | A random whole number between `MIN` and `MAX` |
| `{{timestamp}}` | The current time |
| `{{counter}}` | A number that goes up by one every time it's used |

This is useful any time you don't want to send the exact same request
repeatedly (which can quietly get cached and stop testing what you think
it's testing), or want to simulate distinct users/records:

```bash
python3 slayer.py --url https://api.example.com/users \
  --method POST --json-body --body '{"external_id": "{{uuid}}", "seq": {{counter}}}' \
  --duration 30 --rps 50 --yes
```

### Warming Up Before Measuring

`--warmup 10` (or the wizard's "Warm-up period" question) sends traffic
for that many seconds before the test starts counting anything — useful if
the first few seconds of a test tend to be artificially slow (a cold
cache, a server still starting up its worker processes, etc.) and you
don't want that to skew your results.

```bash
python3 slayer.py --url https://api.example.com/endpoint --warmup 10 --duration 60 --rps 100 --yes
```

### Using Exit Codes in CI

`--fail-on-error-rate`, `--fail-on-p95`, `--fail-on-p99`, and
`--fail-on-avg-latency` let you use a test as a pass/fail gate in a
pipeline, instead of having to read the report yourself:

```bash
python3 slayer.py --url https://staging.example.com/health \
  --duration 30 --rps 50 --yes \
  --fail-on-error-rate 1 --fail-on-p95 500
```

What each exit code means:

- `0` — the test ran and stayed within every threshold you set
- `1` — something was wrong with the setup (bad flags, an invalid URL, a
  missing file) and the test never ran
- `2` — the test ran, but broke one or more of the thresholds you set

If you also pass `--output`, the exported report includes which
thresholds (if any) were broken, under `threshold_failures`.

### Saving and Reusing Configurations

Rather than typing out the same flags every time, you can save a
configuration once and reuse it:

- In the wizard: choose "Save this configuration to a file" at the end of
  setup, and later pick "Load Configuration From File" from the main menu
  to bring it back.
- On the command line: `--save-config out.json` writes down the settings
  used for that run; `--config out.json` loads them back on a later run.
  Any flag you also pass alongside `--config` overrides the saved value
  for just that run.

Custom headers, tokens, and passwords are stored in these files as plain
text, since the tool needs them to replay the test — keep saved
configuration files out of version control if they contain anything
sensitive.

### Exporting the Report

Add `--output report.json` (or answer "Yes" to the export prompt in the
wizard) to write the final report — request counts, status codes, latency
percentiles, error breakdown — out as a JSON file, for feeding into a
dashboard or comparing against previous runs. Headers, credentials, and
request bodies are deliberately left out of the exported file.

## Understanding Results

### The Live Report

Every 10 seconds while the test is running, you'll see something like
this:

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

- **Total Requests**: how many requests have been made so far
- **Successful**: how many got back a 2xx status code
- **Failed**: everything else — 4xx/5xx responses, timeouts, connection
  errors, or a response that failed validation
- **Error Rate**: failed ÷ total, as a percentage
- **Latencies**: how long requests are taking to come back, in
  milliseconds

### The Final Report

When the test ends, you get a full summary:

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

If you asked for more RPS than the test could actually sustain, you'll
also see a "Cancelled (unsent)" line here — it means the target couldn't
be hit as fast as you asked, so some planned requests were dropped instead
of being sent late. If you see this, either lower `--rps` or raise
`--threads` (or switch to `--engine async` — see above).

If you used `--scenario`, you'll also see a per-endpoint breakdown showing
requests, successes, and failures for each entry separately.

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

## Metrics Explained

### Latency

- **Minimum**: the fastest response time seen
- **Maximum**: the slowest response time seen
- **Average**: the mean of all response times
- **Median (p50)**: half of all requests were faster than this
- **P95**: 95% of requests were faster than this (5% were slower)
- **P99**: 99% of requests were faster than this (1% were slower)

What counts as a "good" latency depends entirely on the endpoint you're
testing — compare these numbers against your own baseline or SLA rather
than treating them as universally good or bad.

### Throughput

How many requests per second the target actually handled:

```
Throughput = Total Requests / Duration
```

### Error Rate

```
Error Rate = (Failed / Total) * 100
```

What counts as an acceptable error rate also depends on the service and
how it's failing — check the error breakdown (timeouts vs. clean 4xx/5xx
vs. validation mismatches), not just the percentage.

## Troubleshooting

### Connection Refused

```
Error: ConnectionError
```

Check that the URL is reachable and the target server is actually
running.

### A High Timeout Rate

```
Timeout.............. 50
```

Try increasing `--timeout`, lowering `--threads`, or lowering `--rps`.

### Too Many Requests (429)

```
HTTP 429................. 100
```

The target is rate-limiting you. Lower `--rps` to stay under its limit.

### 502 Bad Gateway

```
HTTP 502................. 15
```

The backend is overloaded. Try lowering `--threads`, or spread the same
number of requests over a longer `--duration`.

### "Cancelled (unsent)" in the Final Report

You asked for more RPS than the test could actually deliver. Lower `--rps`,
raise `--threads`, or switch to `--engine async`.

## Best Practices

1. Start small — begin with 10-20 threads before scaling up
2. Double-check your configuration before starting, especially the target URL
3. Watch the live report while the test runs instead of only checking the end
4. Look for trends in latency and error rate over time, not just the final numbers
5. Adjust one parameter at a time between runs so you know what changed the result
6. Stay within whatever rate limits the target service has told you it can handle

## Configuration Example

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

Expected result: approximately 1500 requests over 30 seconds.
