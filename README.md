# SLAYER - HTTP Load Testing Tool

SLAYER is a professional and efficient HTTP load testing tool. It enables users
to generate massive HTTP requests against web servers to monitor traffic, analyze capacity, and measure performance under load conditions.

## Features

- Interactive configuration wizard with step-by-step guidance
- Multiple traffic patterns: Constant, Ramp-up, and Spike
- Response validation capabilities: HTTP status code verification and response content matching
- Real-time monitoring with reports every 10 seconds during test execution
- Comprehensive statistics including minimum, maximum, average, median, P95, and P99 latencies
- Support for multiple HTTP methods: GET, POST, PUT, DELETE
- Concurrent connection control up to 1000 simultaneous threads
- Detailed error breakdown: timeouts, connection failures, and validation errors
- Comprehensive final report with detailed analysis

## Installation

### Requirements

- Python 3.6 or higher
- The requests library

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

#### Step 1: Configure New Test

Select option 1 from the main menu.

#### Step 2: Enter Target URL

```
Enter target URL: https://api.example.com/endpoint
```

Validation requirements:
- Must include http:// or https://
- Must have a valid domain name

#### Step 3: Select HTTP Method

```
Select HTTP method
  1. GET
  2. POST
  3. PUT
  4. DELETE
```

#### Step 4: Configure Concurrent Threads

```
Number of concurrent threads [50]: 100
```

Range: 1 to 1000
Recommendation: 50-200 for typical tests

#### Step 5: Set Test Duration

```
Test duration in seconds [60]: 120
```

Range: 1 to 3600 seconds

#### Step 6: Choose Traffic Pattern

```
Select traffic pattern
  1. Constant
  2. Ramp-up
  3. Spike
```

Constant Pattern: Fixed requests per second for the entire test duration
```
Target requests per second (RPS) [100]: 100
```

Ramp-up Pattern: Gradually increases requests per second
```
Target requests per second (RPS) [100]: 100
Starting RPS [10]: 20
```

Spike Pattern: Creates traffic peaks during the test
```
Target requests per second (RPS) [100]: 100
Spike duration in seconds [10]: 15
```

#### Step 7: Enable Response Validation

```
Enable response validation
  1. No
  2. Check status code
  3. Validate response content
```

No: Accepts any response

Check status code: Validates that response status is 2xx (200-299)

Validate response content: Searches for a specific keyword in the response body
```
Enter keyword to search in response: success
```

#### Step 8: Set Request Timeout

```
Request timeout in seconds [10]: 15
```

Range: 1 to 60 seconds

#### Step 9: Execute Test

From the main menu:
```
What would you like to do
  1. View Configuration
  2. Modify Configuration
  3. Run Test
  4. Reset Configuration
  5. Exit
```

Select option 3: Run Test

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

General Performance Guidelines:
- Average < 200ms: Excellent
- Average 200-500ms: Good
- Average 500-1000ms: Acceptable
- Average > 1000ms: Performance concerns

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

Acceptable Ranges:
- < 0.1%: Excellent
- 0.1% - 1%: Good
- 1% - 5%: Acceptable
- > 5%: Performance issues detected

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

This project is open source. Feel free to use it freely.

---

## Author

SLAYER Load Testing Tool - Professional HTTP load testing solution

---

## References

- HTTP Status Codes Documentation: https://httpwg.org/specs/rfc7231.html#status.codes
- Percentile Metrics in Load Testing: https://en.wikipedia.org/wiki/Percentile
- Load Testing Best Practices: https://en.wikipedia.org/wiki/Load_testing

---

For questions or additional support, review the examples section or open an issue on GitHub.
