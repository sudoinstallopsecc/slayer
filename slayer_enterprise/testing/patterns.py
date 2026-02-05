"""
Advanced Traffic Pattern Engine for SLAYER Enterprise
===================================================

Sophisticated traffic pattern generation system that can simulate
realistic user behaviors and various load testing scenarios.

Supported patterns:
- Constant load (steady RPS)
- Ramp-up/ramp-down (gradual increase/decrease)
- Burst patterns (sudden spikes)
- Spike testing (extreme load periods)
- Realistic user behavior simulation
- Custom pattern scripts
"""

import asyncio
import json
import math
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Generator, List, Optional, Tuple, Union, Callable
import numpy as np

import logging

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Available traffic pattern types."""
    CONSTANT = "constant"
    RAMP_UP = "ramp_up"
    RAMP_DOWN = "ramp_down"
    BURST = "burst"
    SPIKE = "spike"
    STEP = "step"
    WAVE = "wave"
    REALISTIC_USER = "realistic_user"
    CUSTOM = "custom"


@dataclass
class RequestPattern:
    """Configuration for a specific request pattern phase."""
    
    name: str
    pattern_type: PatternType
    duration_seconds: int
    target_rps: int
    
    # Pattern-specific parameters
    ramp_start_rps: Optional[int] = None
    ramp_end_rps: Optional[int] = None
    burst_interval_seconds: Optional[float] = None
    burst_multiplier: Optional[float] = None
    wave_amplitude: Optional[float] = None
    wave_period_seconds: Optional[float] = None
    
    # Realistic behavior parameters
    user_session_duration: Optional[Tuple[int, int]] = None  # (min, max) seconds
    think_time_range: Optional[Tuple[float, float]] = None   # (min, max) seconds between requests
    user_arrival_rate: Optional[float] = None               # users per second
    
    # custom pattern function
    custom_function: Optional[Callable[[float], int]] = None
    
    # Request distribution
    request_methods: List[str] = field(default_factory=lambda: ["GET"])
    method_weights: List[float] = field(default_factory=lambda: [1.0])
    
    # Payload configuration
    payload_templates: List[Dict[str, Any]] = field(default_factory=list)
    payload_variables: Dict[str, List[str]] = field(default_factory=dict)


class TrafficGenerator(ABC):
    """Abstract base class for traffic generators."""
    
    @abstractmethod
    async def generate_schedule(self, pattern: RequestPattern) -> Generator[Tuple[float, Dict], None, None]:
        """
        Generate request schedule for the pattern.
        
        Yields:
            Tuple of (timestamp, request_config)
        """
        pass


class ConstantTrafficGenerator(TrafficGenerator):
    """Generate constant load traffic."""
    
    async def generate_schedule(self, pattern: RequestPattern) -> Generator[Tuple[float, Dict], None, None]:
        """Generate constant RPS traffic."""
        start_time = time.time()
        end_time = start_time + pattern.duration_seconds
        request_interval = 1.0 / pattern.target_rps if pattern.target_rps > 0 else 1.0
        
        current_time = start_time
        request_id = 0
        
        while current_time < end_time:
            request_config = {
                'method': self._select_method(pattern),
                'payload': self._generate_payload(pattern),
                'request_id': request_id,
                'scheduled_time': current_time
            }
            
            yield current_time, request_config
            current_time += request_interval
            request_id += 1
    
    def _select_method(self, pattern: RequestPattern) -> str:
        """Select HTTP method based on weights."""
        if len(pattern.request_methods) == 1:
            return pattern.request_methods[0]
        
        return random.choices(pattern.request_methods, pattern.method_weights)[0]
    
    def _generate_payload(self, pattern: RequestPattern) -> Optional[Dict]:
        """Generate request payload from templates."""
        if not pattern.payload_templates:
            return None
        
        template = random.choice(pattern.payload_templates)
        payload = template.copy()
        
        # Replace variables
        for key, value in payload.items():
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                var_name = value[2:-1]
                if var_name in pattern.payload_variables:
                    payload[key] = random.choice(pattern.payload_variables[var_name])
        
        return payload


class RampTrafficGenerator(TrafficGenerator):
    """Generate ramping traffic (up or down)."""
    
    async def generate_schedule(self, pattern: RequestPattern) -> Generator[Tuple[float, Dict], None, None]:
        """Generate ramping RPS traffic."""
        start_time = time.time()
        end_time = start_time + pattern.duration_seconds
        
        start_rps = pattern.ramp_start_rps or 0
        end_rps = pattern.ramp_end_rps or pattern.target_rps
        
        current_time = start_time
        request_id = 0
        
        while current_time < end_time:
            # Calculate current RPS based on linear ramp
            progress = (current_time - start_time) / pattern.duration_seconds
            current_rps = start_rps + (end_rps - start_rps) * progress
            
            if current_rps <= 0:
                current_time += 0.1  # Small increment when RPS is 0
                continue
            
            request_interval = 1.0 / current_rps
            
            request_config = {
                'method': self._select_method(pattern),
                'payload': self._generate_payload(pattern),
                'request_id': request_id,
                'scheduled_time': current_time,
                'current_rps': current_rps
            }
            
            yield current_time, request_config
            current_time += request_interval
            request_id += 1
    
    def _select_method(self, pattern: RequestPattern) -> str:
        """Select HTTP method based on weights."""
        return random.choices(pattern.request_methods, pattern.method_weights)[0]
    
    def _generate_payload(self, pattern: RequestPattern) -> Optional[Dict]:
        """Generate request payload from templates."""
        if not pattern.payload_templates:
            return None
        
        template = random.choice(pattern.payload_templates)
        return template.copy()


class BurstTrafficGenerator(TrafficGenerator):
    """Generate burst traffic patterns."""
    
    async def generate_schedule(self, pattern: RequestPattern) -> Generator[Tuple[float, Dict], None, None]:
        """Generate burst pattern traffic."""
        start_time = time.time()
        end_time = start_time + pattern.duration_seconds
        
        base_rps = pattern.target_rps
        burst_interval = pattern.burst_interval_seconds or 30.0
        burst_multiplier = pattern.burst_multiplier or 3.0
        
        current_time = start_time
        request_id = 0
        next_burst_time = start_time + burst_interval
        
        while current_time < end_time:
            # Determine if we're in a burst period
            time_since_burst = (current_time - next_burst_time) % burst_interval
            is_burst = time_since_burst < 5.0  # 5-second burst duration
            
            current_rps = base_rps * burst_multiplier if is_burst else base_rps
            request_interval = 1.0 / current_rps if current_rps > 0 else 1.0
            
            request_config = {
                'method': self._select_method(pattern),
                'payload': self._generate_payload(pattern),
                'request_id': request_id,
                'scheduled_time': current_time,
                'is_burst': is_burst,
                'current_rps': current_rps
            }
            
            yield current_time, request_config
            current_time += request_interval
            request_id += 1
            
            if current_time >= next_burst_time:
                next_burst_time += burst_interval
    
    def _select_method(self, pattern: RequestPattern) -> str:
        return random.choices(pattern.request_methods, pattern.method_weights)[0]
    
    def _generate_payload(self, pattern: RequestPattern) -> Optional[Dict]:
        if not pattern.payload_templates:
            return None
        return random.choice(pattern.payload_templates).copy()


class WaveTrafficGenerator(TrafficGenerator):
    """Generate wave-like traffic patterns."""
    
    async def generate_schedule(self, pattern: RequestPattern) -> Generator[Tuple[float, Dict], None, None]:
        """Generate wave pattern traffic."""
        start_time = time.time()
        end_time = start_time + pattern.duration_seconds
        
        base_rps = pattern.target_rps
        amplitude = pattern.wave_amplitude or (base_rps * 0.5)
        period = pattern.wave_period_seconds or 60.0
        
        current_time = start_time
        request_id = 0
        
        while current_time < end_time:
            # Calculate wave-based RPS
            time_offset = current_time - start_time
            wave_factor = math.sin(2 * math.pi * time_offset / period)
            current_rps = base_rps + (amplitude * wave_factor)
            current_rps = max(current_rps, 1)  # Ensure positive RPS
            
            request_interval = 1.0 / current_rps
            
            request_config = {
                'method': self._select_method(pattern),
                'payload': self._generate_payload(pattern),
                'request_id': request_id,
                'scheduled_time': current_time,
                'current_rps': current_rps,
                'wave_factor': wave_factor
            }
            
            yield current_time, request_config
            current_time += request_interval
            request_id += 1
    
    def _select_method(self, pattern: RequestPattern) -> str:
        return random.choices(pattern.request_methods, pattern.method_weights)[0]
    
    def _generate_payload(self, pattern: RequestPattern) -> Optional[Dict]:
        if not pattern.payload_templates:
            return None
        return random.choice(pattern.payload_templates).copy()


class RealisticUserTrafficGenerator(TrafficGenerator):
    """Generate realistic user behavior patterns."""
    
    def __init__(self):
        self.active_sessions = {}
        self.session_counter = 0
    
    async def generate_schedule(self, pattern: RequestPattern) -> Generator[Tuple[float, Dict], None, None]:
        """Generate realistic user traffic with sessions and think time."""
        start_time = time.time()
        end_time = start_time + pattern.duration_seconds
        
        user_arrival_rate = pattern.user_arrival_rate or 1.0
        session_duration_range = pattern.user_session_duration or (60, 300)
        think_time_range = pattern.think_time_range or (1.0, 10.0)
        
        current_time = start_time
        last_user_arrival = start_time
        
        while current_time < end_time:
            # Check if it's time for a new user session
            if current_time - last_user_arrival >= (1.0 / user_arrival_rate):
                session_id = self.session_counter
                self.session_counter += 1
                
                session_duration = random.randint(*session_duration_range)
                session_end_time = current_time + session_duration
                
                self.active_sessions[session_id] = {
                    'start_time': current_time,
                    'end_time': session_end_time,
                    'last_request_time': current_time,
                    'request_count': 0
                }
                
                last_user_arrival = current_time
            
            # Process active sessions
            sessions_to_remove = []
            for session_id, session in self.active_sessions.items():
                if current_time >= session['end_time']:
                    sessions_to_remove.append(session_id)
                    continue
                
                # Check if it's time for next request in this session
                next_request_time = session['last_request_time'] + random.uniform(*think_time_range)
                if current_time >= next_request_time:
                    request_config = {
                        'method': self._select_method(pattern),
                        'payload': self._generate_payload(pattern),
                        'session_id': session_id,
                        'session_request_count': session['request_count'],
                        'scheduled_time': current_time
                    }
                    
                    yield current_time, request_config
                    
                    session['last_request_time'] = current_time
                    session['request_count'] += 1
            
            # Clean up expired sessions
            for session_id in sessions_to_remove:
                del self.active_sessions[session_id]
            
            current_time += 0.1  # Small increment
    
    def _select_method(self, pattern: RequestPattern) -> str:
        return random.choices(pattern.request_methods, pattern.method_weights)[0]
    
    def _generate_payload(self, pattern: RequestPattern) -> Optional[Dict]:
        if not pattern.payload_templates:
            return None
        return random.choice(pattern.payload_templates).copy()


class TrafficPatternEngine:
    """
    Main engine for managing and executing traffic patterns.
    
    Coordinates multiple pattern phases and provides unified interface
    for complex load testing scenarios.
    """
    
    def __init__(self):
        self.generators = {
            PatternType.CONSTANT: ConstantTrafficGenerator(),
            PatternType.RAMP_UP: RampTrafficGenerator(),
            PatternType.RAMP_DOWN: RampTrafficGenerator(),
            PatternType.BURST: BurstTrafficGenerator(),
            PatternType.WAVE: WaveTrafficGenerator(),
            PatternType.REALISTIC_USER: RealisticUserTrafficGenerator(),
        }
        
        self.current_patterns: List[RequestPattern] = []
        self.execution_stats = {}
    
    def add_pattern(self, pattern: RequestPattern):
        """Add a pattern phase to the test plan."""
        self.current_patterns.append(pattern)
        logger.info(f"Added pattern: {pattern.name} ({pattern.pattern_type.value})")
    
    def load_pattern_from_config(self, config_path: str):
        """Load pattern configuration from JSON file."""
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        for pattern_config in config['patterns']:
            pattern = RequestPattern(
                name=pattern_config['name'],
                pattern_type=PatternType(pattern_config['type']),
                duration_seconds=pattern_config['duration'],
                target_rps=pattern_config['target_rps'],
                **{k: v for k, v in pattern_config.items() 
                   if k not in ['name', 'type', 'duration', 'target_rps']}
            )
            self.add_pattern(pattern)
    
    async def execute_patterns(self, request_callback: Callable) -> Dict[str, Any]:
        """
        Execute all configured patterns sequentially.
        
        Args:
            request_callback: Async function to call for each scheduled request
        
        Returns:
            Execution statistics
        """
        stats = {
            'total_patterns': len(self.current_patterns),
            'patterns_executed': 0,
            'total_requests_scheduled': 0,
            'total_duration': 0,
            'pattern_stats': {}
        }
        
        overall_start_time = time.time()
        
        for pattern in self.current_patterns:
            logger.info(f"Executing pattern: {pattern.name}")
            pattern_start_time = time.time()
            
            generator = self.generators.get(pattern.pattern_type)
            if not generator:
                logger.error(f"No generator for pattern type: {pattern.pattern_type}")
                continue
            
            pattern_requests = 0
            pattern_stats = {
                'requests_scheduled': 0,
                'start_time': pattern_start_time,
                'duration': pattern.duration_seconds,
                'target_rps': pattern.target_rps
            }
            
            # Execute pattern
            async for scheduled_time, request_config in generator.generate_schedule(pattern):
                # Schedule the request
                asyncio.create_task(
                    self._schedule_request(scheduled_time, request_config, request_callback)
                )
                pattern_requests += 1
                pattern_stats['requests_scheduled'] = pattern_requests
            
            # Wait for pattern duration to complete
            await asyncio.sleep(pattern.duration_seconds)
            
            pattern_stats['actual_duration'] = time.time() - pattern_start_time
            stats['pattern_stats'][pattern.name] = pattern_stats
            stats['patterns_executed'] += 1
            stats['total_requests_scheduled'] += pattern_requests
            
            logger.info(f"Pattern {pattern.name} completed: {pattern_requests} requests scheduled")
        
        stats['total_duration'] = time.time() - overall_start_time
        stats['average_rps'] = stats['total_requests_scheduled'] / stats['total_duration']
        
        return stats
    
    async def _schedule_request(self, scheduled_time: float, request_config: Dict, callback: Callable):
        """Schedule a request to be executed at the specified time."""
        current_time = time.time()
        delay = scheduled_time - current_time
        
        if delay > 0:
            await asyncio.sleep(delay)
        
        # Execute the request callback
        try:
            await callback(request_config)
        except Exception as e:
            logger.error(f"Request execution failed: {e}")
    
    def get_pattern_preview(self, pattern: RequestPattern, sample_duration: int = 60) -> List[Tuple[float, int]]:
        """
        Generate a preview of the RPS pattern over time.
        
        Args:
            pattern: Pattern to preview
            sample_duration: Duration in seconds to sample
        
        Returns:
            List of (time_offset, rps) tuples
        """
        preview = []
        generator = self.generators.get(pattern.pattern_type)
        
        if not generator or sample_duration <= 0:
            return preview
        
        # Create a temporary pattern for preview
        preview_pattern = RequestPattern(
            name="preview",
            pattern_type=pattern.pattern_type,
            duration_seconds=sample_duration,
            target_rps=pattern.target_rps,
            ramp_start_rps=pattern.ramp_start_rps,
            ramp_end_rps=pattern.ramp_end_rps,
            burst_interval_seconds=pattern.burst_interval_seconds,
            burst_multiplier=pattern.burst_multiplier,
            wave_amplitude=pattern.wave_amplitude,
            wave_period_seconds=pattern.wave_period_seconds
        )
        
        # Sample pattern
        current_rps = 0
        request_count = 0
        sample_window = 1.0  # 1 second windows
        
        base_time = time.time()
        
        # This is a simplified preview - in reality we'd need to run the async generator
        for t in range(0, sample_duration, int(sample_window)):
            time_offset = t
            
            # Calculate approximate RPS based on pattern type
            if pattern.pattern_type == PatternType.CONSTANT:
                rps = pattern.target_rps
            elif pattern.pattern_type == PatternType.RAMP_UP:
                progress = t / sample_duration
                start_rps = pattern.ramp_start_rps or 0
                end_rps = pattern.ramp_end_rps or pattern.target_rps
                rps = start_rps + (end_rps - start_rps) * progress
            elif pattern.pattern_type == PatternType.WAVE:
                amplitude = pattern.wave_amplitude or (pattern.target_rps * 0.5)
                period = pattern.wave_period_seconds or 60.0
                wave_factor = math.sin(2 * math.pi * t / period)
                rps = pattern.target_rps + (amplitude * wave_factor)
                rps = max(rps, 1)
            else:
                rps = pattern.target_rps
            
            preview.append((time_offset, int(rps)))
        
        return preview
    
    def create_standard_patterns(self) -> Dict[str, RequestPattern]:
        """Create a set of standard testing patterns."""
        return {
            'quick_constant': RequestPattern(
                name="Quick Constant Load",
                pattern_type=PatternType.CONSTANT,
                duration_seconds=60,
                target_rps=50
            ),
            'ramp_up_test': RequestPattern(
                name="Gradual Ramp Up",
                pattern_type=PatternType.RAMP_UP,
                duration_seconds=300,
                target_rps=100,
                ramp_start_rps=10,
                ramp_end_rps=100
            ),
            'spike_test': RequestPattern(
                name="Spike Test",
                pattern_type=PatternType.BURST,
                duration_seconds=120,
                target_rps=50,
                burst_interval_seconds=30,
                burst_multiplier=5
            ),
            'realistic_users': RequestPattern(
                name="Realistic User Behavior",
                pattern_type=PatternType.REALISTIC_USER,
                duration_seconds=600,
                target_rps=0,
                user_arrival_rate=2.0,
                user_session_duration=(30, 120),
                think_time_range=(2.0, 8.0)
            )
        }