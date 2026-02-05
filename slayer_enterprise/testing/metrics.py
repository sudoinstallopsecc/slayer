"""
Real-time Metrics and Dashboard System for SLAYER Enterprise
=========================================================

Advanced monitoring and visualization system for load testing with:
- Real-time metrics collection and aggregation
- SLO (Service Level Objective) monitoring
- Percentile analysis (p50, p95, p99)
- Interactive web dashboard
- Alerting and threshold management
- Historical data analysis
"""

import asyncio
import json
import time
import statistics
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import logging
import numpy as np
from threading import Lock
import websockets
import aioredis

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: float
    value: Union[int, float]
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class ResponseTimeMetrics:
    """Detailed response time statistics."""
    count: int
    sum: float
    min: float
    max: float
    p50: float
    p95: float
    p99: float
    p99_9: float


@dataclass
class RequestMetrics:
    """Comprehensive request metrics."""
    timestamp: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    current_rps: float
    
    # Response time metrics
    response_times: ResponseTimeMetrics
    
    # Error breakdown
    error_counts: Dict[str, int]
    status_code_counts: Dict[int, int]
    
    # Network metrics
    bytes_sent: int
    bytes_received: int
    
    # Connection metrics
    active_connections: int
    connection_errors: int


@dataclass
class SLO:
    """Service Level Objective definition."""
    name: str
    metric_name: str
    threshold: float
    operator: str  # 'lt', 'le', 'gt', 'ge', 'eq'
    window_seconds: int
    description: str = ""


class MetricsBuffer:
    """Thread-safe circular buffer for storing metrics."""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.data = deque(maxlen=max_size)
        self.lock = Lock()
    
    def add(self, point: MetricPoint):
        """Add a metric point to the buffer."""
        with self.lock:
            self.data.append(point)
    
    def get_range(self, start_time: float, end_time: float) -> List[MetricPoint]:
        """Get metric points within a time range."""
        with self.lock:
            return [
                point for point in self.data
                if start_time <= point.timestamp <= end_time
            ]
    
    def get_latest(self, count: int = 100) -> List[MetricPoint]:
        """Get the latest N metric points."""
        with self.lock:
            return list(self.data)[-count:] if len(self.data) >= count else list(self.data)
    
    def clear(self):
        """Clear all data from the buffer."""
        with self.lock:
            self.data.clear()


class ResponseTimeTracker:
    """Track and analyze response times with percentile calculations."""
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.response_times = deque(maxlen=window_size)
        self.lock = Lock()
    
    def add_response_time(self, response_time_ms: float):
        """Add a response time measurement."""
        with self.lock:
            self.response_times.append(response_time_ms)
    
    def get_percentiles(self) -> ResponseTimeMetrics:
        """Calculate response time percentiles."""
        with self.lock:
            if not self.response_times:
                return ResponseTimeMetrics(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
            
            times = list(self.response_times)
            times.sort()
            
            return ResponseTimeMetrics(
                count=len(times),
                sum=sum(times),
                min=min(times),
                max=max(times),
                p50=np.percentile(times, 50),
                p95=np.percentile(times, 95),
                p99=np.percentile(times, 99),
                p99_9=np.percentile(times, 99.9)
            )


class SLOMonitor:
    """Monitor Service Level Objectives during testing."""
    
    def __init__(self):
        self.slos: Dict[str, SLO] = {}
        self.violations: List[Dict[str, Any]] = []
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
    
    def add_slo(self, slo: SLO):
        """Add an SLO to monitor."""
        self.slos[slo.name] = slo
        logger.info(f"Added SLO: {slo.name} - {slo.description}")
    
    def check_slos(self, current_metrics: RequestMetrics) -> List[Dict[str, Any]]:
        """Check all SLOs against current metrics and return violations."""
        violations = []
        current_time = current_metrics.timestamp
        
        for slo_name, slo in self.slos.items():
            try:
                # Get metric value
                metric_value = self._get_metric_value(current_metrics, slo.metric_name)
                
                # Store in history
                self.metrics_history[slo_name].append({
                    'timestamp': current_time,
                    'value': metric_value
                })
                
                # Check if we have enough data for the window
                window_data = [
                    point for point in self.metrics_history[slo_name]
                    if current_time - point['timestamp'] <= slo.window_seconds
                ]
                
                if len(window_data) < 2:
                    continue  # Not enough data
                
                # Calculate window average
                avg_value = sum(point['value'] for point in window_data) / len(window_data)
                
                # Check threshold
                is_violation = self._check_threshold(avg_value, slo.threshold, slo.operator)
                
                if is_violation:
                    violation = {
                        'slo_name': slo_name,
                        'slo_description': slo.description,
                        'metric_name': slo.metric_name,
                        'actual_value': avg_value,
                        'threshold': slo.threshold,
                        'operator': slo.operator,
                        'window_seconds': slo.window_seconds,
                        'timestamp': current_time,
                        'severity': self._calculate_severity(avg_value, slo.threshold, slo.operator)
                    }
                    violations.append(violation)
                    self.violations.append(violation)
                    
                    logger.warning(
                        f"SLO violation: {slo_name} - {avg_value} {slo.operator} {slo.threshold}"
                    )
                
            except Exception as e:
                logger.error(f"Error checking SLO {slo_name}: {e}")
        
        return violations
    
    def _get_metric_value(self, metrics: RequestMetrics, metric_name: str) -> float:
        """Extract metric value by name."""
        if metric_name == 'response_time_p95':
            return metrics.response_times.p95
        elif metric_name == 'response_time_p99':
            return metrics.response_times.p99
        elif metric_name == 'error_rate':
            total = metrics.total_requests
            errors = metrics.failed_requests
            return (errors / total * 100) if total > 0 else 0
        elif metric_name == 'current_rps':
            return metrics.current_rps
        elif metric_name == 'avg_response_time':
            count = metrics.response_times.count
            return (metrics.response_times.sum / count) if count > 0 else 0
        else:
            raise ValueError(f"Unknown metric: {metric_name}")
    
    def _check_threshold(self, value: float, threshold: float, operator: str) -> bool:
        """Check if value violates threshold."""
        if operator == 'lt':
            return value < threshold
        elif operator == 'le':
            return value <= threshold
        elif operator == 'gt':
            return value > threshold
        elif operator == 'ge':
            return value >= threshold
        elif operator == 'eq':
            return abs(value - threshold) < 0.001  # Float equality
        else:
            raise ValueError(f"Unknown operator: {operator}")
    
    def _calculate_severity(self, value: float, threshold: float, operator: str) -> str:
        """Calculate violation severity."""
        if operator in ['lt', 'le']:
            ratio = threshold / value if value > 0 else float('inf')
        else:
            ratio = value / threshold if threshold > 0 else float('inf')
        
        if ratio >= 2.0:
            return 'critical'
        elif ratio >= 1.5:
            return 'high'
        elif ratio >= 1.2:
            return 'medium'
        else:
            return 'low'
    
    def get_slo_summary(self) -> Dict[str, Any]:
        """Get summary of SLO status."""
        recent_violations = [
            v for v in self.violations
            if time.time() - v['timestamp'] <= 300  # Last 5 minutes
        ]
        
        return {
            'total_slos': len(self.slos),
            'recent_violations': len(recent_violations),
            'violation_breakdown': {
                severity: len([v for v in recent_violations if v['severity'] == severity])
                for severity in ['low', 'medium', 'high', 'critical']
            },
            'slo_status': {
                slo_name: {
                    'description': slo.description,
                    'last_check': max([
                        point['timestamp'] for point in self.metrics_history[slo_name]
                    ], default=0),
                    'recent_violations': len([
                        v for v in recent_violations if v['slo_name'] == slo_name
                    ])
                }
                for slo_name, slo in self.slos.items()
            }
        }


class LoadTestMetrics:
    """
    Comprehensive metrics collection and analysis system for load testing.
    
    Collects, processes, and provides real-time access to all test metrics
    including response times, error rates, throughput, and SLO monitoring.
    """
    
    def __init__(self, 
                 buffer_size: int = 10000,
                 response_time_window: int = 1000):
        
        # Core metrics storage
        self.request_metrics_buffer = MetricsBuffer(buffer_size)
        self.response_time_tracker = ResponseTimeTracker(response_time_window)
        
        # Current state
        self.start_time = time.time()
        self.current_rps = 0.0
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
        # Error tracking
        self.error_counts = defaultdict(int)
        self.status_code_counts = defaultdict(int)
        
        # Network tracking
        self.bytes_sent = 0
        self.bytes_received = 0
        
        # Connection tracking
        self.active_connections = 0
        self.connection_errors = 0
        
        # SLO monitoring
        self.slo_monitor = SLOMonitor()
        
        # Real-time calculation state
        self.last_rps_calculation = time.time()
        self.requests_in_last_second = deque(maxlen=1000)
        
        # Lock for thread safety
        self.lock = Lock()
        
        logger.info("LoadTestMetrics initialized")
    
    def record_request(self, 
                      response_time_ms: float,
                      status_code: int,
                      bytes_sent: int = 0,
                      bytes_received: int = 0,
                      error_type: Optional[str] = None):
        """
        Record a completed request with all its metrics.
        
        Args:
            response_time_ms: Response time in milliseconds
            status_code: HTTP status code
            bytes_sent: Bytes sent in request
            bytes_received: Bytes received in response
            error_type: Type of error if request failed
        """
        current_time = time.time()
        
        with self.lock:
            # Update counters
            self.total_requests += 1
            
            if 200 <= status_code < 400:
                self.successful_requests += 1
            else:
                self.failed_requests += 1
                if error_type:
                    self.error_counts[error_type] += 1
            
            # Track status codes
            self.status_code_counts[status_code] += 1
            
            # Track network usage
            self.bytes_sent += bytes_sent
            self.bytes_received += bytes_received
            
            # Record response time
            self.response_time_tracker.add_response_time(response_time_ms)
            
            # Track for RPS calculation
            self.requests_in_last_second.append(current_time)
            
            # Update current RPS
            self._update_current_rps(current_time)
    
    def _update_current_rps(self, current_time: float):
        """Update current RPS calculation."""
        # Remove requests older than 1 second
        cutoff_time = current_time - 1.0
        while self.requests_in_last_second and self.requests_in_last_second[0] < cutoff_time:
            self.requests_in_last_second.popleft()
        
        self.current_rps = len(self.requests_in_last_second)
        self.last_rps_calculation = current_time
    
    def record_connection_event(self, event_type: str):
        """Record connection-related events."""
        with self.lock:
            if event_type == 'connection_opened':
                self.active_connections += 1
            elif event_type == 'connection_closed':
                self.active_connections = max(0, self.active_connections - 1)
            elif event_type == 'connection_error':
                self.connection_errors += 1
    
    def get_current_metrics(self) -> RequestMetrics:
        """Get current comprehensive metrics snapshot."""
        current_time = time.time()
        
        with self.lock:
            self._update_current_rps(current_time)
            
            response_time_metrics = self.response_time_tracker.get_percentiles()
            
            metrics = RequestMetrics(
                timestamp=current_time,
                total_requests=self.total_requests,
                successful_requests=self.successful_requests,
                failed_requests=self.failed_requests,
                current_rps=self.current_rps,
                response_times=response_time_metrics,
                error_counts=dict(self.error_counts),
                status_code_counts=dict(self.status_code_counts),
                bytes_sent=self.bytes_sent,
                bytes_received=self.bytes_received,
                active_connections=self.active_connections,
                connection_errors=self.connection_errors
            )
            
            # Store in buffer
            self.request_metrics_buffer.add(MetricPoint(current_time, 0, {'type': 'snapshot'}))
            
            # Check SLOs
            violations = self.slo_monitor.check_slos(metrics)
            
            return metrics
    
    def get_test_summary(self) -> Dict[str, Any]:
        """Get comprehensive test summary."""
        current_metrics = self.get_current_metrics()
        test_duration = time.time() - self.start_time
        
        # Calculate rates
        avg_rps = self.total_requests / test_duration if test_duration > 0 else 0
        error_rate = (self.failed_requests / self.total_requests * 100) if self.total_requests > 0 else 0
        
        # Calculate throughput
        throughput_mbps = ((self.bytes_sent + self.bytes_received) * 8) / (1024 * 1024 * test_duration)
        
        return {
            'test_duration': test_duration,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'error_rate': error_rate,
            'average_rps': avg_rps,
            'current_rps': self.current_rps,
            'throughput_mbps': throughput_mbps,
            'response_times': asdict(current_metrics.response_times),
            'status_codes': dict(self.status_code_counts),
            'error_breakdown': dict(self.error_counts),
            'network_usage': {
                'bytes_sent': self.bytes_sent,
                'bytes_received': self.bytes_received,
                'total_bytes': self.bytes_sent + self.bytes_received
            },
            'slo_summary': self.slo_monitor.get_slo_summary()
        }
    
    def get_time_series_data(self, 
                           metric_name: str, 
                           start_time: Optional[float] = None,
                           end_time: Optional[float] = None,
                           resolution_seconds: int = 1) -> List[Tuple[float, float]]:
        """
        Get time series data for a specific metric.
        
        Args:
            metric_name: Name of metric to retrieve
            start_time: Start time (default: test start)
            end_time: End time (default: now)
            resolution_seconds: Time resolution for aggregation
        
        Returns:
            List of (timestamp, value) tuples
        """
        if start_time is None:
            start_time = self.start_time
        if end_time is None:
            end_time = time.time()
        
        # Get raw data points
        points = self.request_metrics_buffer.get_range(start_time, end_time)
        
        # Aggregate by resolution
        aggregated = {}
        for point in points:
            bucket = int(point.timestamp / resolution_seconds) * resolution_seconds
            if bucket not in aggregated:
                aggregated[bucket] = []
            aggregated[bucket].append(point)
        
        # Calculate metric values for each bucket
        result = []
        for bucket_time in sorted(aggregated.keys()):
            bucket_points = aggregated[bucket_time]
            # For now, return count of points (this would be expanded for specific metrics)
            value = len(bucket_points)
            result.append((bucket_time, value))
        
        return result
    
    def add_slo(self, slo: SLO):
        """Add an SLO to monitor during the test."""
        self.slo_monitor.add_slo(slo)
    
    def reset(self):
        """Reset all metrics (for new test)."""
        with self.lock:
            self.start_time = time.time()
            self.current_rps = 0.0
            self.total_requests = 0
            self.successful_requests = 0
            self.failed_requests = 0
            
            self.error_counts.clear()
            self.status_code_counts.clear()
            
            self.bytes_sent = 0
            self.bytes_received = 0
            
            self.active_connections = 0
            self.connection_errors = 0
            
            self.requests_in_last_second.clear()
            
            self.request_metrics_buffer.clear()
            self.response_time_tracker = ResponseTimeTracker()
            self.slo_monitor = SLOMonitor()
        
        logger.info("Metrics reset for new test")


class MetricsDashboard:
    """
    Web-based real-time dashboard for load test monitoring.
    
    Provides a WebSocket-based interface for real-time metric streaming
    and serves an interactive web interface for test monitoring.
    """
    
    def __init__(self, 
                 metrics: LoadTestMetrics,
                 port: int = 8080,
                 host: str = "0.0.0.0"):
        
        self.metrics = metrics
        self.port = port
        self.host = host
        self.connected_clients: Set[websockets.WebSocketServerProtocol] = set()
        self.update_interval = 1.0  # Update every second
        
        logger.info(f"MetricsDashboard initialized on {host}:{port}")
    
    async def start_server(self):
        """Start the dashboard server."""
        # Start WebSocket server for real-time updates
        ws_server = await websockets.serve(
            self._handle_websocket_connection,
            self.host,
            self.port + 1  # WebSocket on port + 1
        )
        
        # Start metrics broadcasting
        asyncio.create_task(self._broadcast_metrics())
        
        logger.info(f"Dashboard WebSocket server started on {self.host}:{self.port + 1}")
        
        return ws_server
    
    async def _handle_websocket_connection(self, websocket, path):
        """Handle new WebSocket client connection."""
        self.connected_clients.add(websocket)
        logger.info(f"Dashboard client connected: {websocket.remote_address}")
        
        try:
            # Send initial data
            initial_data = {
                'type': 'initial',
                'data': self.metrics.get_test_summary()
            }
            await websocket.send(json.dumps(initial_data))
            
            # Keep connection alive
            async for message in websocket:
                # Handle client commands if needed
                try:
                    command = json.loads(message)
                    await self._handle_client_command(websocket, command)
                except json.JSONDecodeError:
                    pass  # Ignore invalid JSON
        
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.connected_clients.discard(websocket)
            logger.info(f"Dashboard client disconnected: {websocket.remote_address}")
    
    async def _handle_client_command(self, websocket, command: Dict[str, Any]):
        """Handle command from dashboard client."""
        command_type = command.get('type')
        
        if command_type == 'get_time_series':
            metric_name = command.get('metric', 'rps')
            duration = command.get('duration', 300)  # Last 5 minutes
            
            end_time = time.time()
            start_time = end_time - duration
            
            data = self.metrics.get_time_series_data(metric_name, start_time, end_time)
            
            response = {
                'type': 'time_series',
                'metric': metric_name,
                'data': data
            }
            await websocket.send(json.dumps(response))
    
    async def _broadcast_metrics(self):
        """Broadcast current metrics to all connected clients."""
        while True:
            try:
                if self.connected_clients:
                    current_metrics = self.metrics.get_current_metrics()
                    
                    broadcast_data = {
                        'type': 'metrics_update',
                        'timestamp': current_metrics.timestamp,
                        'data': {
                            'rps': current_metrics.current_rps,
                            'total_requests': current_metrics.total_requests,
                            'success_requests': current_metrics.successful_requests,
                            'error_rate': (
                                current_metrics.failed_requests / current_metrics.total_requests * 100
                                if current_metrics.total_requests > 0 else 0
                            ),
                            'avg_response_time': (
                                current_metrics.response_times.sum / current_metrics.response_times.count
                                if current_metrics.response_times.count > 0 else 0
                            ),
                            'p95_response_time': current_metrics.response_times.p95,
                            'p99_response_time': current_metrics.response_times.p99,
                            'active_connections': current_metrics.active_connections,
                            'status_codes': current_metrics.status_code_counts
                        }
                    }
                    
                    # Send to all clients
                    disconnected_clients = set()
                    for client in self.connected_clients:
                        try:
                            await client.send(json.dumps(broadcast_data))
                        except websockets.exceptions.ConnectionClosed:
                            disconnected_clients.add(client)
                    
                    # Clean up disconnected clients
                    self.connected_clients -= disconnected_clients
                
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error broadcasting metrics: {e}")
                await asyncio.sleep(self.update_interval)
    
    def get_dashboard_html(self) -> str:
        """Generate HTML for the dashboard interface."""
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>SLAYER Load Test Dashboard</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    background: #1a1a1a; 
                    color: #fff; 
                    margin: 0; 
                    padding: 20px; 
                }
                .dashboard { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
                .metric-card { 
                    background: #2a2a2a; 
                    border-radius: 8px; 
                    padding: 20px; 
                    box-shadow: 0 4px 6px rgba(0,0,0,0.3); 
                }
                .metric-title { font-size: 1.2em; margin-bottom: 10px; color: #4CAF50; }
                .metric-value { font-size: 2em; font-weight: bold; }
                .chart-container { position: relative; height: 300px; }
                .status-indicator {
                    display: inline-block;
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    margin-right: 8px;
                }
                .status-good { background-color: #4CAF50; }
                .status-warning { background-color: #FF9800; }
                .status-error { background-color: #f44336; }
                .header { text-align: center; margin-bottom: 30px; }
                .header h1 { color: #4CAF50; margin: 0; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚀 SLAYER Load Test Dashboard</h1>
                <div id="test-status">
                    <span class="status-indicator status-good"></span>
                    <span id="status-text">Test Running</span>
                </div>
            </div>
            
            <div class="dashboard">
                <div class="metric-card">
                    <div class="metric-title">Current RPS</div>
                    <div class="metric-value" id="current-rps">0</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">Total Requests</div>
                    <div class="metric-value" id="total-requests">0</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">Error Rate (%)</div>
                    <div class="metric-value" id="error-rate">0.0</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">P95 Response Time (ms)</div>
                    <div class="metric-value" id="p95-response-time">0</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">RPS Over Time</div>
                    <div class="chart-container">
                        <canvas id="rps-chart"></canvas>
                    </div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">Response Times</div>
                    <div class="chart-container">
                        <canvas id="response-time-chart"></canvas>
                    </div>
                </div>
            </div>
            
            <script>
                // WebSocket connection for real-time updates
                const ws = new WebSocket(`ws://${window.location.hostname}:${window.location.port.replace(/\\d+$/, '')}8081`);
                
                // Chart setup
                const rpsChart = new Chart(document.getElementById('rps-chart'), {
                    type: 'line',
                    data: {
                        labels: [],
                        datasets: [{
                            label: 'RPS',
                            data: [],
                            borderColor: '#4CAF50',
                            backgroundColor: 'rgba(76, 175, 80, 0.1)',
                            tension: 0.1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            y: { beginAtZero: true, ticks: { color: '#fff' } },
                            x: { ticks: { color: '#fff' } }
                        }
                    }
                });
                
                const responseTimeChart = new Chart(document.getElementById('response-time-chart'), {
                    type: 'line',
                    data: {
                        labels: [],
                        datasets: [
                            {
                                label: 'Average',
                                data: [],
                                borderColor: '#2196F3',
                                backgroundColor: 'rgba(33, 150, 243, 0.1)',
                                tension: 0.1
                            },
                            {
                                label: 'P95',
                                data: [],
                                borderColor: '#FF9800',
                                backgroundColor: 'rgba(255, 152, 0, 0.1)',
                                tension: 0.1
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: { beginAtZero: true, ticks: { color: '#fff' } },
                            x: { ticks: { color: '#fff' } }
                        },
                        plugins: { legend: { labels: { color: '#fff' } } }
                    }
                });
                
                // Handle WebSocket messages
                ws.onmessage = function(event) {
                    const message = JSON.parse(event.data);
                    
                    if (message.type === 'metrics_update') {
                        updateMetrics(message.data);
                        updateCharts(message.data, message.timestamp);
                    }
                };
                
                function updateMetrics(data) {
                    document.getElementById('current-rps').textContent = Math.round(data.rps);
                    document.getElementById('total-requests').textContent = data.total_requests.toLocaleString();
                    document.getElementById('error-rate').textContent = data.error_rate.toFixed(1);
                    document.getElementById('p95-response-time').textContent = Math.round(data.p95_response_time);
                }
                
                function updateCharts(data, timestamp) {
                    const timeLabel = new Date(timestamp * 1000).toLocaleTimeString();
                    
                    // Update RPS chart
                    rpsChart.data.labels.push(timeLabel);
                    rpsChart.data.datasets[0].data.push(data.rps);
                    
                    // Keep only last 60 data points
                    if (rpsChart.data.labels.length > 60) {
                        rpsChart.data.labels.shift();
                        rpsChart.data.datasets[0].data.shift();
                    }
                    
                    rpsChart.update('none'); // No animation for real-time
                    
                    // Update response time chart
                    responseTimeChart.data.labels.push(timeLabel);
                    responseTimeChart.data.datasets[0].data.push(data.avg_response_time);
                    responseTimeChart.data.datasets[1].data.push(data.p95_response_time);
                    
                    if (responseTimeChart.data.labels.length > 60) {
                        responseTimeChart.data.labels.shift();
                        responseTimeChart.data.datasets[0].data.shift();
                        responseTimeChart.data.datasets[1].data.shift();
                    }
                    
                    responseTimeChart.update('none');
                }
                
                ws.onerror = function(error) {
                    console.error('WebSocket error:', error);
                    document.getElementById('status-text').textContent = 'Connection Error';
                    document.querySelector('.status-indicator').className = 'status-indicator status-error';
                };
            </script>
        </body>
        </html>
        """