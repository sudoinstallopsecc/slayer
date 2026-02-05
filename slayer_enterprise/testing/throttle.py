"""
Intelligent Throttle and Back-off System for SLAYER Enterprise
============================================================

Advanced traffic management system that automatically adjusts request rate
based on server response patterns to prevent overwhelming target systems
and maintain ethical testing practices.

Features:
- Adaptive rate limiting based on server performance
- Multiple back-off strategies (exponential, linear, custom)
- Circuit breaker pattern for automatic protection
- Health-based throttling
- Graceful degradation under load
- Configurable safety limits
"""

import asyncio
import logging
import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable
import statistics
from collections import deque

logger = logging.getLogger(__name__)


class BackoffStrategy(Enum):
    """Available back-off strategies."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIBONACCI = "fibonacci"
    CUSTOM = "custom"
    ADAPTIVE = "adaptive"


class ThrottleState(Enum):
    """Current state of the throttle system."""
    NORMAL = "normal"
    BACKING_OFF = "backing_off"
    CIRCUIT_OPEN = "circuit_open"
    RECOVERY = "recovery"
    EMERGENCY_STOP = "emergency_stop"


@dataclass
class ThrottleConfig:
    """Configuration for intelligent throttle system."""
    
    # Rate limit settings
    max_rps: int = 100
    min_rps: int = 1
    initial_rps: int = 10
    
    # Back-off triggers
    error_rate_threshold: float = 5.0  # Percentage
    response_time_threshold: float = 5000.0  # Milliseconds
    connection_error_threshold: int = 5  # Consecutive connection errors
    
    # Back-off strategy
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    backoff_multiplier: float = 2.0
    backoff_max_delay: float = 60.0  # Maximum delay in seconds
    
    # Recovery settings
    recovery_test_interval: float = 10.0  # Seconds between recovery tests
    recovery_success_threshold: int = 3  # Successful requests to consider recovery
    
    # Circuit breaker settings
    circuit_failure_threshold: int = 10  # Consecutive failures to open circuit
    circuit_timeout: float = 30.0  # Seconds before attempting recovery
    
    # Health monitoring
    health_check_interval: float = 5.0  # Seconds
    health_check_window: int = 20  # Number of recent requests to analyze
    
    # Safety limits
    absolute_max_rps: int = 1000  # Hard limit regardless of server performance
    emergency_stop_error_rate: float = 50.0  # Stop if error rate exceeds this
    
    # Adaptive settings
    adaptation_sensitivity: float = 0.3  # How quickly to adapt (0.1 = slow, 0.9 = fast)
    performance_target_p95: float = 2000.0  # Target P95 response time


@dataclass
class ServerHealthMetrics:
    """Health metrics about the target server."""
    timestamp: float
    response_time_avg: float
    response_time_p95: float
    error_rate: float
    connection_errors: int
    successful_requests: int
    failed_requests: int
    current_rps: float


class BackoffCalculator(ABC):
    """Abstract base class for back-off calculation strategies."""
    
    @abstractmethod
    def calculate_delay(self, attempt: int, base_delay: float) -> float:
        """Calculate the delay for a given attempt number."""
        pass
    
    @abstractmethod
    def calculate_new_rps(self, current_rps: float, metrics: ServerHealthMetrics) -> float:
        """Calculate new RPS based on current metrics."""
        pass


class ExponentialBackoffCalculator(BackoffCalculator):
    """Exponential back-off calculator."""
    
    def __init__(self, multiplier: float = 2.0, max_delay: float = 60.0):
        self.multiplier = multiplier
        self.max_delay = max_delay
    
    def calculate_delay(self, attempt: int, base_delay: float) -> float:
        """Calculate exponential delay."""
        delay = base_delay * (self.multiplier ** attempt)
        return min(delay, self.max_delay)
    
    def calculate_new_rps(self, current_rps: float, metrics: ServerHealthMetrics) -> float:
        """Reduce RPS exponentially when issues detected."""
        if metrics.error_rate > 10.0:
            return max(current_rps / self.multiplier, 1)
        elif metrics.response_time_p95 > 5000:
            return max(current_rps * 0.7, 1)
        return current_rps


class LinearBackoffCalculator(BackoffCalculator):
    """Linear back-off calculator."""
    
    def __init__(self, increment: float = 1.0, max_delay: float = 60.0):
        self.increment = increment
        self.max_delay = max_delay
    
    def calculate_delay(self, attempt: int, base_delay: float) -> float:
        """Calculate linear delay."""
        delay = base_delay + (attempt * self.increment)
        return min(delay, self.max_delay)
    
    def calculate_new_rps(self, current_rps: float, metrics: ServerHealthMetrics) -> float:
        """Reduce RPS linearly when issues detected."""
        if metrics.error_rate > 10.0:
            return max(current_rps - 5, 1)
        elif metrics.response_time_p95 > 5000:
            return max(current_rps - 2, 1)
        return current_rps


class FibonacciBackoffCalculator(BackoffCalculator):
    """Fibonacci sequence back-off calculator."""
    
    def __init__(self, max_delay: float = 60.0):
        self.max_delay = max_delay
        self.fibonacci_cache = [1, 1]  # Start of Fibonacci sequence
    
    def _get_fibonacci(self, n: int) -> int:
        """Get nth Fibonacci number."""
        while len(self.fibonacci_cache) <= n:
            self.fibonacci_cache.append(
                self.fibonacci_cache[-1] + self.fibonacci_cache[-2]
            )
        return self.fibonacci_cache[n]
    
    def calculate_delay(self, attempt: int, base_delay: float) -> float:
        """Calculate Fibonacci-based delay."""
        fib_value = self._get_fibonacci(min(attempt, 20))  # Cap at 20th Fibonacci number
        delay = base_delay * fib_value
        return min(delay, self.max_delay)
    
    def calculate_new_rps(self, current_rps: float, metrics: ServerHealthMetrics) -> float:
        """Adjust RPS using Fibonacci-based reduction."""
        if metrics.error_rate > 10.0:
            reduction_factor = 1 / self._get_fibonacci(3)  # Use 3rd Fibonacci number
            return max(current_rps * reduction_factor, 1)
        return current_rps


class AdaptiveBackoffCalculator(BackoffCalculator):
    """Adaptive back-off that learns from server behavior."""
    
    def __init__(self, config: ThrottleConfig):
        self.config = config
        self.performance_history = deque(maxlen=100)
        self.optimal_rps_estimate = config.initial_rps
        
    def calculate_delay(self, attempt: int, base_delay: float) -> float:
        """Calculate adaptive delay based on historical performance."""
        if len(self.performance_history) < 5:
            return base_delay * (2 ** attempt)  # Fallback to exponential
        
        # Analyze recent performance to determine appropriate delay
        recent_metrics = list(self.performance_history)[-5:]
        avg_response_time = statistics.mean(m.response_time_avg for m in recent_metrics)
        avg_error_rate = statistics.mean(m.error_rate for m in recent_metrics)
        
        # Calculate adaptive multiplier based on server stress
        stress_factor = 1.0
        if avg_response_time > self.config.performance_target_p95:
            stress_factor *= (avg_response_time / self.config.performance_target_p95)
        if avg_error_rate > 1.0:
            stress_factor *= (1 + avg_error_rate / 10.0)
        
        delay = base_delay * (stress_factor ** attempt)
        return min(delay, self.config.backoff_max_delay)
    
    def calculate_new_rps(self, current_rps: float, metrics: ServerHealthMetrics) -> float:
        """Adaptively calculate new RPS based on server performance."""
        self.performance_history.append(metrics)
        
        if len(self.performance_history) < 3:
            return current_rps  # Not enough data
        
        # Analyze trend
        recent_metrics = list(self.performance_history)[-3:]
        
        # Calculate performance score (lower is better)
        def performance_score(m: ServerHealthMetrics) -> float:
            score = 0.0
            score += m.response_time_p95 / self.config.performance_target_p95
            score += m.error_rate / 100.0
            if m.connection_errors > 0:
                score += 1.0
            return score
        
        scores = [performance_score(m) for m in recent_metrics]
        
        # Determine if performance is improving, degrading, or stable
        if len(scores) >= 3:
            trend = (scores[-1] - scores[0]) / len(scores)
            
            if trend > 0.2:  # Performance degrading
                new_rps = current_rps * (1 - self.config.adaptation_sensitivity)
            elif trend < -0.2:  # Performance improving
                new_rps = current_rps * (1 + self.config.adaptation_sensitivity * 0.5)
            else:  # Stable performance
                # Try to gradually increase if performance is good
                if scores[-1] < 1.5:  # Good performance
                    new_rps = current_rps * 1.1
                else:
                    new_rps = current_rps
            
            # Update optimal RPS estimate
            if scores[-1] < 1.0:  # Excellent performance
                self.optimal_rps_estimate = max(self.optimal_rps_estimate, current_rps)
            
            # Ensure bounds
            new_rps = max(self.config.min_rps, min(new_rps, self.config.max_rps))
            new_rps = min(new_rps, self.optimal_rps_estimate * 1.2)  # Don't exceed 120% of known optimal
            
            return new_rps
        
        return current_rps


class CircuitBreaker:
    """Circuit breaker for automatic protection against failing services."""
    
    def __init__(self, 
                 failure_threshold: int = 10,
                 recovery_timeout: float = 30.0,
                 success_threshold: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        # State
        self.state = "closed"  # closed, open, half_open
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
    
    def record_success(self):
        """Record a successful request."""
        if self.state == "half_open":
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._close()
        else:
            self.failure_count = 0
    
    def record_failure(self):
        """Record a failed request."""
        if self.state == "closed":
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self._open()
        elif self.state == "half_open":
            self._open()  # Failed recovery attempt
    
    def can_execute(self) -> bool:
        """Check if requests can be executed."""
        if self.state == "closed":
            return True
        elif self.state == "open":
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self._half_open()
                return True
            return False
        else:  # half_open
            return True
    
    def _open(self):
        """Open the circuit (block requests)."""
        self.state = "open"
        self.last_failure_time = time.time()
        self.success_count = 0
        logger.warning("Circuit breaker opened - blocking requests")
    
    def _close(self):
        """Close the circuit (allow requests)."""
        self.state = "closed"
        self.failure_count = 0
        self.success_count = 0
        logger.info("Circuit breaker closed - allowing requests")
    
    def _half_open(self):
        """Half-open the circuit (test mode)."""
        self.state = "half_open"
        self.success_count = 0
        logger.info("Circuit breaker half-open - testing recovery")


class IntelligentThrottle:
    """
    Intelligent throttling system that automatically adjusts request rate
    based on server health and performance characteristics.
    
    Implements multiple back-off strategies, circuit breaking, and adaptive
    rate limiting to ensure ethical load testing practices.
    """
    
    def __init__(self, config: ThrottleConfig):
        self.config = config
        self.current_rps = config.initial_rps
        self.target_rps = config.initial_rps
        self.state = ThrottleState.NORMAL
        
        # Back-off management
        self.backoff_attempt = 0
        self.last_backoff_time = 0.0
        
        # Health monitoring
        self.health_metrics_history = deque(maxlen=config.health_check_window)
        self.last_health_check = time.time()
        
        # Circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=config.circuit_failure_threshold,
            recovery_timeout=config.circuit_timeout
        )
        
        # Back-off calculator
        self.backoff_calculator = self._create_backoff_calculator()
        
        # Request timing
        self.request_times = deque(maxlen=1000)
        self.last_request_time = 0.0
        
        # Emergency state
        self.emergency_stop_triggered = False
        
        logger.info(f"IntelligentThrottle initialized with {config.initial_rps} RPS")
    
    def _create_backoff_calculator(self) -> BackoffCalculator:
        """Create appropriate back-off calculator based on config."""
        if self.config.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            return ExponentialBackoffCalculator(
                self.config.backoff_multiplier,
                self.config.backoff_max_delay
            )
        elif self.config.backoff_strategy == BackoffStrategy.LINEAR:
            return LinearBackoffCalculator(max_delay=self.config.backoff_max_delay)
        elif self.config.backoff_strategy == BackoffStrategy.FIBONACCI:
            return FibonacciBackoffCalculator(self.config.backoff_max_delay)
        elif self.config.backoff_strategy == BackoffStrategy.ADAPTIVE:
            return AdaptiveBackoffCalculator(self.config)
        else:
            return ExponentialBackoffCalculator(
                self.config.backoff_multiplier,
                self.config.backoff_max_delay
            )
    
    async def should_make_request(self) -> Tuple[bool, Optional[float]]:
        """
        Check if a request should be made now and calculate delay if needed.
        
        Returns:
            Tuple of (should_make_request, delay_seconds)
        """
        current_time = time.time()
        
        # Check circuit breaker first
        if not self.circuit_breaker.can_execute():
            return False, self.config.circuit_timeout
        
        # Check emergency stop
        if self.emergency_stop_triggered:
            return False, None
        
        # Check state-specific logic
        if self.state == ThrottleState.CIRCUIT_OPEN:
            return False, self.config.circuit_timeout
        
        elif self.state == ThrottleState.BACKING_OFF:
            # Check if backoff period is over
            backoff_delay = self.backoff_calculator.calculate_delay(
                self.backoff_attempt,
                1.0  # Base delay of 1 second
            )
            if current_time - self.last_backoff_time >= backoff_delay:
                self.state = ThrottleState.RECOVERY
                self.backoff_attempt = 0
                logger.info("Exiting back-off state, entering recovery")
        
        # Calculate delay based on current RPS
        if self.current_rps <= 0:
            return False, 1.0
        
        target_interval = 1.0 / self.current_rps
        
        # Check if enough time has passed since last request
        if self.last_request_time > 0:
            time_since_last = current_time - self.last_request_time
            if time_since_last < target_interval:
                delay = target_interval - time_since_last
                return False, delay
        
        # Request is allowed
        self.last_request_time = current_time
        self.request_times.append(current_time)
        
        return True, None
    
    def record_request_result(self, 
                            response_time_ms: float,
                            status_code: int,
                            error_type: Optional[str] = None):
        """
        Record the result of a request for throttle adjustment.
        
        Args:
            response_time_ms: Response time in milliseconds
            status_code: HTTP status code
            error_type: Type of error if request failed
        """
        current_time = time.time()
        
        # Update circuit breaker
        if 200 <= status_code < 400:
            self.circuit_breaker.record_success()
        else:
            self.circuit_breaker.record_failure()
        
        # Collect health metrics
        self._collect_health_metrics(response_time_ms, status_code, error_type)
        
        # Check for immediate throttling triggers
        if self._should_trigger_backoff(response_time_ms, status_code, error_type):
            self._trigger_backoff()
        
        # Periodic health assessment
        if current_time - self.last_health_check >= self.config.health_check_interval:
            self._assess_server_health()
            self.last_health_check = current_time
    
    def _collect_health_metrics(self, 
                              response_time_ms: float,
                              status_code: int,
                              error_type: Optional[str]):
        """Collect health metrics from request result."""
        # This is a simplified version - in practice, you'd maintain rolling windows
        # of various metrics and calculate proper statistics
        
        # For now, we'll approximate the metrics
        current_time = time.time()
        recent_requests = [t for t in self.request_times if current_time - t <= 10.0]
        current_rps = len(recent_requests) / 10.0 if recent_requests else 0.0
        
        # Calculate approximate error rate (simplified)
        error_rate = 0.0
        if status_code >= 400:
            error_rate = 10.0  # Simplified error rate calculation
        
        metrics = ServerHealthMetrics(
            timestamp=current_time,
            response_time_avg=response_time_ms,
            response_time_p95=response_time_ms * 1.2,  # Approximation
            error_rate=error_rate,
            connection_errors=1 if error_type and 'connection' in error_type.lower() else 0,
            successful_requests=1 if 200 <= status_code < 400 else 0,
            failed_requests=1 if status_code >= 400 else 0,
            current_rps=current_rps
        )
        
        self.health_metrics_history.append(metrics)
    
    def _should_trigger_backoff(self, 
                              response_time_ms: float,
                              status_code: int,
                              error_type: Optional[str]) -> bool:
        """Check if immediate backoff should be triggered."""
        # High response time
        if response_time_ms > self.config.response_time_threshold:
            logger.warning(f"High response time detected: {response_time_ms}ms")
            return True
        
        # Connection errors
        if error_type and 'connection' in error_type.lower():
            logger.warning("Connection error detected")
            return True
        
        # Server errors
        if status_code >= 500:
            logger.warning(f"Server error detected: {status_code}")
            return True
        
        return False
    
    def _trigger_backoff(self):
        """Trigger backoff state."""
        if self.state != ThrottleState.BACKING_OFF:
            self.state = ThrottleState.BACKING_OFF
            self.backoff_attempt += 1
            self.last_backoff_time = time.time()
            
            # Immediately reduce RPS
            self.current_rps = max(self.current_rps * 0.5, self.config.min_rps)
            
            logger.warning(f"Backoff triggered (attempt {self.backoff_attempt}), RPS reduced to {self.current_rps}")
    
    def _assess_server_health(self):
        """Assess overall server health and adjust throttling."""
        if len(self.health_metrics_history) < 3:
            return  # Not enough data
        
        recent_metrics = list(self.health_metrics_history)[-5:]  # Last 5 health checks
        
        # Calculate aggregated metrics
        avg_response_time = statistics.mean(m.response_time_avg for m in recent_metrics)
        avg_error_rate = statistics.mean(m.error_rate for m in recent_metrics)
        total_connection_errors = sum(m.connection_errors for m in recent_metrics)
        
        # Check for emergency stop conditions
        if avg_error_rate > self.config.emergency_stop_error_rate:
            self._trigger_emergency_stop(f"High error rate: {avg_error_rate}%")
            return
        
        # Check for health-based RPS adjustments
        latest_metrics = recent_metrics[-1]
        
        if self.state == ThrottleState.NORMAL:
            new_rps = self.backoff_calculator.calculate_new_rps(self.current_rps, latest_metrics)
            
            # Apply safety limits
            new_rps = max(self.config.min_rps, min(new_rps, self.config.max_rps))
            new_rps = min(new_rps, self.config.absolute_max_rps)
            
            if new_rps != self.current_rps:
                logger.info(f"Adjusting RPS from {self.current_rps} to {new_rps} based on server health")
                self.current_rps = new_rps
        
        elif self.state == ThrottleState.RECOVERY:
            # Gradual recovery - slowly increase RPS if metrics are good
            if avg_error_rate < 2.0 and avg_response_time < self.config.performance_target_p95:
                new_rps = min(self.current_rps * 1.1, self.target_rps)
                logger.info(f"Recovery: increasing RPS to {new_rps}")
                self.current_rps = new_rps
                
                if new_rps >= self.target_rps * 0.9:
                    self.state = ThrottleState.NORMAL
                    logger.info("Recovery complete, returning to normal state")
    
    def _trigger_emergency_stop(self, reason: str):
        """Trigger emergency stop."""
        self.emergency_stop_triggered = True
        self.state = ThrottleState.EMERGENCY_STOP
        self.current_rps = 0
        
        logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}")
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current throttle state and metrics."""
        return {
            'state': self.state.value,
            'current_rps': self.current_rps,
            'target_rps': self.target_rps,
            'backoff_attempt': self.backoff_attempt,
            'circuit_breaker_state': self.circuit_breaker.state,
            'emergency_stop': self.emergency_stop_triggered,
            'health_metrics_count': len(self.health_metrics_history),
            'last_health_check': self.last_health_check
        }
    
    def set_target_rps(self, target_rps: int):
        """Set new target RPS (subject to safety limits)."""
        target_rps = max(self.config.min_rps, min(target_rps, self.config.max_rps))
        target_rps = min(target_rps, self.config.absolute_max_rps)
        
        self.target_rps = target_rps
        
        if not self.emergency_stop_triggered:
            # Gradually adjust current RPS towards target
            if self.state == ThrottleState.NORMAL:
                self.current_rps = target_rps
        
        logger.info(f"Target RPS set to {target_rps}")
    
    def reset_emergency_stop(self):
        """Reset emergency stop (manual intervention required)."""
        if self.emergency_stop_triggered:
            self.emergency_stop_triggered = False
            self.state = ThrottleState.RECOVERY
            self.current_rps = self.config.min_rps
            self.backoff_attempt = 0
            
            logger.info("Emergency stop reset - starting recovery mode")
    
    def get_recommended_delay(self) -> float:
        """Get recommended delay before next request."""
        if self.current_rps <= 0:
            return 1.0
        return 1.0 / self.current_rps
    
    def create_standard_slos(self) -> List:
        """Create standard SLOs for monitoring.""" 
        from .metrics import SLO
        
        return [
            SLO(
                name="response_time_p95",
                metric_name="response_time_p95",
                threshold=self.config.performance_target_p95,
                operator="lt",
                window_seconds=60,
                description="95th percentile response time should be under target"
            ),
            SLO(
                name="error_rate",
                metric_name="error_rate",
                threshold=self.config.error_rate_threshold,
                operator="lt",
                window_seconds=30,
                description="Error rate should be under threshold"
            ),
            SLO(
                name="min_rps",
                metric_name="current_rps",
                threshold=self.config.min_rps,
                operator="ge",
                window_seconds=10,
                description="RPS should not drop below minimum"
            )
        ]