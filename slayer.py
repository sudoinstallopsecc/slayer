#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLAYER - HTTP Load Testing and Request Framework

A unified HTTP load testing tool with enterprise-grade features including
async requests, connection pooling, circuit breakers, rate limiting,
real-time metrics, and intelligent throttling.

Usage:
    Interactive mode:  python slayer.py
    Load test:         python slayer.py test -u <url> [options]
    Single request:    python slayer.py request -u <url> [options]
    Generate config:   python slayer.py config -o <file>
    System info:       python slayer.py info

Copyright (c) 2026 SLAYER Project
Licensed under MIT License
"""

import asyncio
import json
import os
import random
import sys
import time
import threading
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

import click
import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    SpinnerColumn,
    TaskProgressColumn,
)

# Enterprise imports (degrade gracefully)
_enterprise_available = False
try:
    from slayer_enterprise import SlayerClient, SlayerConfig
    from slayer_enterprise.core.config import load_config
    _enterprise_available = True
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
__version__ = "4.0.0"
console = Console()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

SUPPORTED_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
def print_banner():
    banner_text = (
        "[bold white]"
        " ____  _        _ __   _______ ____  \n"
        "/ ___|| |      / \\\\ \\ / / ____|  _ \\ \n"
        "\\___ \\| |     / _ \\\\ V /|  _| | |_) |\n"
        " ___) | |___ / ___ \\| | | |___|  _ < \n"
        "|____/|_____/_/   \\_\\_| |_____|_| \\_\\"
        "[/bold white]"
    )
    console.print(banner_text)
    console.print(
        f"[dim]HTTP Load Testing and Request Framework  v{__version__}[/dim]\n"
    )


# ============================================================================
# CORE: Synchronous Load Testing Engine (threading-based)
# ============================================================================
class LoadTestEngine:
    """
    Thread-based HTTP load testing engine.

    Uses requests.Session for keep-alive connections and a pool of worker
    threads to generate concurrent load against a target URL.
    """

    def __init__(self):
        self.target_url: str = ""
        self.method: str = "GET"
        self.threads: int = 10
        self.delay: float = 0.01
        self.max_requests: Optional[int] = None
        self.max_time: Optional[int] = None
        self.headers: Dict[str, str] = {}
        self.data: Optional[str] = None
        self.timeout: int = 10

        # Runtime state
        self.running: bool = False
        self.requests_count: int = 0
        self.success_count: int = 0
        self.error_count: int = 0
        self.start_time: float = 0.0
        self.response_times: List[float] = []
        self.status_codes: Dict[int, int] = {}
        self._lock = threading.Lock()
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({"Accept": "*/*", "Connection": "keep-alive"})
        return session

    def _worker(self, thread_id: int):
        while self.running:
            try:
                headers = self.headers.copy()
                headers["User-Agent"] = random.choice(USER_AGENTS)

                t0 = time.time()
                resp = self._session.request(
                    self.method,
                    self.target_url,
                    headers=headers,
                    data=self.data,
                    timeout=self.timeout,
                    allow_redirects=True,
                )
                elapsed_ms = (time.time() - t0) * 1000

                with self._lock:
                    self.requests_count += 1
                    self.response_times.append(elapsed_ms)
                    code = resp.status_code
                    self.status_codes[code] = self.status_codes.get(code, 0) + 1
                    if 200 <= code < 400:
                        self.success_count += 1
                    else:
                        self.error_count += 1

                    if self.max_requests and self.requests_count >= self.max_requests:
                        self.running = False
                        return
                    if self.max_time and (time.time() - self.start_time) >= self.max_time:
                        self.running = False
                        return

            except Exception:
                with self._lock:
                    self.error_count += 1
                    self.requests_count += 1

            if self.delay > 0:
                time.sleep(self.delay)

    def run(
        self,
        url: str,
        method: str = "GET",
        threads: int = 10,
        delay: float = 0.01,
        max_requests: Optional[int] = None,
        max_time: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[str] = None,
        timeout: int = 10,
    ) -> Dict[str, Any]:
        """Execute a load test and return results."""
        if not url.startswith(("http://", "https://")):
            url = "http://" + url

        self.target_url = url
        self.method = method.upper()
        self.threads = threads
        self.delay = delay
        self.max_requests = max_requests
        self.max_time = max_time
        self.headers = headers or {}
        self.data = data
        self.timeout = timeout

        # Reset counters
        self.requests_count = 0
        self.success_count = 0
        self.error_count = 0
        self.response_times = []
        self.status_codes = {}
        self.running = True
        self.start_time = time.time()

        # Start workers
        workers: List[threading.Thread] = []
        for i in range(self.threads):
            t = threading.Thread(target=self._worker, args=(i,), daemon=True)
            workers.append(t)
            t.start()

        # Progress display
        total = max_requests or 0
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[cyan]{task.description}"),
                BarColumn(bar_width=30),
                TaskProgressColumn(),
                TextColumn("[green]RPS: {task.fields[rps]:.1f}"),
                TextColumn("[yellow]Avg: {task.fields[avg]:.0f}ms"),
                TextColumn("[red]Err: {task.fields[errors]}"),
                TimeElapsedColumn(),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task(
                    "Testing",
                    total=total if total else None,
                    rps=0.0,
                    avg=0.0,
                    errors=0,
                )
                prev_count = 0
                prev_time = time.time()

                while self.running:
                    time.sleep(0.4)
                    now = time.time()
                    dt = now - prev_time
                    rps = (self.requests_count - prev_count) / dt if dt > 0 else 0
                    prev_count = self.requests_count
                    prev_time = now

                    avg = 0.0
                    if self.response_times:
                        with self._lock:
                            avg = sum(self.response_times) / len(self.response_times)

                    progress.update(
                        task,
                        completed=self.requests_count if total else None,
                        rps=rps,
                        avg=avg,
                        errors=self.error_count,
                    )
        except KeyboardInterrupt:
            console.print("\n[yellow]Test interrupted.[/yellow]")
        finally:
            self.running = False
            for t in workers:
                t.join(timeout=2)

        return self._build_results()

    def _build_results(self) -> Dict[str, Any]:
        elapsed = time.time() - self.start_time
        rps = self.requests_count / elapsed if elapsed > 0 else 0
        success_rate = (
            (self.success_count / self.requests_count * 100)
            if self.requests_count > 0
            else 0
        )

        times = sorted(self.response_times) if self.response_times else [0]
        n = len(times)

        return {
            "url": self.target_url,
            "method": self.method,
            "threads": self.threads,
            "total_requests": self.requests_count,
            "successful": self.success_count,
            "errors": self.error_count,
            "duration_s": round(elapsed, 2),
            "rps": round(rps, 2),
            "success_rate": round(success_rate, 1),
            "response_times": {
                "avg": round(sum(times) / n, 1) if n else 0,
                "min": round(times[0], 1) if n else 0,
                "median": round(times[n // 2], 1) if n else 0,
                "p95": round(times[int(n * 0.95)], 1) if n > 20 else round(times[-1], 1),
                "p99": round(times[int(n * 0.99)], 1) if n > 100 else round(times[-1], 1),
                "max": round(times[-1], 1) if n else 0,
            },
            "status_codes": dict(sorted(self.status_codes.items())),
        }


# ============================================================================
# CORE: Async Load Testing Engine (aiohttp-based)
# ============================================================================
class AsyncLoadTestEngine:
    """
    Async HTTP load testing engine using aiohttp.

    Provides higher throughput via non-blocking I/O and integrates with the
    enterprise features (circuit breakers, caching, rate limiting) when the
    slayer_enterprise package is installed.
    """

    async def run(
        self,
        url: str,
        method: str = "GET",
        concurrency: int = 10,
        max_requests: Optional[int] = 100,
        max_time: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[str] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """Run an async load test and return results."""
        import aiohttp as _aiohttp

        if not url.startswith(("http://", "https://")):
            url = "http://" + url

        results: Dict[str, Any] = {
            "success": 0,
            "errors": 0,
            "response_times": [],
            "status_codes": {},
        }
        lock = asyncio.Lock()
        stop_event = asyncio.Event()

        async def _make_request(session, sem):
            if stop_event.is_set():
                return
            async with sem:
                if stop_event.is_set():
                    return
                req_headers = dict(headers or {})
                req_headers["User-Agent"] = random.choice(USER_AGENTS)
                t0 = time.time()
                try:
                    async with session.request(
                        method.upper(),
                        url,
                        headers=req_headers,
                        data=data,
                        timeout=_aiohttp.ClientTimeout(total=timeout),
                    ) as resp:
                        await resp.read()
                        elapsed_ms = (time.time() - t0) * 1000
                        async with lock:
                            results["success"] += 1
                            results["response_times"].append(elapsed_ms)
                            code = resp.status
                            results["status_codes"][code] = (
                                results["status_codes"].get(code, 0) + 1
                            )
                except Exception:
                    elapsed_ms = (time.time() - t0) * 1000
                    async with lock:
                        results["errors"] += 1
                        results["response_times"].append(elapsed_ms)

        sem = asyncio.Semaphore(concurrency)
        connector = _aiohttp.TCPConnector(
            limit=concurrency, limit_per_host=concurrency, force_close=False
        )

        start = time.time()
        async with _aiohttp.ClientSession(connector=connector) as session:
            if max_requests:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[cyan]{task.description}"),
                    BarColumn(bar_width=30),
                    TaskProgressColumn(),
                    TimeElapsedColumn(),
                    console=console,
                    transient=True,
                ) as progress:
                    task = progress.add_task("Testing (async)", total=max_requests)
                    batch = 0
                    remaining = max_requests
                    while remaining > 0:
                        chunk = min(remaining, concurrency * 4)
                        tasks = [_make_request(session, sem) for _ in range(chunk)]
                        await asyncio.gather(*tasks)
                        remaining -= chunk
                        batch += chunk
                        progress.update(task, completed=batch)
            elif max_time:
                end_time = start + max_time
                console.print(f"[cyan]Running for {max_time}s ...[/cyan]")
                while time.time() < end_time:
                    tasks = [_make_request(session, sem) for _ in range(concurrency)]
                    await asyncio.gather(*tasks)

        total_time = time.time() - start
        total_reqs = results["success"] + results["errors"]
        rps = total_reqs / total_time if total_time > 0 else 0
        times = sorted(results["response_times"]) if results["response_times"] else [0]
        n = len(times)
        success_rate = (results["success"] / total_reqs * 100) if total_reqs > 0 else 0

        return {
            "url": url,
            "method": method.upper(),
            "concurrency": concurrency,
            "total_requests": total_reqs,
            "successful": results["success"],
            "errors": results["errors"],
            "duration_s": round(total_time, 2),
            "rps": round(rps, 2),
            "success_rate": round(success_rate, 1),
            "response_times": {
                "avg": round(sum(times) / n, 1) if n else 0,
                "min": round(times[0], 1) if n else 0,
                "median": round(times[n // 2], 1) if n else 0,
                "p95": round(times[int(n * 0.95)], 1) if n > 20 else round(times[-1], 1),
                "p99": round(times[int(n * 0.99)], 1) if n > 100 else round(times[-1], 1),
                "max": round(times[-1], 1) if n else 0,
            },
            "status_codes": dict(sorted(results["status_codes"].items())),
        }


# ============================================================================
# Display helpers
# ============================================================================
def display_results(results: Dict[str, Any]) -> None:
    """Render load test results as rich tables."""
    table = Table(title="Test Results", border_style="cyan", show_lines=True)
    table.add_column("Metric", style="white bold")
    table.add_column("Value", style="green")

    table.add_row("Target", results["url"])
    table.add_row("Method", results["method"])
    table.add_row(
        "Concurrency / Threads",
        str(results.get("threads", results.get("concurrency", "-"))),
    )
    table.add_row("Total Requests", f"{results['total_requests']:,}")
    table.add_row("Successful", f"[green]{results['successful']:,}[/green]")
    table.add_row("Errors", f"[red]{results['errors']:,}[/red]")
    table.add_row("Duration", f"{results['duration_s']:.2f} s")
    table.add_row("Requests/sec", f"{results['rps']:.2f}")
    table.add_row("Success Rate", f"{results['success_rate']:.1f}%")
    console.print(table)

    rt = results["response_times"]
    rt_table = Table(title="Response Times (ms)", border_style="blue", show_lines=True)
    rt_table.add_column("Percentile", style="yellow")
    rt_table.add_column("Time (ms)", style="green")
    rt_table.add_row("Min", f"{rt['min']:.1f}")
    rt_table.add_row("Avg", f"{rt['avg']:.1f}")
    rt_table.add_row("Median (P50)", f"{rt['median']:.1f}")
    rt_table.add_row("P95", f"{rt['p95']:.1f}")
    rt_table.add_row("P99", f"{rt['p99']:.1f}")
    rt_table.add_row("Max", f"{rt['max']:.1f}")
    console.print(rt_table)

    if results.get("status_codes"):
        sc_table = Table(title="HTTP Status Codes", border_style="magenta")
        sc_table.add_column("Code", style="yellow")
        sc_table.add_column("Count", style="green")
        for code, count in results["status_codes"].items():
            sc_table.add_row(str(code), f"{count:,}")
        console.print(sc_table)


def display_response(method: str, url: str, resp: requests.Response) -> None:
    """Display a single HTTP response."""
    console.print(f"\n[bold]Status:[/bold]  {resp.status_code}")
    console.print(
        f"[bold]Time:[/bold]    {resp.elapsed.total_seconds() * 1000:.0f} ms"
    )
    console.print(
        f"[bold]Type:[/bold]    {resp.headers.get('Content-Type', 'N/A')}"
    )
    console.print(
        f"[bold]Length:[/bold]  {resp.headers.get('Content-Length', 'N/A')}"
    )

    h_table = Table(title="Response Headers", border_style="dim")
    h_table.add_column("Header", style="cyan")
    h_table.add_column("Value", style="white")
    for k, v in resp.headers.items():
        h_table.add_row(k, v[:120])
    console.print(h_table)


# ============================================================================
# CLI -- Click command group
# ============================================================================
@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="SLAYER")
@click.pass_context
def cli(ctx):
    """SLAYER -- HTTP Load Testing and Request Framework."""
    if ctx.invoked_subcommand is None:
        interactive_mode()


# ---------------------------------------------------------------------------
# Command: test
# ---------------------------------------------------------------------------
@cli.command()
@click.option("--url", "-u", required=True, help="Target URL.")
@click.option(
    "--requests", "-n", "num_requests", default=100, show_default=True,
    help="Total number of requests.",
)
@click.option(
    "--concurrency", "-c", default=10, show_default=True,
    help="Number of concurrent threads/connections.",
)
@click.option(
    "--method", "-m", default="GET", show_default=True, help="HTTP method.",
)
@click.option(
    "--delay", "-d", default=0.0, show_default=True,
    help="Delay between requests per thread (seconds).",
)
@click.option(
    "--duration", "-t", default=None, type=int,
    help="Max test duration in seconds (overrides -n).",
)
@click.option("--data", default=None, help="Request body.")
@click.option(
    "--header", "-H", multiple=True,
    help="Custom header (key:value). Repeatable.",
)
@click.option(
    "--timeout", default=10, show_default=True,
    help="Request timeout in seconds.",
)
@click.option(
    "--engine",
    type=click.Choice(["sync", "async"]),
    default="sync",
    show_default=True,
    help="Engine: sync (threading) or async (aiohttp).",
)
@click.option(
    "--output", "-o", default=None, help="Save results to JSON file.",
)
def test(url, num_requests, concurrency, method, delay, duration, data,
         header, timeout, engine, output):
    """Run an HTTP load test against a target URL."""
    print_banner()

    headers: Dict[str, str] = {}
    for h in header:
        if ":" in h:
            k, v = h.split(":", 1)
            headers[k.strip()] = v.strip()

    console.print(
        Panel.fit(
            f"[bold]Target:[/bold]       {url}\n"
            f"[bold]Method:[/bold]       {method.upper()}\n"
            f"[bold]Requests:[/bold]     "
            f"{str(duration) + 's' if duration else num_requests}\n"
            f"[bold]Concurrency:[/bold]  {concurrency}\n"
            f"[bold]Engine:[/bold]       {engine}",
            title="Load Test Configuration",
            border_style="cyan",
        )
    )
    console.print()

    if engine == "async":
        async_engine = AsyncLoadTestEngine()
        results = asyncio.run(
            async_engine.run(
                url=url,
                method=method,
                concurrency=concurrency,
                max_requests=None if duration else num_requests,
                max_time=duration,
                headers=headers,
                data=data,
                timeout=timeout,
            )
        )
    else:
        sync_engine = LoadTestEngine()
        results = sync_engine.run(
            url=url,
            method=method,
            threads=concurrency,
            delay=delay,
            max_requests=None if duration else num_requests,
            max_time=duration,
            headers=headers,
            data=data,
            timeout=timeout,
        )

    console.print()
    display_results(results)

    if output:
        with open(output, "w") as f:
            json.dump(results, f, indent=2)
        console.print(f"\n[green]Results saved to {output}[/green]")


# ---------------------------------------------------------------------------
# Command: request
# ---------------------------------------------------------------------------
@cli.command("request")
@click.option("--url", "-u", required=True, help="Target URL.")
@click.option(
    "--method", "-m", default="GET", show_default=True, help="HTTP method.",
)
@click.option(
    "--header", "-H", multiple=True,
    help="Custom header (key:value). Repeatable.",
)
@click.option(
    "--data", "-d", default=None,
    help="Request body (JSON string or plain text).",
)
@click.option(
    "--output", "-o", default=None, help="Save response body to file.",
)
@click.option(
    "--verbose", "-v", is_flag=True, help="Show response body.",
)
def single_request(url, method, header, data, output, verbose):
    """Make a single HTTP request and display the response."""
    print_banner()

    headers: Dict[str, str] = {"User-Agent": random.choice(USER_AGENTS)}
    for h in header:
        if ":" in h:
            k, v = h.split(":", 1)
            headers[k.strip()] = v.strip()

    json_data = None
    body = data
    if data:
        try:
            json_data = json.loads(data)
            body = None
        except json.JSONDecodeError:
            pass

    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]Sending request..."),
        console=console,
        transient=True,
    ) as prog:
        prog.add_task("req", total=None)
        resp = requests.request(
            method.upper(), url, headers=headers,
            json=json_data, data=body, timeout=30,
        )

    display_response(method.upper(), url, resp)

    if verbose:
        body_text = resp.text
        console.print(f"\n[bold]Body ({len(body_text)} chars):[/bold]")
        console.print(
            body_text[:2000] + ("..." if len(body_text) > 2000 else "")
        )

    if output:
        with open(output, "w") as f:
            f.write(resp.text)
        console.print(f"\n[green]Response saved to {output}[/green]")


# ---------------------------------------------------------------------------
# Command: config
# ---------------------------------------------------------------------------
@cli.command("config")
@click.option(
    "--output", "-o", default="slayer_config.json", show_default=True,
    help="Output file.",
)
def generate_config(output):
    """Generate a sample configuration file."""
    sample = {
        "target_url": "https://httpbin.org/get",
        "method": "GET",
        "requests": 500,
        "concurrency": 20,
        "delay": 0.0,
        "timeout": 10,
        "engine": "sync",
        "headers": {},
        "data": None,
    }
    with open(output, "w") as f:
        json.dump(sample, f, indent=2)
    console.print(f"[green]Configuration template saved to {output}[/green]")


# ---------------------------------------------------------------------------
# Command: info
# ---------------------------------------------------------------------------
@cli.command("info")
def info():
    """Display system and version information."""
    print_banner()
    table = Table(title="System Information", border_style="cyan")
    table.add_column("Component", style="yellow")
    table.add_column("Status", style="green")
    table.add_row("Version", __version__)
    table.add_row("Python", sys.version.split()[0])
    table.add_row("Sync engine (requests)", "available")
    table.add_row(
        "Async engine (aiohttp)",
        "[green]available[/green]"
        if _enterprise_available
        else "[red]not installed[/red]",
    )
    table.add_row(
        "Enterprise features",
        "[green]available[/green]"
        if _enterprise_available
        else "[red]not installed[/red]",
    )
    console.print(table)


# ============================================================================
# Interactive Mode
# ============================================================================
def interactive_mode():
    """Launch the interactive shell for quick testing."""
    print_banner()

    state: Dict[str, Any] = {
        "url": "",
        "method": "GET",
        "threads": 10,
        "delay": 0.01,
        "requests": 100,
        "duration": None,
        "data": None,
        "headers": {},
        "timeout": 10,
        "engine": "sync",
    }

    def show_status():
        t = Table(border_style="dim", show_header=False, padding=(0, 2))
        t.add_column("Key", style="cyan")
        t.add_column("Value", style="white")
        t.add_row("Target", state["url"] or "[dim]not set[/dim]")
        t.add_row("Method", state["method"])
        t.add_row("Threads", str(state["threads"]))
        t.add_row(
            "Requests",
            str(state["duration"]) + "s"
            if state["duration"]
            else str(state["requests"]),
        )
        t.add_row("Delay", f"{state['delay']}s")
        t.add_row("Engine", state["engine"])
        console.print(t)

    def show_help():
        console.print(
            Panel(
                "[bold]Commands:[/bold]\n\n"
                "  [cyan]target[/cyan] <url>             Set the target URL\n"
                "  [cyan]method[/cyan] <GET|POST|...>    Set the HTTP method\n"
                "  [cyan]threads[/cyan] <n>              Set concurrent threads\n"
                "  [cyan]requests[/cyan] <n>             Set total request count\n"
                "  [cyan]duration[/cyan] <seconds>       Set test duration\n"
                "  [cyan]delay[/cyan] <seconds>          Set delay between requests\n"
                "  [cyan]data[/cyan] <text>              Set request body\n"
                "  [cyan]header[/cyan] <key:value>       Add a custom header\n"
                "  [cyan]engine[/cyan] <sync|async>      Set testing engine\n"
                "  [cyan]timeout[/cyan] <seconds>        Set request timeout\n\n"
                "  [cyan]run[/cyan]                      Start the load test\n"
                "  [cyan]request[/cyan]                  Single request to target\n"
                "  [cyan]status[/cyan]                   Show current config\n"
                "  [cyan]clear[/cyan]                    Clear screen\n"
                "  [cyan]help[/cyan]                     Show this help\n"
                "  [cyan]exit[/cyan]                     Quit\n",
                title="Help",
                border_style="cyan",
            )
        )

    show_help()

    while True:
        try:
            raw = console.input("[bold]slayer>[/bold] ").strip()
            if not raw:
                continue

            parts = raw.split()
            cmd = parts[0].lower()

            if cmd in ("exit", "quit", "q"):
                console.print("[dim]Goodbye.[/dim]")
                break

            elif cmd == "help":
                show_help()

            elif cmd == "clear":
                os.system("clear" if os.name == "posix" else "cls")
                print_banner()

            elif cmd == "status":
                show_status()

            elif cmd == "target":
                if len(parts) < 2:
                    console.print("[red]Usage: target <url>[/red]")
                else:
                    state["url"] = parts[1]
                    console.print(f"[green]Target set: {parts[1]}[/green]")

            elif cmd == "method":
                if len(parts) < 2:
                    console.print(
                        f"[red]Usage: method "
                        f"<{'|'.join(SUPPORTED_METHODS)}>[/red]"
                    )
                else:
                    m = parts[1].upper()
                    if m in SUPPORTED_METHODS:
                        state["method"] = m
                        console.print(f"[green]Method set: {m}[/green]")
                    else:
                        console.print(f"[red]Unsupported method: {m}[/red]")

            elif cmd == "threads":
                if len(parts) < 2:
                    console.print("[red]Usage: threads <number>[/red]")
                else:
                    try:
                        n = int(parts[1])
                        if n > 0:
                            state["threads"] = n
                            console.print(f"[green]Threads set: {n}[/green]")
                        else:
                            console.print("[red]Must be > 0[/red]")
                    except ValueError:
                        console.print("[red]Must be a number[/red]")

            elif cmd == "requests":
                if len(parts) < 2:
                    console.print("[red]Usage: requests <number>[/red]")
                else:
                    try:
                        n = int(parts[1])
                        state["requests"] = n
                        state["duration"] = None
                        console.print(f"[green]Requests set: {n}[/green]")
                    except ValueError:
                        console.print("[red]Must be a number[/red]")

            elif cmd == "duration":
                if len(parts) < 2:
                    console.print("[red]Usage: duration <seconds>[/red]")
                else:
                    try:
                        s = parts[1].rstrip("s")
                        n = int(s)
                        state["duration"] = n
                        console.print(f"[green]Duration set: {n}s[/green]")
                    except ValueError:
                        console.print("[red]Must be a number[/red]")

            elif cmd == "delay":
                if len(parts) < 2:
                    console.print("[red]Usage: delay <seconds>[/red]")
                else:
                    try:
                        d = float(parts[1])
                        state["delay"] = d
                        console.print(f"[green]Delay set: {d}s[/green]")
                    except ValueError:
                        console.print("[red]Must be a number[/red]")

            elif cmd == "data":
                if len(parts) < 2:
                    state["data"] = None
                    console.print("[green]Data cleared[/green]")
                else:
                    state["data"] = " ".join(parts[1:])
                    console.print("[green]Data set[/green]")

            elif cmd == "header":
                if len(parts) < 2:
                    console.print("[red]Usage: header <key:value>[/red]")
                else:
                    h = " ".join(parts[1:])
                    if ":" in h:
                        k, v = h.split(":", 1)
                        state["headers"][k.strip()] = v.strip()
                        console.print(
                            f"[green]Header set: {k.strip()}[/green]"
                        )
                    else:
                        console.print("[red]Format: key:value[/red]")

            elif cmd == "engine":
                if len(parts) < 2 or parts[1].lower() not in (
                    "sync", "async",
                ):
                    console.print("[red]Usage: engine <sync|async>[/red]")
                else:
                    state["engine"] = parts[1].lower()
                    console.print(
                        f"[green]Engine set: {state['engine']}[/green]"
                    )

            elif cmd == "timeout":
                if len(parts) < 2:
                    console.print("[red]Usage: timeout <seconds>[/red]")
                else:
                    try:
                        t = int(parts[1])
                        state["timeout"] = t
                        console.print(f"[green]Timeout set: {t}s[/green]")
                    except ValueError:
                        console.print("[red]Must be a number[/red]")

            elif cmd == "run":
                if not state["url"]:
                    console.print(
                        "[red]Set a target first: target <url>[/red]"
                    )
                    continue

                console.print()
                if state["engine"] == "async":
                    eng = AsyncLoadTestEngine()
                    results = asyncio.run(
                        eng.run(
                            url=state["url"],
                            method=state["method"],
                            concurrency=state["threads"],
                            max_requests=(
                                None
                                if state["duration"]
                                else state["requests"]
                            ),
                            max_time=state["duration"],
                            headers=state["headers"],
                            data=state["data"],
                            timeout=state["timeout"],
                        )
                    )
                else:
                    eng = LoadTestEngine()
                    results = eng.run(
                        url=state["url"],
                        method=state["method"],
                        threads=state["threads"],
                        delay=state["delay"],
                        max_requests=(
                            None
                            if state["duration"]
                            else state["requests"]
                        ),
                        max_time=state["duration"],
                        headers=state["headers"],
                        data=state["data"],
                        timeout=state["timeout"],
                    )
                console.print()
                display_results(results)

            elif cmd == "request":
                if not state["url"]:
                    console.print(
                        "[red]Set a target first: target <url>[/red]"
                    )
                    continue
                url = state["url"]
                if not url.startswith(("http://", "https://")):
                    url = "http://" + url
                hdrs = dict(state["headers"])
                hdrs["User-Agent"] = random.choice(USER_AGENTS)
                resp = requests.request(
                    state["method"],
                    url,
                    headers=hdrs,
                    data=state["data"],
                    timeout=state["timeout"],
                )
                display_response(state["method"], url, resp)

            else:
                console.print(f"[red]Unknown command: {cmd}[/red]")
                console.print(
                    "[dim]Type 'help' for available commands.[/dim]"
                )

        except KeyboardInterrupt:
            console.print()
        except EOFError:
            console.print("\n[dim]Goodbye.[/dim]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


# ============================================================================
# Entry point
# ============================================================================
if __name__ == "__main__":
    cli()