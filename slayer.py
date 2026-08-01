#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLAYER - HTTP Load Testing Tool
A professional, simple, and effective load testing solution.
"""

import argparse
import asyncio
import json
import logging
import random
import re
import signal
import sys
import threading
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from statistics import mean, median
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter

try:
    import aiohttp
except ImportError:
    aiohttp = None

logger = logging.getLogger("slayer")

SENSITIVE_KEY_HINTS = ("token", "secret", "password", "key", "authorization")
SPARK_CHARS = "▁▂▃▄▅▆▇█"


class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'

    @classmethod
    def disable(cls):
        """Strip ANSI codes (non-tty output, --no-color, or piped logs)."""
        for name in ('RESET', 'BOLD', 'DIM', 'RED', 'GREEN', 'YELLOW', 'BLUE', 'CYAN', 'WHITE'):
            setattr(cls, name, '')


class ProgressBar:
    """Display a text-based progress bar."""

    def __init__(self, total_seconds, width=50):
        self.total_seconds = max(total_seconds, 1)
        self.width = width

    def render(self, current_second):
        """Render progress bar with percentage."""
        percent = min(100, int((current_second / self.total_seconds) * 100))
        filled = int((percent / 100) * self.width)
        bar = '█' * filled + '░' * (self.width - filled)
        return f"[{bar}] {percent}%"


class Statistics:
    """Collect and analyze load test statistics."""

    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.cancelled_requests = 0
        self.status_codes = defaultdict(int)
        self.response_times = []
        self.errors = defaultdict(int)
        self.per_target = defaultdict(lambda: {'total': 0, 'successful': 0, 'failed': 0})
        self.start_time = None
        self.end_time = None
        self.lock = threading.Lock()

    def record_request(self, status_code, response_time, error=None, validation_failed=False, label=None):
        """Record a single request result."""
        with self.lock:
            self.total_requests += 1
            self.response_times.append(response_time)
            self.status_codes[status_code] += 1

            successful = 200 <= status_code < 300
            if successful:
                self.successful_requests += 1
            else:
                self.failed_requests += 1

            if label:
                target = self.per_target[label]
                target['total'] += 1
                target['successful' if successful else 'failed'] += 1

            if validation_failed:
                self.errors['validation_failed'] += 1
            elif error:
                self.errors[error] += 1

    def get_statistics(self):
        """Return current statistics summary."""
        if not self.response_times:
            return None

        latencies = sorted(self.response_times)
        n = len(latencies)

        return {
            'total': self.total_requests,
            'successful': self.successful_requests,
            'failed': self.failed_requests,
            'error_rate': (self.failed_requests / self.total_requests * 100) if self.total_requests > 0 else 0,
            'min_latency': min(latencies),
            'max_latency': max(latencies),
            'avg_latency': mean(latencies),
            'median_latency': median(latencies),
            'p95_latency': latencies[min(n - 1, int(n * 0.95))],
            'p99_latency': latencies[min(n - 1, int(n * 0.99))],
            'status_codes': dict(self.status_codes),
            'errors': dict(self.errors),
            'per_target': {k: dict(v) for k, v in self.per_target.items()},
        }


def parse_header(text):
    """Parse a 'Key: Value' header line. Raises ValueError on bad format."""
    if ':' not in text:
        raise ValueError(f"Formato de header invalido (usa 'Clave: Valor'): {text}")
    key, value = text.split(':', 1)
    key, value = key.strip(), value.strip()
    if not key:
        raise ValueError(f"Nombre de header vacio: {text}")
    return key, value


def mask_headers(headers):
    """Return a copy of headers with sensitive values redacted for display."""
    masked = {}
    for key, value in (headers or {}).items():
        if any(hint in key.lower() for hint in SENSITIVE_KEY_HINTS):
            masked[key] = '***'
        else:
            masked[key] = value
    return masked


def is_valid_url(url):
    """Validate that a URL has an http(s) scheme and a network location."""
    if not url:
        return False
    try:
        result = urlparse(url)
        return all([result.scheme in ('http', 'https'), result.netloc])
    except ValueError:
        return False


def sparkline(values):
    """Render a compact Unicode trend line for a series of numbers."""
    if not values:
        return ""
    lo, hi = min(values), max(values)
    span = hi - lo
    if span == 0:
        return SPARK_CHARS[0] * len(values)
    return "".join(
        SPARK_CHARS[int((v - lo) / span * (len(SPARK_CHARS) - 1))]
        for v in values
    )


def describe_targets(config):
    """Human-readable summary of what a config will hit, for prompts/display."""
    scenario = config.get('scenario')
    if scenario:
        def entry_url(entry):
            if 'steps' in entry:
                steps = entry['steps']
                first_url = steps[0].get('url', '?') if steps else '?'
                return f"{first_url} (+{len(steps) - 1} more steps)" if len(steps) > 1 else first_url
            return entry.get('url', '?')

        urls = [entry_url(entry) for entry in scenario]
        preview = ", ".join(urls[:3])
        more = f" (+{len(urls) - 3} more)" if len(urls) > 3 else ""
        return f"{len(urls)} endpoint(s): {preview}{more}"
    return config.get('url', '(no target configured)')


_STEP_FIELDS = ('url', 'method', 'headers', 'json_body', 'raw_body', 'validation_type', 'validation_keyword', 'extract')


def normalize_flow_entry(entry):
    """Wrap a legacy flat scenario entry into a single-step flow; pass multi-step flows through."""
    if 'steps' in entry:
        return {'name': entry.get('name'), 'weight': entry.get('weight', 1), 'steps': entry['steps']}
    step = {k: entry[k] for k in _STEP_FIELDS if k in entry}
    return {'name': entry.get('name'), 'weight': entry.get('weight', 1), 'steps': [step]}


class _AtomicCounter:
    """Thread-safe incrementing counter, shared by the {{counter}} template token."""

    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()

    def next(self):
        with self._lock:
            self._value += 1
            return self._value


_TEMPLATE_COUNTER = _AtomicCounter()
_TEMPLATE_RE = re.compile(r'\{\{(\w+)(?::(-?\d+):(-?\d+))?\}\}')


def render_template(value, variables):
    """Substitute {{name}} placeholders: flow-extracted variables first, then built-in generators."""
    if isinstance(value, str):
        def replace(match):
            name, min_s, max_s = match.group(1), match.group(2), match.group(3)
            if name in variables:
                return str(variables[name])
            if name == 'uuid':
                return str(uuid.uuid4())
            if name == 'random_int':
                lo = int(min_s) if min_s is not None else 1
                hi = int(max_s) if max_s is not None else 1_000_000
                return str(random.randint(lo, hi))
            if name == 'timestamp':
                return str(int(time.time()))
            if name == 'counter':
                return str(_TEMPLATE_COUNTER.next())
            return match.group(0)
        return _TEMPLATE_RE.sub(replace, value)
    if isinstance(value, dict):
        return {k: render_template(v, variables) for k, v in value.items()}
    if isinstance(value, list):
        return [render_template(v, variables) for v in value]
    return value


_PATH_TOKEN_RE = re.compile(r'[^.\[\]]+|\[\d+\]')


def extract_json_path(data, path):
    """Pull a value out of parsed JSON with a small dotted/bracket path, e.g. 'data.items[0].token'."""
    path = path.strip()
    if path.startswith('$'):
        path = path[1:]
    path = path.lstrip('.')
    current = data
    for token in _PATH_TOKEN_RE.findall(path):
        if token.startswith('['):
            current = current[int(token[1:-1])]
        else:
            current = current[token]
    return current


class LoadTester:
    """Main load testing engine."""

    def __init__(self):
        self.config = {}
        self.statistics = Statistics()
        self.running = False
        self.session = None
        self.executor = None
        self.submitted = 0
        self._scenario_targets = None
        self._scenario_cum_weights = None
        self._scenario_total_weight = 0
        self._latency_history = []
        self._rps_history = []

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def print_header(self):
        """Display the tool banner."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}SLAYER{Colors.RESET}\n")

    def print_separator(self, char="─", length=70):
        """Print a visual separator."""
        print(Colors.DIM + char * length + Colors.RESET)

    def clear_screen(self):
        """Clear terminal screen (only when attached to an interactive tty)."""
        if sys.stdout.isatty():
            print("\033c", end="")

    def prompt(self, message, default=None, options=None):
        """Display a prompt and get user input."""
        if options:
            print(f"\n{Colors.CYAN}{message}{Colors.RESET}")
            for i, option in enumerate(options, 1):
                print(f"  {i}. {option}")
            while True:
                choice = input(f"\nSelect option (1-{len(options)}): ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(options):
                    return options[int(choice) - 1]
                print(f"{Colors.RED}Invalid selection. Please try again.{Colors.RESET}")
        else:
            if default:
                prompt_text = f"{Colors.CYAN}{message} [{default}]: {Colors.RESET}"
            else:
                prompt_text = f"{Colors.CYAN}{message}: {Colors.RESET}"
            response = input(prompt_text).strip()
            return response if response else default

    def validate_url(self, url):
        """Validate if URL is properly formatted."""
        return is_valid_url(url)

    # ------------------------------------------------------------------
    # Interactive configuration wizard
    # ------------------------------------------------------------------

    def configure_test(self):
        """Interactive configuration wizard."""
        self.clear_screen()
        self.print_header()
        print("Test Configuration")
        self.print_separator()

        while True:
            url = self.prompt("Enter target URL")
            if self.validate_url(url):
                self.config['url'] = url
                break
            print(f"{Colors.RED}Invalid URL format. Please try again.{Colors.RESET}")

        method = self.prompt(
            "Select HTTP method",
            default="GET",
            options=["GET", "POST", "PUT", "PATCH", "DELETE"]
        )
        self.config['method'] = method

        engine_options = ["Threads (default)"]
        if aiohttp is not None:
            engine_options.append("Async / aiohttp (higher RPS ceiling)")
        else:
            engine_options.append("Async / aiohttp (not installed - pip install aiohttp)")
        engine_choice = self.prompt("Select execution engine", default=engine_options[0], options=engine_options)
        if engine_choice.startswith("Async") and aiohttp is None:
            print(f"{Colors.RED}aiohttp is not installed; falling back to the threads engine.{Colors.RESET}")
            self.config['engine'] = 'threads'
        else:
            self.config['engine'] = 'async' if engine_choice.startswith("Async") else 'threads'

        concurrency_label = (
            "Number of concurrent threads" if self.config['engine'] == 'threads'
            else "Max concurrent in-flight requests"
        )
        while True:
            threads = self.prompt(concurrency_label, default="50")
            if threads.isdigit() and 1 <= int(threads) <= 1000:
                self.config['threads'] = int(threads)
                break
            print(f"{Colors.RED}Please enter a number between 1 and 1000.{Colors.RESET}")

        while True:
            duration = self.prompt("Test duration in seconds", default="60")
            if duration.isdigit() and 1 <= int(duration) <= 3600:
                self.config['duration'] = int(duration)
                break
            print(f"{Colors.RED}Please enter a number between 1 and 3600.{Colors.RESET}")

        while True:
            warmup = self.prompt(
                "Warm-up period in seconds (traffic sent but excluded from results)",
                default="0"
            )
            if warmup.isdigit() and 0 <= int(warmup) <= 3600:
                self.config['warmup'] = int(warmup)
                break
            print(f"{Colors.RED}Please enter a number between 0 and 3600.{Colors.RESET}")

        pattern = self.prompt(
            "Select traffic pattern",
            default="Constant",
            options=["Constant", "Ramp-up", "Spike"]
        )
        self.config['pattern'] = pattern

        while True:
            rps = self.prompt("Target requests per second (RPS)", default="100")
            if rps.isdigit() and 1 <= int(rps) <= 100000:
                self.config['target_rps'] = int(rps)
                break
            print(f"{Colors.RED}Please enter a number between 1 and 100000.{Colors.RESET}")

        if pattern == "Ramp-up":
            while True:
                start_rps = self.prompt("Starting RPS", default="10")
                if start_rps.isdigit() and 1 <= int(start_rps) <= int(self.config['target_rps']):
                    self.config['start_rps'] = int(start_rps)
                    break
                print(f"{Colors.RED}Starting RPS must be less than target RPS.{Colors.RESET}")

        elif pattern == "Spike":
            while True:
                spike_duration = self.prompt("Spike duration in seconds", default="10")
                if spike_duration.isdigit() and 1 <= int(spike_duration) < self.config['duration']:
                    self.config['spike_duration'] = int(spike_duration)
                    break
                print(f"{Colors.RED}Spike duration must be less than test duration.{Colors.RESET}")

        validation = self.prompt(
            "Enable response validation",
            options=["No", "Check status code", "Validate response content"]
        )

        if validation != "No":
            self.config['validation_enabled'] = True
            self.config['validation_type'] = validation
            if validation == "Validate response content":
                keyword = self.prompt("Enter keyword to search in response")
                self.config['validation_keyword'] = keyword
        else:
            self.config['validation_enabled'] = False

        while True:
            timeout = self.prompt("Request timeout in seconds", default="10")
            if timeout.isdigit() and 1 <= int(timeout) <= 60:
                self.config['timeout'] = int(timeout)
                break
            print(f"{Colors.RED}Please enter a number between 1 and 60.{Colors.RESET}")

        headers = {}
        if self.prompt("Add custom headers", options=["No", "Yes"]) == "Yes":
            print(f"{Colors.DIM}Enter one 'Key: Value' header per line. Empty line to finish.{Colors.RESET}")
            while True:
                line = input("Header: ").strip()
                if not line:
                    break
                try:
                    key, value = parse_header(line)
                    headers[key] = value
                except ValueError as e:
                    print(f"{Colors.RED}{e}{Colors.RESET}")

        if method in ("POST", "PUT", "PATCH"):
            body_choice = self.prompt(
                "Send a request body",
                options=["No", "JSON", "Plain text"]
            )
            if body_choice == "JSON":
                raw = self.prompt("Enter JSON body", default="{}")
                try:
                    self.config['json_body'] = json.loads(raw) if raw else {}
                except json.JSONDecodeError as e:
                    print(f"{Colors.RED}Invalid JSON ({e}). Sending without a body.{Colors.RESET}")
            elif body_choice == "Plain text":
                self.config['raw_body'] = self.prompt("Enter body text", default="")

        auth_choice = self.prompt(
            "Authentication",
            options=["No", "Bearer token", "Basic auth"]
        )
        if auth_choice == "Bearer token":
            token = self.prompt("Enter token")
            if token:
                headers['Authorization'] = f"Bearer {token}"
        elif auth_choice == "Basic auth":
            user = self.prompt("Username")
            password = self.prompt("Password")
            self.config['basic_auth'] = (user or "", password or "")

        self.config['headers'] = headers

        if urlparse(self.config['url']).scheme == 'https':
            verify = self.prompt("Verify SSL certificate", options=["Yes", "No"])
            self.config['verify_ssl'] = (verify == "Yes")
        else:
            self.config['verify_ssl'] = True

        if self.prompt("Save this configuration to a file", options=["No", "Yes"]) == "Yes":
            path = self.prompt("File path", default="slayer_config.json")
            self.save_config(path)

    def save_config(self, path):
        """Persist the current configuration as JSON."""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"{Colors.GREEN}Configuration saved to {path}{Colors.RESET}")
        except OSError as e:
            print(f"{Colors.RED}Could not save configuration: {e}{Colors.RESET}")

    def load_config(self, path):
        """Load configuration from a JSON file previously saved with save_config."""
        with open(path, encoding='utf-8') as f:
            self.config = json.load(f)
        if isinstance(self.config.get('basic_auth'), list):
            self.config['basic_auth'] = tuple(self.config['basic_auth'])

    def display_configuration(self):
        """Show current test configuration (secrets redacted)."""
        self.clear_screen()
        self.print_header()
        print("Current Configuration")
        self.print_separator()

        for key, value in self.config.items():
            if key == 'headers':
                value = mask_headers(value)
            elif key == 'basic_auth' and value:
                value = (value[0], '***')
            elif key == 'scenario':
                value = [self._masked_scenario_entry(entry) for entry in value]
            formatted_key = key.replace('_', ' ').title()
            print(f"  {formatted_key:.<40} {Colors.BLUE}{value}{Colors.RESET}")

        self.print_separator()
        print("\n")

    @staticmethod
    def _masked_scenario_entry(entry):
        """Redact secrets from a scenario entry (flat or multi-step) for display."""
        if 'steps' in entry:
            return {
                **entry,
                'steps': [
                    {**step, 'headers': mask_headers(step.get('headers'))} if step.get('headers') else step
                    for step in entry['steps']
                ],
            }
        return {**entry, 'headers': mask_headers(entry.get('headers'))} if entry.get('headers') else entry

    # ------------------------------------------------------------------
    # Traffic pattern / request execution
    # ------------------------------------------------------------------

    def calculate_rps_for_second(self, current_second):
        """Calculate RPS for current second based on traffic pattern."""
        pattern = self.config.get('pattern', 'Constant')
        target_rps = self.config['target_rps']
        duration = self.config['duration']

        if pattern == "Constant":
            return target_rps

        elif pattern == "Ramp-up":
            start_rps = self.config.get('start_rps', 10)
            rps_increase = (target_rps - start_rps) / duration
            return start_rps + (rps_increase * current_second)

        elif pattern == "Spike":
            spike_duration = self.config.get('spike_duration', 10)
            if current_second < spike_duration:
                return target_rps * 2
            else:
                return target_rps

        return target_rps

    @staticmethod
    def _content_matches(body_text, keyword):
        if not keyword:
            return True
        return keyword.lower() in (body_text or '').lower()

    def validate_response(self, response, validation_type=None, validation_keyword=None):
        """Validate a `requests` response based on configuration (or per-target overrides)."""
        if not self.config.get('validation_enabled', False):
            return True

        validation_type = validation_type or self.config.get('validation_type')

        if validation_type == "Check status code":
            return 200 <= response.status_code < 300

        elif validation_type == "Validate response content":
            keyword = validation_keyword if validation_keyword is not None else self.config.get('validation_keyword', '')
            try:
                return self._content_matches(response.text, keyword)
            except (UnicodeDecodeError, ValueError):
                return False

        return True

    def validate_async_response(self, status_code, body_text, validation_type=None, validation_keyword=None):
        """Validate an aiohttp response (status_code + already-read body text)."""
        if not self.config.get('validation_enabled', False):
            return True

        validation_type = validation_type or self.config.get('validation_type')

        if validation_type == "Check status code":
            return 200 <= status_code < 300

        elif validation_type == "Validate response content":
            keyword = validation_keyword if validation_keyword is not None else self.config.get('validation_keyword', '')
            return self._content_matches(body_text, keyword)

        return True

    def _build_session(self, pool_size):
        """Build a shared, connection-pooled session for the whole test."""
        session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=max(pool_size, 10),
            pool_maxsize=max(pool_size, 10),
            max_retries=0,
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def _prepare_scenario(self):
        """Precompute weighted-selection data for multi-endpoint / multi-step scenarios."""
        scenario = self.config.get('scenario')
        if not scenario:
            self._scenario_targets = None
            return

        normalized = [normalize_flow_entry(entry) for entry in scenario]
        weights = [max(entry.get('weight', 1), 0) for entry in normalized]
        total_weight = sum(weights)
        if total_weight <= 0:
            raise ValueError("Scenario weights must sum to a positive number")

        self._scenario_targets = normalized
        self._scenario_total_weight = total_weight
        cumulative = []
        acc = 0
        for weight in weights:
            acc += weight
            cumulative.append(acc)
        self._scenario_cum_weights = cumulative

    def _pick_scenario_target(self):
        """Pick one scenario flow using weighted random selection."""
        r = random.uniform(0, self._scenario_total_weight)
        for entry, cum in zip(self._scenario_targets, self._scenario_cum_weights):
            if r <= cum:
                return entry
        return self._scenario_targets[-1]

    def _get_flow(self):
        """Return (flow_name_or_None, steps) — the unit of work for one submission."""
        if self._scenario_targets:
            target = self._pick_scenario_target()
            return target.get('name'), target['steps']
        cfg = self.config
        step = {
            'url': cfg['url'],
            'method': cfg['method'],
            'headers': cfg.get('headers'),
            'json_body': cfg.get('json_body'),
            'raw_body': cfg.get('raw_body'),
            'validation_type': cfg.get('validation_type'),
            'validation_keyword': cfg.get('validation_keyword'),
        }
        return None, [step]

    @staticmethod
    def _step_label(flow_name, index, n_steps, method, url):
        if n_steps == 1:
            return flow_name or f"{method} {url}"
        return f"{flow_name or 'flow'} [step {index + 1}/{n_steps}]"

    def _apply_extract(self, extract_map, body_text, variables, label):
        """Pull values out of a step's JSON response body into `variables` for later steps."""
        if not extract_map:
            return True
        try:
            parsed = json.loads(body_text)
        except (ValueError, TypeError) as e:
            logger.debug("Extract failed for %s: response body is not JSON (%s)", label, e)
            return False
        try:
            for var_name, path in extract_map.items():
                variables[var_name] = extract_json_path(parsed, path)
            return True
        except (KeyError, IndexError, TypeError) as e:
            logger.debug("Extract failed for %s: %s", label, e)
            return False

    def _render_step_fields(self, step, variables):
        """Render templates for one step's fields against the flow's accumulated variables."""
        headers = render_template({**(self.config.get('headers') or {}), **(step.get('headers') or {})}, variables)
        url = render_template(step['url'], variables)
        method = str(step.get('method', self.config['method'])).upper()
        json_body = render_template(step['json_body'], variables) if step.get('json_body') is not None else None
        raw_body = render_template(step['raw_body'], variables) if step.get('raw_body') is not None else None
        validation_type = step.get('validation_type', self.config.get('validation_type'))
        keyword_raw = step.get('validation_keyword', self.config.get('validation_keyword'))
        validation_keyword = render_template(keyword_raw, variables) if keyword_raw else keyword_raw
        return url, method, headers, json_body, raw_body, validation_type, validation_keyword

    def _send_request(self, record=True):
        """Execute one unit of work: a single request, or a multi-step flow, in sequence."""
        flow_name, steps = self._get_flow()
        variables = {}
        cookies = {}
        for index, step in enumerate(steps):
            keep_going = self._send_step_sync(step, variables, cookies, index, flow_name, len(steps), record)
            if not keep_going:
                break

    def _send_step_sync(self, step, variables, cookies, index, flow_name, n_steps, record):
        """Perform one flow step over `requests` and, if record=True, log the outcome.

        Returns whether the flow should continue to its next step.
        """
        url, method, headers, json_body, raw_body, validation_type, validation_keyword = (
            self._render_step_fields(step, variables)
        )
        label = self._step_label(flow_name, index, n_steps, method, url)
        start_time = time.monotonic()
        try:
            kwargs = {
                'headers': headers or None,
                'timeout': self.config['timeout'],
                'verify': self.config.get('verify_ssl', True),
                'cookies': cookies or None,
            }
            if self.config.get('basic_auth'):
                kwargs['auth'] = tuple(self.config['basic_auth'])
            if json_body is not None:
                kwargs['json'] = json_body
            elif raw_body is not None:
                kwargs['data'] = raw_body

            response = self.session.request(method, url, **kwargs)
            response_time = (time.monotonic() - start_time) * 1000
            # Only this response's own cookies are read (never the shared session jar), so
            # concurrent flow executions never contaminate each other's cookie state.
            cookies.update(response.cookies.get_dict())

            extract_ok = self._apply_extract(step.get('extract'), response.text, variables, label)
            validation_ok = self.validate_response(response, validation_type, validation_keyword)

            if record:
                self.statistics.record_request(
                    response.status_code, response_time, validation_failed=not validation_ok, label=label
                )
            return extract_ok and validation_ok and 200 <= response.status_code < 300

        except requests.exceptions.Timeout:
            if record:
                self.statistics.record_request(
                    0, (time.monotonic() - start_time) * 1000, error="timeout", label=label
                )
            return False
        except requests.exceptions.ConnectionError:
            if record:
                self.statistics.record_request(
                    0, (time.monotonic() - start_time) * 1000, error="connection_error", label=label
                )
            return False
        except requests.exceptions.RequestException as e:
            logger.debug("Request error: %s", e)
            if record:
                self.statistics.record_request(
                    0, (time.monotonic() - start_time) * 1000, error=type(e).__name__, label=label
                )
            return False

    def _handle_sigterm(self, signum, frame):
        raise KeyboardInterrupt()

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def _print_latency_block(self, stats):
        print(f"\n{Colors.BOLD}Latency Statistics (ms){Colors.RESET}")
        print(f"  Minimum.................. {stats['min_latency']:.2f} ms")
        print(f"  Maximum.................. {stats['max_latency']:.2f} ms")
        print(f"  Average.................. {stats['avg_latency']:.2f} ms")
        print(f"  Median (p50)............. {stats['median_latency']:.2f} ms")
        print(f"  95th Percentile (p95).... {stats['p95_latency']:.2f} ms")
        print(f"  99th Percentile (p99).... {stats['p99_latency']:.2f} ms")

    def _print_status_codes_block(self, stats, title="HTTP Status Codes"):
        if not stats['status_codes']:
            return
        print(f"\n{Colors.BOLD}{title}{Colors.RESET}")
        for code in sorted(stats['status_codes'].keys()):
            count = stats['status_codes'][code]
            percentage = (count / stats['total']) * 100
            color = Colors.GREEN if 200 <= code < 300 else Colors.RED
            print(f"  {code}........................ {color}{count}{Colors.RESET} ({percentage:.1f}%)")

    def _print_errors_block(self, stats, title="Error Details"):
        if not stats['errors']:
            return
        print(f"\n{Colors.BOLD}{title}{Colors.RESET}")
        for error_type, count in stats['errors'].items():
            label = error_type.replace('_', ' ').title()
            print(f"  {label}.............. {Colors.RED}{count}{Colors.RESET}")

    def _print_per_target_block(self, stats):
        per_target = stats.get('per_target')
        if not per_target:
            return
        print(f"\n{Colors.BOLD}Per-Endpoint Breakdown{Colors.RESET}")
        for label in sorted(per_target.keys()):
            t = per_target[label]
            rate = (t['successful'] / t['total'] * 100) if t['total'] else 0
            print(f"  {label}")
            print(
                f"      Requests: {t['total']}  "
                f"Successful: {Colors.GREEN}{t['successful']}{Colors.RESET}  "
                f"Failed: {Colors.RED}{t['failed']}{Colors.RESET}  ({rate:.1f}% ok)"
            )

    def print_report(self, elapsed_seconds):
        """Print current test report."""
        stats = self.statistics.get_statistics()
        if not stats:
            return

        current_rps = stats['total'] / max(elapsed_seconds, 1)
        self._latency_history.append(stats['avg_latency'])
        self._rps_history.append(current_rps)

        progress_bar = ProgressBar(self.config['duration'])
        print(f"\n{progress_bar.render(elapsed_seconds)}")
        print(f"Time: {elapsed_seconds}s / {self.config['duration']}s | ", end="")
        print(f"Requests: {stats['total']} | ", end="")
        print(f"Current RPS: {int(current_rps)}")

        if len(self._latency_history) > 1:
            print(
                f"Latency trend: {sparkline(self._latency_history)}  "
                f"RPS trend: {sparkline(self._rps_history)}"
            )

        self.print_separator()

        print(f"\n{Colors.BOLD}Request Summary{Colors.RESET}")
        print(f"  Total Requests............ {Colors.BLUE}{stats['total']}{Colors.RESET}")
        print(f"  Successful (2xx)......... {Colors.GREEN}{stats['successful']}{Colors.RESET}")
        print(f"  Failed (other)........... {Colors.RED}{stats['failed']}{Colors.RESET}")
        print(f"  Error Rate............... {Colors.YELLOW}{stats['error_rate']:.2f}%{Colors.RESET}")

        self._print_latency_block(stats)
        self._print_status_codes_block(stats)
        self._print_errors_block(stats)

        self.print_separator()

    def _run_phase_threads(self, duration, rps_func, record, report):
        """Run one traffic phase (warm-up or measured) for `duration` seconds, thread engine."""
        tick_interval = 0.1
        ticks_per_second = round(1 / tick_interval)
        total_ticks = duration * ticks_per_second
        scheduled = 0.0
        submitted = 0
        backlog_warned = False
        concurrency = self.config['threads']
        start_mono = time.monotonic()

        for tick in range(total_ticks):
            if not self.running:
                break

            current_second = tick // ticks_per_second
            rps = rps_func(current_second)
            scheduled += rps * tick_interval
            to_submit = int(scheduled) - submitted

            for _ in range(to_submit):
                self.executor.submit(self._send_request, record)
            submitted += to_submit
            if record:
                self.submitted += to_submit

            if record:
                pending = self.submitted - self.statistics.total_requests
                if pending > concurrency * 20 and not backlog_warned:
                    print(
                        f"\n{Colors.YELLOW}Warning: request backlog is growing "
                        f"(target RPS may exceed what {concurrency} threads can sustain).{Colors.RESET}"
                    )
                    backlog_warned = True

            if report and tick % ticks_per_second == 0 and (current_second == 0 or current_second % 10 == 0):
                self.print_report(current_second)

            next_tick_time = start_mono + (tick + 1) * tick_interval
            sleep_for = next_tick_time - time.monotonic()
            if sleep_for > 0:
                time.sleep(sleep_for)

    async def _send_request_async(self, session, record=True):
        """Async counterpart of _send_request: execute one unit of work (request or flow)."""
        flow_name, steps = self._get_flow()
        variables = {}
        cookies = {}
        for index, step in enumerate(steps):
            keep_going = await self._send_step_async(
                session, step, variables, cookies, index, flow_name, len(steps), record
            )
            if not keep_going:
                break

    async def _send_step_async(self, session, step, variables, cookies, index, flow_name, n_steps, record):
        """Perform one flow step over aiohttp. Returns whether the flow should continue."""
        url, method, headers, json_body, raw_body, validation_type, validation_keyword = (
            self._render_step_fields(step, variables)
        )
        label = self._step_label(flow_name, index, n_steps, method, url)
        start_time = time.monotonic()
        try:
            kwargs = {'ssl': self.config.get('verify_ssl', True)}
            if headers:
                kwargs['headers'] = headers
            if cookies:
                kwargs['cookies'] = cookies
            if json_body is not None:
                kwargs['json'] = json_body
            elif raw_body is not None:
                kwargs['data'] = raw_body
            if self.config.get('basic_auth'):
                user, password = self.config['basic_auth']
                kwargs['auth'] = aiohttp.BasicAuth(user, password)

            async with session.request(method, url, **kwargs) as response:
                extract_map = step.get('extract')
                wants_content_check = (
                    validation_type or self.config.get('validation_type')
                ) == "Validate response content"
                needs_body = bool(extract_map) or (self.config.get('validation_enabled', False) and wants_content_check)
                body_text = await response.text() if needs_body else None

                for key, morsel in response.cookies.items():
                    cookies[key] = morsel.value

                response_time = (time.monotonic() - start_time) * 1000

                extract_ok = self._apply_extract(extract_map, body_text, variables, label) if extract_map else True
                validation_ok = self.validate_async_response(
                    response.status, body_text, validation_type, validation_keyword
                )

                if record:
                    self.statistics.record_request(
                        response.status, response_time, validation_failed=not validation_ok, label=label
                    )
                return extract_ok and validation_ok and 200 <= response.status < 300

        except asyncio.TimeoutError:
            if record:
                self.statistics.record_request(
                    0, (time.monotonic() - start_time) * 1000, error="timeout", label=label
                )
            return False
        except aiohttp.ClientConnectionError:
            if record:
                self.statistics.record_request(
                    0, (time.monotonic() - start_time) * 1000, error="connection_error", label=label
                )
            return False
        except aiohttp.ClientError as e:
            logger.debug("Async request error: %s", e)
            if record:
                self.statistics.record_request(
                    0, (time.monotonic() - start_time) * 1000, error=type(e).__name__, label=label
                )
            return False

    async def _run_phase_async(self, duration, rps_func, record, report, session, semaphore):
        """Run one traffic phase for `duration` seconds using the async engine."""
        tick_interval = 0.1
        ticks_per_second = round(1 / tick_interval)
        total_ticks = duration * ticks_per_second
        scheduled = 0.0
        submitted = 0
        backlog_warned = False
        concurrency = self.config['threads']
        start_mono = time.monotonic()
        pending_tasks = set()

        async def bounded_send():
            async with semaphore:
                await self._send_request_async(session, record)

        for tick in range(total_ticks):
            if not self.running:
                break

            current_second = tick // ticks_per_second
            rps = rps_func(current_second)
            scheduled += rps * tick_interval
            to_submit = int(scheduled) - submitted

            for _ in range(to_submit):
                task = asyncio.ensure_future(bounded_send())
                pending_tasks.add(task)
                task.add_done_callback(pending_tasks.discard)
            submitted += to_submit
            if record:
                self.submitted += to_submit

            if record:
                pending = self.submitted - self.statistics.total_requests
                if pending > concurrency * 20 and not backlog_warned:
                    print(
                        f"\n{Colors.YELLOW}Warning: request backlog is growing "
                        f"(target RPS may exceed what {concurrency} concurrent requests can sustain).{Colors.RESET}"
                    )
                    backlog_warned = True

            if report and tick % ticks_per_second == 0 and (current_second == 0 or current_second % 10 == 0):
                self.print_report(current_second)

            next_tick_time = start_mono + (tick + 1) * tick_interval
            sleep_for = next_tick_time - time.monotonic()
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)

        return pending_tasks

    async def _run_async(self):
        """Drive warm-up + measured phases for the whole test using aiohttp."""
        concurrency = self.config['threads']
        connector = aiohttp.TCPConnector(limit=concurrency, limit_per_host=max(concurrency, 10))
        timeout = aiohttp.ClientTimeout(total=self.config['timeout'])
        semaphore = asyncio.Semaphore(concurrency)
        pending = set()

        # Cookies are tracked per flow execution in _send_step_async instead, so concurrent
        # "virtual users" never see each other's session state through a shared jar.
        async with aiohttp.ClientSession(
            connector=connector, timeout=timeout, cookie_jar=aiohttp.DummyCookieJar()
        ) as session:
            try:
                warmup_duration = self.config.get('warmup', 0)
                if warmup_duration > 0:
                    print(f"{Colors.DIM}Warming up for {warmup_duration}s (not recorded in results)...{Colors.RESET}")
                    pattern = self.config.get('pattern', 'Constant')
                    base_rps = (
                        self.config.get('start_rps', self.config['target_rps'])
                        if pattern == 'Ramp-up' else self.config['target_rps']
                    )
                    warm_pending = await self._run_phase_async(
                        warmup_duration, lambda _s: base_rps, False, False, session, semaphore
                    )
                    if warm_pending:
                        await asyncio.gather(*warm_pending, return_exceptions=True)
                    self.print_separator()

                self.statistics.start_time = time.time()
                pending = await self._run_phase_async(
                    self.config['duration'], self.calculate_rps_for_second, True, True, session, semaphore
                )

            finally:
                self.running = False
                if self.statistics.start_time is None:
                    self.statistics.start_time = time.time()
                self.statistics.end_time = time.time()
                for task in pending:
                    if not task.done():
                        task.cancel()
                if pending:
                    await asyncio.gather(*pending, return_exceptions=True)

    def execute_test(self):
        """Execute the load test using the configured engine (threads or async)."""
        self.clear_screen()
        self.print_header()
        engine = self.config.get('engine', 'threads')
        print(f"Starting test on {Colors.BLUE}{describe_targets(self.config)}{Colors.RESET}")
        print(f"{Colors.DIM}Engine: {engine}{Colors.RESET}")
        self.print_separator()

        self._prepare_scenario()
        self.running = True
        self.submitted = 0
        self._latency_history = []
        self._rps_history = []

        try:
            signal.signal(signal.SIGTERM, self._handle_sigterm)
        except (AttributeError, ValueError):
            pass

        if engine == 'async':
            self._execute_async()
        else:
            self._execute_threads()

    def _execute_threads(self):
        """Run the test using a pooled requests.Session + ThreadPoolExecutor."""
        num_threads = self.config['threads']
        self.session = self._build_session(num_threads)
        self.executor = ThreadPoolExecutor(max_workers=num_threads, thread_name_prefix="slayer-worker")

        try:
            warmup_duration = self.config.get('warmup', 0)
            if warmup_duration > 0:
                print(f"{Colors.DIM}Warming up for {warmup_duration}s (not recorded in results)...{Colors.RESET}")
                pattern = self.config.get('pattern', 'Constant')
                base_rps = (
                    self.config.get('start_rps', self.config['target_rps'])
                    if pattern == 'Ramp-up' else self.config['target_rps']
                )
                self._run_phase_threads(warmup_duration, lambda _s: base_rps, record=False, report=False)
                self.print_separator()

            self.statistics.start_time = time.time()
            self._run_phase_threads(
                self.config['duration'], self.calculate_rps_for_second, record=True, report=True
            )

        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}Test interrupted by user.{Colors.RESET}")

        finally:
            self.running = False
            if self.statistics.start_time is None:
                self.statistics.start_time = time.time()
            self.statistics.end_time = time.time()
            self.executor.shutdown(wait=True, cancel_futures=True)
            self.session.close()

    def _execute_async(self):
        """Run the test using the aiohttp-based async engine (higher RPS ceiling)."""
        if aiohttp is None:
            print(
                f"{Colors.RED}The async engine requires the 'aiohttp' package. "
                f"Install it with: pip install aiohttp{Colors.RESET}"
            )
            self.running = False
            self.statistics.start_time = self.statistics.start_time or time.time()
            self.statistics.end_time = time.time()
            return

        try:
            asyncio.run(self._run_async())
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}Test interrupted by user.{Colors.RESET}")
            self.running = False
            if self.statistics.start_time is None:
                self.statistics.start_time = time.time()
            if self.statistics.end_time is None:
                self.statistics.end_time = time.time()

    def print_final_report(self):
        """Print final test report."""
        self.clear_screen()
        self.print_header()
        print(f"{Colors.BOLD}Final Test Report{Colors.RESET}")
        self.print_separator()

        stats = self.statistics.get_statistics()
        if not stats:
            print("No data collected.")
            return

        elapsed = max(self.statistics.end_time - self.statistics.start_time, 1e-6)
        cancelled = max(self.submitted - stats['total'], 0)

        print(f"\n{Colors.BOLD}Test Summary{Colors.RESET}")
        print(f"  Duration.................. {elapsed:.1f} seconds")
        print(f"  Total Requests............ {Colors.BLUE}{stats['total']}{Colors.RESET}")
        print(f"  Throughput................ {stats['total']/elapsed:.2f} requests/sec")
        print(f"  Successful Requests....... {Colors.GREEN}{stats['successful']}{Colors.RESET}")
        print(f"  Failed Requests........... {Colors.RED}{stats['failed']}{Colors.RESET}")
        print(f"  Error Rate................ {Colors.YELLOW}{stats['error_rate']:.2f}%{Colors.RESET}")
        if cancelled:
            print(
                f"  Cancelled (unsent)........ {Colors.YELLOW}{cancelled}{Colors.RESET} "
                f"(target RPS exceeded engine capacity)"
            )

        if len(self._latency_history) > 1:
            print(f"\n{Colors.BOLD}Trend Over Time{Colors.RESET}")
            print(f"  Avg Latency: {sparkline(self._latency_history)}")
            print(f"  RPS........: {sparkline(self._rps_history)}")

        self._print_latency_block(stats)
        self._print_status_codes_block(stats, title="HTTP Status Codes Distribution")
        self._print_errors_block(stats, title="Error Summary")
        self._print_per_target_block(stats)

        self.print_separator()
        print("\n")

    def export_report(self, path, threshold_failures=None):
        """Export the final report as JSON. Excludes headers/auth to avoid leaking secrets."""
        stats = self.statistics.get_statistics()
        if not stats:
            return
        elapsed = max(self.statistics.end_time - self.statistics.start_time, 1e-6)

        safe_config = {
            k: v for k, v in self.config.items()
            if k not in ('headers', 'basic_auth', 'json_body', 'raw_body', 'scenario')
        }

        payload = {
            'config': safe_config,
            'started_at': datetime.fromtimestamp(self.statistics.start_time).isoformat(),
            'ended_at': datetime.fromtimestamp(self.statistics.end_time).isoformat(),
            'duration_seconds': elapsed,
            'throughput_rps': stats['total'] / elapsed,
            'cancelled_requests': max(self.submitted - stats['total'], 0),
            **stats,
        }
        if threshold_failures is not None:
            payload['threshold_failures'] = threshold_failures
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Interactive main loop
    # ------------------------------------------------------------------

    def run_interactive(self):
        """Main interactive loop."""
        while True:
            self.clear_screen()
            self.print_header()

            if not self.config:
                print("Welcome to SLAYER Load Testing Tool.")
                print("Please configure your test to begin.\n")
                action = self.prompt(
                    "What would you like to do",
                    options=["Configure New Test", "Load Configuration From File", "Exit"]
                )

                if action == "Configure New Test":
                    self.configure_test()
                elif action == "Load Configuration From File":
                    path = self.prompt("Configuration file path", default="slayer_config.json")
                    try:
                        self.load_config(path)
                        print(f"{Colors.GREEN}Configuration loaded from {path}{Colors.RESET}")
                    except (OSError, json.JSONDecodeError) as e:
                        print(f"{Colors.RED}Could not load configuration: {e}{Colors.RESET}")
                    input("Press Enter to continue...")
                else:
                    print(f"\n{Colors.BLUE}Thank you for using SLAYER. Goodbye.{Colors.RESET}\n")
                    sys.exit(0)
            else:
                action = self.prompt(
                    "What would you like to do",
                    options=[
                        "View Configuration",
                        "Modify Configuration",
                        "Run Test",
                        "Reset Configuration",
                        "Exit"
                    ]
                )

                if action == "View Configuration":
                    self.display_configuration()
                    input("Press Enter to continue...")

                elif action == "Modify Configuration":
                    self.configure_test()

                elif action == "Run Test":
                    confirm = self.prompt(
                        f"I confirm I am authorized to load-test {describe_targets(self.config)} "
                        f"and want to start the test",
                        options=["Yes", "No"]
                    )
                    if confirm == "Yes":
                        self.execute_test()
                        self.print_final_report()
                        if self.prompt("Export this report to a JSON file", options=["No", "Yes"]) == "Yes":
                            path = self.prompt("Report file path", default="slayer_report.json")
                            self.export_report(path)
                            print(f"{Colors.GREEN}Report exported to {path}{Colors.RESET}")
                        input("Press Enter to continue...")

                elif action == "Reset Configuration":
                    self.config = {}
                    self.statistics = Statistics()

                elif action == "Exit":
                    print(f"\n{Colors.BLUE}Thank you for using SLAYER. Goodbye.{Colors.RESET}\n")
                    sys.exit(0)


# ----------------------------------------------------------------------
# Non-interactive / CLI mode
# ----------------------------------------------------------------------

PATTERN_MAP = {'constant': 'Constant', 'ramp-up': 'Ramp-up', 'spike': 'Spike'}
VALIDATION_MAP = {'none': 'No', 'status': 'Check status code', 'content': 'Validate response content'}


def build_arg_parser():
    parser = argparse.ArgumentParser(description="SLAYER - HTTP Load Testing Tool")
    parser.add_argument('--url', help='Target URL. Providing this switches to non-interactive mode.')
    parser.add_argument('--method', choices=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
    parser.add_argument('--threads', type=int,
                         help='Concurrency (1-1000): OS threads, or in-flight requests with --engine async')
    parser.add_argument('--engine', choices=['threads', 'async'],
                         help="Execution engine: 'threads' (default) or 'async' (aiohttp, higher RPS ceiling)")
    parser.add_argument('--duration', type=int, help='Test duration in seconds (1-3600)')
    parser.add_argument('--pattern', choices=list(PATTERN_MAP.keys()))
    parser.add_argument('--rps', type=int, dest='target_rps', help='Target requests per second')
    parser.add_argument('--start-rps', type=int, help='Starting RPS for the ramp-up pattern')
    parser.add_argument('--spike-duration', type=int, help='Spike duration in seconds for the spike pattern')
    parser.add_argument('--timeout', type=int, help='Per-request timeout in seconds (1-60)')
    parser.add_argument('--validation', choices=list(VALIDATION_MAP.keys()))
    parser.add_argument('--validation-keyword', help='Keyword required in response body (with --validation content)')
    parser.add_argument('--header', action='append', default=[], metavar='"Key: Value"',
                         help='Custom request header, repeatable')
    parser.add_argument('--body', help='Raw request body')
    parser.add_argument('--body-file', help='Path to a file containing the request body')
    parser.add_argument('--json-body', action='store_true', help='Treat --body/--body-file as JSON')
    parser.add_argument('--auth-bearer', help='Bearer token for the Authorization header')
    parser.add_argument('--auth-basic', metavar='user:password', help='HTTP Basic Auth credentials')
    parser.add_argument('--insecure', action='store_true', help='Disable SSL certificate verification')
    parser.add_argument('--scenario', help='JSON file with a weighted list of {url, method, weight, ...} '
                                            'request definitions, for multi-endpoint tests')
    parser.add_argument('--warmup', type=int, help='Warm-up seconds before measurements start (not in the report)')
    parser.add_argument('--config', help='Load base configuration from a JSON file')
    parser.add_argument('--save-config', help='Save the resulting configuration to a JSON file')
    parser.add_argument('--output', help='Write the final report as JSON to this path')
    parser.add_argument('--fail-on-error-rate', type=float, metavar='PCT',
                         help='Exit nonzero if the error rate exceeds PCT%%')
    parser.add_argument('--fail-on-p95', type=float, metavar='MS',
                         help='Exit nonzero if p95 latency exceeds MS milliseconds')
    parser.add_argument('--fail-on-p99', type=float, metavar='MS',
                         help='Exit nonzero if p99 latency exceeds MS milliseconds')
    parser.add_argument('--fail-on-avg-latency', type=float, metavar='MS',
                         help='Exit nonzero if average latency exceeds MS milliseconds')
    parser.add_argument('--yes', '-y', action='store_true',
                         help='Skip the authorization confirmation prompt (for automation)')
    parser.add_argument('--log-file', help='Write detailed logs to this file')
    parser.add_argument('--verbose', action='store_true', help='Print debug logs to stderr')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')
    return parser


def confirm_authorization(url, skip):
    """Require an explicit confirmation before generating load against a target."""
    if skip:
        return True
    answer = input(
        f"Do you confirm you are authorized to run this load test against {url}? [y/N]: "
    ).strip().lower()
    return answer in ('y', 'yes', 's', 'si', 'si')


def build_cli_config(args):
    """Merge --config file contents with CLI flags into a LoadTester config dict."""
    config = {}
    if args.config:
        with open(args.config, encoding='utf-8') as f:
            config = json.load(f)
        if isinstance(config.get('basic_auth'), list):
            config['basic_auth'] = tuple(config['basic_auth'])

    if args.scenario:
        with open(args.scenario, encoding='utf-8') as f:
            scenario = json.load(f)
        if not isinstance(scenario, list) or not scenario:
            raise ValueError("--scenario file must contain a non-empty JSON array of request/flow definitions")
        for entry in scenario:
            if not isinstance(entry, dict):
                raise ValueError(f"Invalid scenario entry (must be an object): {entry}")
            flow = normalize_flow_entry(entry)
            if not flow['steps']:
                raise ValueError(f"Scenario entry has no steps: {entry}")
            for step in flow['steps']:
                if not isinstance(step, dict) or not is_valid_url(step.get('url', '')):
                    raise ValueError(f"Invalid or missing 'url' in scenario step: {step}")
        config['scenario'] = scenario

    if args.url:
        config['url'] = args.url
    if not config.get('url') and not config.get('scenario'):
        raise ValueError("You must provide --url, --scenario, or --config with a target.")
    if not config.get('url'):
        config['url'] = describe_targets(config)

    config['method'] = (args.method or config.get('method') or 'GET').upper()
    config['threads'] = args.threads or config.get('threads', 50)
    config['engine'] = args.engine or config.get('engine', 'threads')
    if config['engine'] == 'async' and aiohttp is None:
        raise ValueError("--engine async requires the 'aiohttp' package. Install it with: pip install aiohttp")
    config['duration'] = args.duration or config.get('duration', 60)
    config['pattern'] = PATTERN_MAP.get(args.pattern, config.get('pattern', 'Constant'))
    config['target_rps'] = args.target_rps or config.get('target_rps', 100)

    if config['pattern'] == 'Ramp-up':
        config['start_rps'] = args.start_rps or config.get('start_rps', 10)
    if config['pattern'] == 'Spike':
        config['spike_duration'] = args.spike_duration or config.get('spike_duration', 10)

    config['timeout'] = args.timeout or config.get('timeout', 10)

    if args.validation:
        config['validation_enabled'] = args.validation != 'none'
        config['validation_type'] = VALIDATION_MAP[args.validation]
        if args.validation == 'content':
            if not args.validation_keyword:
                raise ValueError("--validation-keyword is required with --validation content")
            config['validation_keyword'] = args.validation_keyword
    else:
        config.setdefault('validation_enabled', False)

    headers = dict(config.get('headers') or {})
    for raw_header in args.header:
        key, value = parse_header(raw_header)
        headers[key] = value
    if args.auth_bearer:
        headers['Authorization'] = f"Bearer {args.auth_bearer}"
    config['headers'] = headers

    if args.auth_basic:
        if ':' not in args.auth_basic:
            raise ValueError("--auth-basic must be in the form user:password")
        user, password = args.auth_basic.split(':', 1)
        config['basic_auth'] = (user, password)

    body_text = None
    if args.body_file:
        with open(args.body_file, encoding='utf-8') as f:
            body_text = f.read()
    elif args.body is not None:
        body_text = args.body

    if body_text is not None:
        if args.json_body:
            config['json_body'] = json.loads(body_text)
        else:
            config['raw_body'] = body_text

    config['verify_ssl'] = not args.insecure
    config['warmup'] = args.warmup if args.warmup is not None else config.get('warmup', 0)

    return config


def evaluate_thresholds(stats, args):
    """Check final stats against --fail-on-* CLI thresholds. Returns a list of failure descriptions."""
    failures = []
    if args.fail_on_error_rate is not None and stats['error_rate'] > args.fail_on_error_rate:
        failures.append(f"error rate {stats['error_rate']:.2f}% > {args.fail_on_error_rate}%")
    if args.fail_on_p95 is not None and stats['p95_latency'] > args.fail_on_p95:
        failures.append(f"p95 latency {stats['p95_latency']:.2f}ms > {args.fail_on_p95}ms")
    if args.fail_on_p99 is not None and stats['p99_latency'] > args.fail_on_p99:
        failures.append(f"p99 latency {stats['p99_latency']:.2f}ms > {args.fail_on_p99}ms")
    if args.fail_on_avg_latency is not None and stats['avg_latency'] > args.fail_on_avg_latency:
        failures.append(f"average latency {stats['avg_latency']:.2f}ms > {args.fail_on_avg_latency}ms")
    return failures


def run_cli(tester, args):
    """Run a single non-interactive load test based on parsed CLI arguments."""
    try:
        tester.config = build_cli_config(args)
    except (ValueError, OSError, json.JSONDecodeError) as e:
        print(f"{Colors.RED}Configuration error: {e}{Colors.RESET}")
        sys.exit(1)

    if tester.config.get('scenario'):
        for entry in tester.config['scenario']:
            flow = normalize_flow_entry(entry)
            for step in flow['steps']:
                if not is_valid_url(step.get('url', '')):
                    print(f"{Colors.RED}Invalid scenario URL: {step.get('url')}{Colors.RESET}")
                    sys.exit(1)
    elif not tester.validate_url(tester.config['url']):
        print(f"{Colors.RED}Invalid URL: {tester.config['url']}{Colors.RESET}")
        sys.exit(1)

    if not confirm_authorization(describe_targets(tester.config), args.yes):
        print(f"{Colors.YELLOW}Test cancelled: authorization not confirmed.{Colors.RESET}")
        sys.exit(1)

    if args.save_config:
        tester.save_config(args.save_config)

    tester.execute_test()
    tester.print_final_report()

    stats = tester.statistics.get_statistics()
    thresholds_specified = any(
        v is not None for v in (
            args.fail_on_error_rate, args.fail_on_p95, args.fail_on_p99, args.fail_on_avg_latency
        )
    )
    failures = evaluate_thresholds(stats, args) if stats and thresholds_specified else None

    if args.output:
        tester.export_report(args.output, threshold_failures=failures)
        print(f"{Colors.GREEN}Report exported to {args.output}{Colors.RESET}")

    if failures:
        print(f"\n{Colors.RED}Threshold checks failed:{Colors.RESET}")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(2)


def setup_logging(log_file=None, verbose=False):
    logger.setLevel(logging.DEBUG)
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.DEBUG if verbose else logging.WARNING)
    console.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(console)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(threadName)s %(message)s'))
        logger.addHandler(file_handler)


def main():
    """Entry point."""
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.no_color or not sys.stdout.isatty():
        Colors.disable()
    setup_logging(args.log_file, args.verbose)

    tester = LoadTester()

    try:
        if args.url or args.config or args.scenario:
            run_cli(tester, args)
        else:
            tester.run_interactive()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Application terminated by user.{Colors.RESET}\n")
        sys.exit(0)
    except Exception as e:
        logger.exception("Unhandled error")
        print(f"\n{Colors.RED}An error occurred: {e}{Colors.RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
