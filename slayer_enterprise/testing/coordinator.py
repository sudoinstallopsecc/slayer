"""
Distributed Coordinator for SLAYER Enterprise
============================================

Advanced distributed testing system that coordinates load testing
across multiple nodes for maximum scalability and realistic traffic generation.

Key Features:
- Master-worker architecture with automatic failover
- Real-time coordination and synchronization
- Load balancing across available nodes
- Distributed metrics aggregation
- Fault tolerance and recovery
- Dynamic scaling (add/remove workers during test)
"""

import asyncio
import json
import socket
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
import logging
import websockets
import aioredis
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class NodeRole(Enum):
    """Role of a node in the distributed system."""
    MASTER = "master"
    WORKER = "worker"
    OBSERVER = "observer"


class NodeStatus(Enum):
    """Status of a node in the cluster."""
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    DISCONNECTED = "disconnected"


class MessageType(Enum):
    """Types of messages exchanged between nodes."""
    HANDSHAKE = "handshake"
    HEARTBEAT = "heartbeat"
    COMMAND = "command"
    STATUS_UPDATE = "status_update"
    METRICS = "metrics"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class NodeInfo:
    """Information about a cluster node."""
    node_id: str
    role: NodeRole
    status: NodeStatus
    address: str
    port: int
    capabilities: Dict[str, Any]
    last_heartbeat: float
    connection_time: float
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestCommand:
    """Command to execute test on worker nodes."""
    command_id: str
    test_config: Dict[str, Any]
    target_url: str
    assigned_nodes: List[str]
    total_rps: int
    duration_seconds: int
    pattern_config: Dict[str, Any]
    coordination_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClusterMessage:
    """Message format for cluster communication."""
    message_id: str
    message_type: MessageType
    sender_id: str
    timestamp: float
    data: Dict[str, Any]
    signature: Optional[str] = None


class MessageSecurity:
    """Handle message encryption and authentication."""
    
    def __init__(self, secret_key: Optional[bytes] = None):
        if secret_key:
            self.cipher = Fernet(secret_key)
        else:
            # Generate a new key (in production, share this securely)
            self.cipher = Fernet(Fernet.generate_key())
        self.enabled = True
    
    def encrypt_message(self, message: ClusterMessage) -> str:
        """Encrypt a cluster message."""
        if not self.enabled:
            return json.dumps(asdict(message))
        
        message_json = json.dumps(asdict(message))
        encrypted = self.cipher.encrypt(message_json.encode())
        return encrypted.decode()
    
    def decrypt_message(self, encrypted_data: str) -> ClusterMessage:
        """Decrypt a cluster message."""
        if not self.enabled:
            data = json.loads(encrypted_data)
            return ClusterMessage(**data)
        
        try:
            decrypted = self.cipher.decrypt(encrypted_data.encode())
            data = json.loads(decrypted.decode())
            return ClusterMessage(**data)
        except Exception as e:
            raise ValueError(f"Failed to decrypt message: {e}")


class ClusterMetrics:
    """Aggregate and manage cluster-wide metrics."""
    
    def __init__(self):
        self.node_metrics: Dict[str, Dict] = {}
        self.aggregated_metrics = {}
        self.last_update = time.time()
    
    def update_node_metrics(self, node_id: str, metrics: Dict[str, Any]):
        """Update metrics for a specific node."""
        self.node_metrics[node_id] = {
            **metrics,
            'timestamp': time.time(),
            'node_id': node_id
        }
        self._recalculate_aggregates()
    
    def _recalculate_aggregates(self):
        """Recalculate cluster-wide aggregate metrics."""
        if not self.node_metrics:
            return
        
        # Sum request counts
        total_requests = sum(
            metrics.get('total_requests', 0) 
            for metrics in self.node_metrics.values()
        )
        
        # Sum successful requests
        total_success = sum(
            metrics.get('successful_requests', 0)
            for metrics in self.node_metrics.values()
        )
        
        # Calculate average response times (weighted by request count)
        weighted_response_times = []
        total_weight = 0
        for metrics in self.node_metrics.values():
            avg_response_time = metrics.get('avg_response_time', 0)
            weight = metrics.get('total_requests', 0)
            if weight > 0:
                weighted_response_times.append(avg_response_time * weight)
                total_weight += weight
        
        avg_response_time = sum(weighted_response_times) / total_weight if total_weight > 0 else 0
        
        # Calculate current RPS across all nodes
        current_time = time.time()
        current_rps = sum(
            metrics.get('current_rps', 0)
            for metrics in self.node_metrics.values()
        )
        
        # Error rate
        error_rate = ((total_requests - total_success) / total_requests * 100) if total_requests > 0 else 0
        
        self.aggregated_metrics = {
            'total_requests': total_requests,
            'successful_requests': total_success,
            'error_rate': error_rate,
            'avg_response_time': avg_response_time,
            'current_rps': current_rps,
            'active_nodes': len(self.node_metrics),
            'last_update': current_time
        }
        
        self.last_update = current_time
    
    def get_cluster_summary(self) -> Dict[str, Any]:
        """Get summary of cluster performance."""
        return {
            'aggregated': self.aggregated_metrics,
            'nodes': {
                node_id: {
                    'requests': metrics.get('total_requests', 0),
                    'rps': metrics.get('current_rps', 0),
                    'errors': metrics.get('error_count', 0),
                    'last_update': metrics.get('timestamp', 0)
                }
                for node_id, metrics in self.node_metrics.items()
            }
        }


class DistributedCoordinator:
    """
    Master coordinator for distributed load testing.
    
    Manages a cluster of worker nodes, distributes load, and aggregates results.
    Provides fault tolerance, automatic scaling, and real-time coordination.
    """
    
    def __init__(self, 
                 node_id: Optional[str] = None,
                 bind_address: str = "0.0.0.0",
                 bind_port: int = 8765,
                 redis_url: Optional[str] = None,
                 security_key: Optional[bytes] = None):
        
        self.node_id = node_id or f"master-{uuid.uuid4().hex[:8]}"
        self.bind_address = bind_address
        self.bind_port = bind_port
        self.role = NodeRole.MASTER
        self.status = NodeStatus.INITIALIZING
        
        # Cluster state
        self.nodes: Dict[str, NodeInfo] = {}
        self.active_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.metrics = ClusterMetrics()
        self.security = MessageSecurity(security_key)
        
        # Test coordination
        self.active_tests: Dict[str, TestCommand] = {}
        self.test_results: Dict[str, Dict] = {}
        
        # Redis for persistent coordination data
        self.redis_client = None
        if redis_url:
            self.redis_url = redis_url
        
        # Event callbacks
        self.on_node_connected: Optional[Callable] = None
        self.on_node_disconnected: Optional[Callable] = None
        self.on_test_started: Optional[Callable] = None
        self.on_test_completed: Optional[Callable] = None
        
        logger.info(f"Distributed coordinator initialized: {self.node_id}")
    
    async def start(self):
        """Start the coordinator server."""
        self.status = NodeStatus.READY
        
        # Connect to Redis if configured
        if hasattr(self, 'redis_url'):
            try:
                self.redis_client = await aioredis.from_url(self.redis_url)
                logger.info("Connected to Redis for coordination data")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
        
        # Start WebSocket server
        server = await websockets.serve(
            self._handle_connection,
            self.bind_address,
            self.bind_port
        )
        
        # Start background tasks
        asyncio.create_task(self._heartbeat_monitor())
        asyncio.create_task(self._metrics_aggregator())
        
        logger.info(f"Coordinator server started on {self.bind_address}:{self.bind_port}")
        
        return server
    
    async def _handle_connection(self, websocket, path):
        """Handle new WebSocket connection from worker node."""
        node_id = None
        try:
            # Perform handshake
            node_id = await self._perform_handshake(websocket)
            if node_id:
                self.active_connections[node_id] = websocket
                logger.info(f"Node connected: {node_id}")
                
                if self.on_node_connected:
                    await self.on_node_connected(node_id, self.nodes[node_id])
                
                # Handle messages from this node
                async for message in websocket:
                    await self._handle_node_message(node_id, message)
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Node disconnected: {node_id}")
        except Exception as e:
            logger.error(f"Connection error with {node_id}: {e}")
        finally:
            if node_id:
                await self._handle_node_disconnect(node_id)
    
    async def _perform_handshake(self, websocket) -> Optional[str]:
        """Perform handshake with connecting node."""
        try:
            # Wait for handshake message
            message_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            message = self.security.decrypt_message(message_data)
            
            if message.message_type != MessageType.HANDSHAKE:
                await websocket.close(code=4000, reason="Invalid handshake")
                return None
            
            node_info = NodeInfo(
                node_id=message.data['node_id'],
                role=NodeRole(message.data['role']),
                status=NodeStatus.READY,
                address=message.data['address'],
                port=message.data.get('port', 0),
                capabilities=message.data.get('capabilities', {}),
                last_heartbeat=time.time(),
                connection_time=time.time()
            )
            
            # Store node info
            self.nodes[node_info.node_id] = node_info
            
            # Send handshake response
            response = ClusterMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.HANDSHAKE,
                sender_id=self.node_id,
                timestamp=time.time(),
                data={
                    'status': 'accepted',
                    'coordinator_id': self.node_id,
                    'cluster_config': self._get_cluster_config()
                }
            )
            
            await websocket.send(self.security.encrypt_message(response))
            
            logger.info(f"Handshake completed with {node_info.node_id}")
            return node_info.node_id
            
        except Exception as e:
            logger.error(f"Handshake failed: {e}")
            await websocket.close(code=4001, reason="Handshake failed")
            return None
    
    async def _handle_node_message(self, node_id: str, message_data: str):
        """Handle message from worker node."""
        try:
            message = self.security.decrypt_message(message_data)
            
            # Update last heartbeat
            if node_id in self.nodes:
                self.nodes[node_id].last_heartbeat = time.time()
            
            if message.message_type == MessageType.HEARTBEAT:
                await self._handle_heartbeat(node_id, message)
            
            elif message.message_type == MessageType.STATUS_UPDATE:
                await self._handle_status_update(node_id, message)
            
            elif message.message_type == MessageType.METRICS:
                await self._handle_metrics_update(node_id, message)
            
            elif message.message_type == MessageType.ERROR:
                await self._handle_node_error(node_id, message)
            
            else:
                logger.warning(f"Unknown message type from {node_id}: {message.message_type}")
                
        except Exception as e:
            logger.error(f"Failed to handle message from {node_id}: {e}")
    
    async def _handle_heartbeat(self, node_id: str, message: ClusterMessage):
        """Handle heartbeat from worker node."""
        if node_id in self.nodes:
            self.nodes[node_id].last_heartbeat = time.time()
            
            # Update node status if provided
            if 'status' in message.data:
                self.nodes[node_id].status = NodeStatus(message.data['status'])
    
    async def _handle_status_update(self, node_id: str, message: ClusterMessage):
        """Handle status update from worker node."""
        if node_id in self.nodes:
            status_data = message.data
            self.nodes[node_id].status = NodeStatus(status_data.get('status', 'ready'))
            
            # Update node capabilities if provided
            if 'capabilities' in status_data:
                self.nodes[node_id].capabilities.update(status_data['capabilities'])
    
    async def _handle_metrics_update(self, node_id: str, message: ClusterMessage):
        """Handle metrics update from worker node."""
        metrics_data = message.data
        self.metrics.update_node_metrics(node_id, metrics_data)
    
    async def _handle_node_error(self, node_id: str, message: ClusterMessage):
        """Handle error report from worker node."""
        error_data = message.data
        logger.error(f"Node {node_id} reported error: {error_data}")
        
        # Update node status
        if node_id in self.nodes:
            self.nodes[node_id].status = NodeStatus.ERROR
    
    async def _handle_node_disconnect(self, node_id: str):
        """Handle node disconnection."""
        if node_id in self.active_connections:
            del self.active_connections[node_id]
        
        if node_id in self.nodes:
            self.nodes[node_id].status = NodeStatus.DISCONNECTED
            
            if self.on_node_disconnected:
                await self.on_node_disconnected(node_id, self.nodes[node_id])
    
    async def _heartbeat_monitor(self):
        """Monitor node heartbeats and detect failed nodes."""
        while True:
            try:
                current_time = time.time()
                heartbeat_timeout = 30.0  # 30 seconds
                
                disconnected_nodes = []
                for node_id, node_info in self.nodes.items():
                    if (current_time - node_info.last_heartbeat) > heartbeat_timeout:
                        if node_info.status != NodeStatus.DISCONNECTED:
                            logger.warning(f"Node {node_id} heartbeat timeout")
                            node_info.status = NodeStatus.DISCONNECTED
                            disconnected_nodes.append(node_id)
                
                # Clean up disconnected nodes from active connections
                for node_id in disconnected_nodes:
                    if node_id in self.active_connections:
                        try:
                            await self.active_connections[node_id].close()
                        except:
                            pass
                        del self.active_connections[node_id]
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Heartbeat monitor error: {e}")
                await asyncio.sleep(10)
    
    async def _metrics_aggregator(self):
        """Periodically aggregate metrics from all nodes."""
        while True:
            try:
                # Metrics are updated in real-time when received
                # This task can perform additional processing if needed
                
                # Store metrics in Redis if available
                if self.redis_client:
                    try:
                        metrics_data = self.metrics.get_cluster_summary()
                        await self.redis_client.setex(
                            f"cluster_metrics:{self.node_id}",
                            60,  # Expire after 60 seconds
                            json.dumps(metrics_data)
                        )
                    except Exception as e:
                        logger.warning(f"Failed to store metrics in Redis: {e}")
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                logger.error(f"Metrics aggregator error: {e}")
                await asyncio.sleep(5)
    
    async def start_distributed_test(self, test_config: Dict[str, Any]) -> str:
        """
        Start a distributed load test across available nodes.
        
        Args:
            test_config: Test configuration including target, patterns, etc.
        
        Returns:
            Test ID for tracking
        """
        test_id = str(uuid.uuid4())
        
        # Get available worker nodes
        available_nodes = [
            node_id for node_id, node_info in self.nodes.items()
            if (node_info.role == NodeRole.WORKER and 
                node_info.status == NodeStatus.READY and
                node_id in self.active_connections)
        ]
        
        if not available_nodes:
            raise ValueError("No worker nodes available for test execution")
        
        # Distribute load across nodes
        total_rps = test_config.get('target_rps', 100)
        rps_per_node = total_rps // len(available_nodes)
        remaining_rps = total_rps % len(available_nodes)
        
        # Create test command
        test_command = TestCommand(
            command_id=test_id,
            test_config=test_config,
            target_url=test_config['target_url'],
            assigned_nodes=available_nodes,
            total_rps=total_rps,
            duration_seconds=test_config.get('duration', 60),
            pattern_config=test_config.get('pattern', {}),
            coordination_data={
                'start_time': time.time() + 10,  # Start in 10 seconds
                'sync_interval': 5,  # Sync every 5 seconds
            }
        )
        
        self.active_tests[test_id] = test_command
        
        # Send commands to worker nodes
        for i, node_id in enumerate(available_nodes):
            node_rps = rps_per_node
            if i == 0:  # First node gets the remainder
                node_rps += remaining_rps
            
            node_test_config = test_config.copy()
            node_test_config['target_rps'] = node_rps
            node_test_config['node_assignment'] = {
                'node_id': node_id,
                'assigned_rps': node_rps,
                'total_nodes': len(available_nodes),
                'node_index': i
            }
            
            command_message = ClusterMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.COMMAND,
                sender_id=self.node_id,
                timestamp=time.time(),
                data={
                    'command': 'start_test',
                    'test_id': test_id,
                    'test_config': node_test_config,
                    'coordination': test_command.coordination_data
                }
            )
            
            try:
                await self.active_connections[node_id].send(
                    self.security.encrypt_message(command_message)
                )
                logger.info(f"Test command sent to {node_id}: {node_rps} RPS")
            except Exception as e:
                logger.error(f"Failed to send test command to {node_id}: {e}")
        
        if self.on_test_started:
            await self.on_test_started(test_id, test_command)
        
        logger.info(f"Distributed test started: {test_id} with {len(available_nodes)} nodes")
        return test_id
    
    async def stop_test(self, test_id: str):
        """Stop a running distributed test."""
        if test_id not in self.active_tests:
            raise ValueError(f"Test {test_id} not found")
        
        test_command = self.active_tests[test_id]
        
        # Send stop commands to all assigned nodes
        stop_message = ClusterMessage(
            message_id=str(uuid.uuid4()),
            message_type=MessageType.COMMAND,
            sender_id=self.node_id,
            timestamp=time.time(),
            data={
                'command': 'stop_test',
                'test_id': test_id
            }
        )
        
        for node_id in test_command.assigned_nodes:
            if node_id in self.active_connections:
                try:
                    await self.active_connections[node_id].send(
                        self.security.encrypt_message(stop_message)
                    )
                except Exception as e:
                    logger.error(f"Failed to send stop command to {node_id}: {e}")
        
        # Clean up test
        del self.active_tests[test_id]
        
        if self.on_test_completed:
            await self.on_test_completed(test_id, test_command)
        
        logger.info(f"Distributed test stopped: {test_id}")
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get current cluster status and metrics."""
        return {
            'coordinator_id': self.node_id,
            'status': self.status.value,
            'nodes': {
                node_id: {
                    'role': node_info.role.value,
                    'status': node_info.status.value,
                    'address': node_info.address,
                    'capabilities': node_info.capabilities,
                    'last_heartbeat': node_info.last_heartbeat,
                    'connected': node_id in self.active_connections
                }
                for node_id, node_info in self.nodes.items()
            },
            'active_tests': list(self.active_tests.keys()),
            'metrics': self.metrics.get_cluster_summary()
        }
    
    def _get_cluster_config(self) -> Dict[str, Any]:
        """Get cluster configuration for worker nodes."""
        return {
            'coordinator_id': self.node_id,
            'heartbeat_interval': 10,
            'metrics_interval': 5,
            'max_rps_per_node': 1000,
            'security_enabled': self.security.enabled
        }


class TestCoordinator:
    """
    Simplified coordinator for single-node testing with room for expansion.
    """
    
    def __init__(self, node_id: Optional[str] = None):
        self.node_id = node_id or f"test-coordinator-{uuid.uuid4().hex[:8]}"
        self.active_tests: Dict[str, Dict] = {}
        self.test_metrics: Dict[str, Dict] = {}
        
    async def start_test(self, test_config: Dict[str, Any]) -> str:
        """Start a single-node test."""
        test_id = str(uuid.uuid4())
        
        self.active_tests[test_id] = {
            'config': test_config,
            'start_time': time.time(),
            'status': 'running'
        }
        
        logger.info(f"Single-node test started: {test_id}")
        return test_id
    
    def stop_test(self, test_id: str):
        """Stop a test."""
        if test_id in self.active_tests:
            self.active_tests[test_id]['status'] = 'stopped'
            self.active_tests[test_id]['end_time'] = time.time()
    
    def get_test_status(self, test_id: str) -> Optional[Dict]:
        """Get status of a specific test."""
        return self.active_tests.get(test_id)