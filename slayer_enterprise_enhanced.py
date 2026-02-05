"""
SLAYER Enterprise Load Testing Framework
===========================================

Advanced HTTP load testing tool with enterprise features:
- Intelligent throttle with back-off strategies
- Advanced traffic patterns
- Distributed coordination
- Real-time metrics and dashboard
- SLO monitoring
"""

import asyncio
import json
import signal
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

# Import enterprise components
from slayer_enterprise.testing.patterns import TrafficPatternEngine, RequestPattern, PatternType
from slayer_enterprise.testing.coordinator import TestCoordinator, DistributedCoordinator
from slayer_enterprise.testing.metrics import LoadTestMetrics, MetricsDashboard, SLO
from slayer_enterprise.testing.throttle import IntelligentThrottle, ThrottleConfig, BackoffStrategy

console = Console()


class LoadTester:
    """
    Enterprise load tester with advanced features.
    """
    
    def __init__(self):
        # Initialize components
        self.throttle_config = ThrottleConfig()
        self.throttle = IntelligentThrottle(self.throttle_config)
        
        self.pattern_engine = TrafficPatternEngine()
        self.metrics = LoadTestMetrics()
        self.dashboard = MetricsDashboard(self.metrics)
        
        self.coordinator = TestCoordinator()
        
        # Test state
        self.current_test_id: Optional[str] = None
        self.running = False
        
        console.print("[green]SLAYER Enterprise Load Tester initialized[/green]")
    
    async def run_load_test(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a complete load test with monitoring.
        
        Args:
            config: Test configuration
        
        Returns:
            Test results
        """
        target_url = config['target_url']
        
        # Display test banner
        console.print("\n[bold white]SLAYER[/bold white]")
        console.print("[cyan]Enterprise Load Testing Framework[/cyan]")
        console.print(f"\n[green]Target:[/green] {target_url}")
        console.print(f"[green]Rate:[/green] {config.get('target_rps', 50)} req/s")
        console.print(f"[green]Duration:[/green] {config.get('duration', 60)}s")
        console.print(f"[green]Pattern:[/green] {config.get('pattern', {}).get('type', 'constant')}")
        
        # Start dashboard if enabled
        if config.get('enable_dashboard', False):
            console.print("\n[blue]🚀 Starting dashboard at http://localhost:8080[/blue]")
            await self.dashboard.start()
            for warning in warnings:
                console.print(f"  {warning}")
        
        # User confirmation for high-intensity tests
        if config.get('target_rps', 0) > self.auth_config.high_intensity_rps:
            if not config.get('auto_confirm', False):
                confirm = click.confirm(
                    f"\nThis is a high-intensity test ({config.get('target_rps')} RPS). "
                    "Are you sure you want to proceed?"
                )
                if not confirm:
                    console.print("[red]Test cancelled by user[/red]")
                    return {'status': 'cancelled', 'reason': 'User cancelled high-intensity test'}
        
        # 🎯 PHASE 2: Configure Traffic Patterns
        console.print("\n[bold blue]🎯 PHASE 2: Traffic Pattern Configuration[/bold blue]")
        
        pattern_config = config.get('pattern', {})
        pattern_type = PatternType(pattern_config.get('type', 'constant'))
        
        pattern = RequestPattern(
            name=f"Load Test Pattern",
            pattern_type=pattern_type,
            duration_seconds=config.get('duration', 60),
            target_rps=config.get('target_rps', 100),
            **pattern_config
        )
        
        self.pattern_engine.add_pattern(pattern)
        
        # Show pattern preview
        preview = self.pattern_engine.get_pattern_preview(pattern, 60)
        console.print(f"[cyan]Pattern Preview (first 60s): Max RPS = {max(rps for _, rps in preview)}[/cyan]")
        
        # 🎛️  PHASE 3: Configure Intelligent Throttling
        console.print("\n[bold blue]🎛️ PHASE 3: Intelligent Throttling Setup[/bold blue]")
        
        # Update throttle config with test parameters
        self.throttle.set_target_rps(config.get('target_rps', 100))
        
        # Add SLOs
        for slo in self.throttle.create_standard_slos():
            self.metrics.add_slo(slo)
        
        # Custom SLOs from config
        for slo_config in config.get('slos', []):
            slo = SLO(**slo_config)
            self.metrics.add_slo(slo)
        
        console.print(f"[green]✅ Throttling configured with target {config.get('target_rps', 100)} RPS[/green]")
        
        # 📊 PHASE 4: Start Monitoring Dashboard
        console.print("\n[bold blue]📊 PHASE 4: Starting Monitoring Dashboard[/bold blue]")
        
        if config.get('enable_dashboard', True):
            try:
                dashboard_server = await self.dashboard.start_server()
                dashboard_url = f"http://localhost:{self.dashboard.port}"
                console.print(f"[green]✅ Dashboard started: {dashboard_url}[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠️  Dashboard failed to start: {e}[/yellow]")
        
        # 🚀 PHASE 5: Execute Load Test
        console.print("\n[bold blue]🚀 PHASE 5: Executing Load Test[/bold blue]")
        
        # Start the test
        self.current_test_id = await self.coordinator.start_test(config)
        self.running = True
        
        # Reset metrics for new test
        self.metrics.reset()
        
        console.print(f"[green]🟢 Load test started (ID: {self.current_test_id})[/green]")
        
        # Execute the actual requests
        try:
            test_results = await self._execute_test_requests(target_url, config)
        except KeyboardInterrupt:
            console.print("\n[yellow]⏸️  Test interrupted by user[/yellow]")
            test_results = self._get_partial_results()
        except Exception as e:
            console.print(f"\n[red]❌ Test failed: {e}[/red]")
            test_results = {'status': 'failed', 'error': str(e)}
        finally:
            self.running = False
            if self.current_test_id:
                self.coordinator.stop_test(self.current_test_id)
        
        # 📋 PHASE 6: Generate Final Report
        console.print("\n[bold blue]📋 PHASE 6: Final Results Analysis[/bold blue]")
        
        final_metrics = self.metrics.get_test_summary()
        
        # Create results summary
        results = {
            'test_id': self.current_test_id,
            'target_url': target_url,
            'authorization': auth_details,
            'configuration': config,
            'metrics': final_metrics,
            'throttle_state': self.throttle.get_current_state(),
            'test_results': test_results,
            'status': 'completed' if not test_results.get('error') else 'failed'
        }
        
        self._display_final_results(results)
        
        return results
    
    async def _execute_test_requests(self, target_url: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the actual HTTP requests with throttling and monitoring."""
        import aiohttp
        import time
        
        async def make_request(request_config: Dict[str, Any]):
            """Make a single HTTP request with throttling and metrics."""
            
            # Check if we should make this request (throttling)
            should_make, delay = await self.throttle.should_make_request()
            
            if not should_make:
                if delay:
                    await asyncio.sleep(delay)
                return  # Skip this request
            
            start_time = time.time()
            
            try:
                async with aiohttp.ClientSession() as session:
                    method = request_config.get('method', 'GET')
                    
                    async with session.request(
                        method,
                        target_url,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        response_time = (time.time() - start_time) * 1000
                        
                        # Record metrics
                        self.metrics.record_request(
                            response_time_ms=response_time,
                            status_code=response.status,
                            bytes_sent=100,  # Approximate
                            bytes_received=len(await response.read())
                        )
                        
                        # Update throttle
                        self.throttle.record_request_result(
                            response_time,
                            response.status
                        )
                        
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                
                # Record error metrics
                self.metrics.record_request(
                    response_time_ms=response_time,
                    status_code=0,
                    error_type=type(e).__name__
                )
                
                # Update throttle with error
                self.throttle.record_request_result(
                    response_time,
                    0,
                    type(e).__name__
                )
        
        # Execute patterns
        return await self.pattern_engine.execute_patterns(make_request)
    
    def _get_partial_results(self) -> Dict[str, Any]:
        """Get partial results when test is interrupted."""
        return {
            'status': 'interrupted',
            'partial_metrics': self.metrics.get_test_summary(),
            'message': 'Test was interrupted before completion'
        }
    
    def _display_final_results(self, results: Dict[str, Any]):
        """Display comprehensive test results."""
        metrics = results['metrics']
        
        # Main results table
        table = Table(title="🎯 Load Test Results Summary", style="cyan")
        table.add_column("Metric", style="yellow")
        table.add_column("Value", style="green")
        
        table.add_row("Test Duration", f"{metrics['test_duration']:.1f} seconds")
        table.add_row("Total Requests", f"{metrics['total_requests']:,}")
        table.add_row("Successful Requests", f"{metrics['successful_requests']:,}")
        table.add_row("Failed Requests", f"{metrics['failed_requests']:,}")
        table.add_row("Error Rate", f"{metrics['error_rate']:.1f}%")
        table.add_row("Average RPS", f"{metrics['average_rps']:.1f}")
        table.add_row("Final RPS", f"{metrics['current_rps']:.1f}")
        
        console.print(table)
        
        # Response time statistics
        rt_table = Table(title="📈 Response Time Statistics", style="blue")
        rt_table.add_column("Percentile", style="yellow")
        rt_table.add_column("Time (ms)", style="green")
        
        response_times = metrics['response_times']
        rt_table.add_row("Average", f"{response_times['sum'] / response_times['count'] if response_times['count'] > 0 else 0:.1f}")
        rt_table.add_row("Minimum", f"{response_times['min']:.1f}")
        rt_table.add_row("P50 (Median)", f"{response_times['p50']:.1f}")
        rt_table.add_row("P95", f"{response_times['p95']:.1f}")
        rt_table.add_row("P99", f"{response_times['p99']:.1f}")
        rt_table.add_row("Maximum", f"{response_times['max']:.1f}")
        
        console.print(rt_table)
        
        # SLO Summary
        slo_summary = metrics.get('slo_summary', {})
        if slo_summary.get('total_slos', 0) > 0:
            slo_panel = Panel(
                f"[yellow]SLOs Monitored:[/yellow] {slo_summary['total_slos']}\n"
                f"[red]Recent Violations:[/red] {slo_summary['recent_violations']}\n"
                f"[cyan]Violation Breakdown:[/cyan] {slo_summary['violation_breakdown']}",
                title="🎯 SLO Monitoring Results"
            )
            console.print(slo_panel)
        
        # Status codes breakdown
        if metrics.get('status_codes'):
            status_table = Table(title="📊 HTTP Status Codes", style="magenta")
            status_table.add_column("Status Code", style="yellow")
            status_table.add_column("Count", style="green")
            
            for code, count in metrics['status_codes'].items():
                status_table.add_row(str(code), f"{count:,}")
            
            console.print(status_table)


@click.group()
@click.version_option(version="4.0.0")
def cli():
    """SLAYER Enterprise Load Testing Framework v4.0"""
    pass


@cli.command()
@click.option('--url', '-u', required=True, help='Target URL for load testing')
@click.option('--rps', '-r', default=50, help='Requests per second')
@click.option('--duration', '-d', default=60, help='Test duration in seconds') 
@click.option('--threads', '-t', default=10, help='Concurrent connections')
@click.option('--method', '-m', default='GET', help='HTTP method')
@click.option('--pattern', default='constant', help='Traffic pattern: constant, ramp_up, burst, wave')
@click.option('--dashboard/--no-dashboard', default=False, help='Enable web dashboard')
@click.option('--config', '-c', help='Load from JSON config file')
def load_test(url, rps, duration, threads, method, pattern, dashboard, config):
    """Run HTTP load test against target URL."""
    
    # Load configuration
    if config:
        with open(config, 'r') as f:
            test_config = json.load(f)
    else:
        test_config = {
            'target_url': url,
            'target_rps': rps,
            'duration': duration,
            'concurrent_connections': threads,
            'method': method,
            'pattern': {'type': pattern},
            'enable_dashboard': dashboard
        }
    
    # Run test
    async def run_test():
        tester = LoadTester()
        results = await tester.run_load_test(test_config)
        
        # Save results
        results_file = f"slayer_results_{int(time.time())}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        console.print(f"\n[green]Results saved: {results_file}[/green]")
        return results
    
    try:
        asyncio.run(run_test())
    except KeyboardInterrupt:
        console.print("\n[yellow]Test interrupted[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Test failed: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--output', '-o', default='slayer_config.json', help='Output configuration file')
def generate_config(output):
    """Generate sample configuration file."""
    
    sample_config = {
        "target_url": "https://httpbin.org/get",
        "target_rps": 100,
        "duration": 300,
        "concurrent_connections": 20,
        "method": "GET",
        "pattern": {
            "type": "ramp_up",
            "start_rps": 10,
            "end_rps": 100,
            "ramp_duration": 60
        },
        "throttle": {
            "enabled": True,
            "max_rps": 200,
            "initial_delay": 0.01
        },
        "slo": {
            "max_response_time_ms": 500,
            "min_success_rate": 99.0,
            "max_error_rate": 1.0
        },
        "enable_dashboard": True
    }
    
    with open(output, 'w') as f:
        json.dump(sample_config, f, indent=2)
    
    console.print(f"[green]Config template saved: {output}[/green]")
    console.print(f"[cyan]Edit the file and run: slayer load-test --config {output}[/cyan]")
            "ramp_start_rps": 10,
            "ramp_end_rps": 100
        },
        "throttle": {
            "max_rps": 200,
            "min_rps": 5,
            "error_rate_threshold": 5.0,
            "response_time_threshold": 3000.0,
            "backoff_strategy": "adaptive"
        },
        "slos": [
            {
                "name": "response_time_p95",
                "metric_name": "response_time_p95", 
                "threshold": 500.0,
                "operator": "lt",
                "window_seconds": 60,
                "description": "95th percentile response time should be under 500ms"
            },
            {
                "name": "error_rate",
                "metric_name": "error_rate",
                "threshold": 1.0,
                "operator": "lt", 
                "window_seconds": 30,
                "description": "Error rate should be under 1%"
            }
        ],
        "enable_dashboard": True
    }
    
    with open(output, 'w') as f:
        json.dump(sample_config, f, indent=2)
    
    console.print(f"[green]Config template saved: {output}[/green]")


if __name__ == "__main__":
    cli()