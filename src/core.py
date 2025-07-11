"""
Core Network Automation Engine
Manages the entire automation pipeline with advanced features
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import aiohttp
import aiofiles
from concurrent.futures import ThreadPoolExecutor
import hashlib
import time

from .request_builder import RequestBuilder
from .request_sender import RequestSender
from .queue_manager import QueueManager
from .monitor import NetworkMonitor
from .exceptions import NetworkAutomationError


class RequestPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


@dataclass
class AutomationConfig:
    """Configuration for the network automation system"""
    max_concurrent_requests: int = 50
    request_timeout: int = 30
    retry_count: int = 3
    retry_delay: float = 1.0
    rate_limit_per_second: int = 100
    enable_monitoring: bool = True
    enable_caching: bool = True
    cache_ttl: int = 3600
    log_level: str = "INFO"
    webhook_url: Optional[str] = None
    custom_headers: Dict[str, str] = field(default_factory=dict)


class NetworkAutomation:
    """
    Main network automation orchestrator with advanced features:
    - Asynchronous request handling
    - Priority-based queue management
    - Real-time monitoring and metrics
    - Intelligent retry mechanisms
    - Request caching and deduplication
    - Webhook notifications
    - Circuit breaker pattern
    """

    def __init__(self, config: Optional[AutomationConfig] = None):
        self.config = config or AutomationConfig()
        self.setup_logging()
        
        self.request_builder = RequestBuilder()
        self.request_sender = RequestSender(self.config)
        self.queue_manager = QueueManager(max_size=1000)
        self.monitor = NetworkMonitor() if self.config.enable_monitoring else None
        
        self._cache = {}
        self._circuit_breakers = {}
        self._running = False
        self._tasks = []
        self._executor = ThreadPoolExecutor(max_workers=10)
        
        self.logger.info("Network Automation System initialized")

    def setup_logging(self):
        """Configure logging system"""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, self.config.log_level))
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    async def start(self):
        """Start the automation system"""
        if self._running:
            self.logger.warning("System already running")
            return
        
        self._running = True
        self.logger.info("Starting Network Automation System")
        
        # Start background tasks
        self._tasks = [
            asyncio.create_task(self._process_queue()),
            asyncio.create_task(self._monitor_system()),
            asyncio.create_task(self._cleanup_cache()),
            asyncio.create_task(self._health_check())
        ]
        
        if self.monitor:
            await self.monitor.start()

    async def stop(self):
        """Stop the automation system gracefully"""
        self.logger.info("Stopping Network Automation System")
        self._running = False
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        await asyncio.gather(*self._tasks, return_exceptions=True)
        
        if self.monitor:
            await self.monitor.stop()
        
        self._executor.shutdown(wait=True)
        self.logger.info("System stopped")

    async def add_request(
        self, 
        request_data: Dict[str, Any],
        priority: RequestPriority = RequestPriority.NORMAL,
        callback: Optional[Callable] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a request to the automation queue
        
        Args:
            request_data: Request configuration
            priority: Request priority level
            callback: Optional callback function
            metadata: Additional metadata
            
        Returns:
            Request ID
        """
        request_id = self._generate_request_id(request_data)
        
        # Check cache if enabled
        if self.config.enable_caching:
            cached_result = self._get_cached_result(request_id)
            if cached_result:
                self.logger.info(f"Returning cached result for {request_id}")
                if callback:
                    await callback(cached_result)
                return request_id
        
        # Build the request
        built_request = self.request_builder.build(request_data)
        
        # Add to queue
        queue_item = {
            "id": request_id,
            "request": built_request,
            "priority": priority,
            "callback": callback,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
            "attempts": 0
        }
        
        await self.queue_manager.add(queue_item, priority)
        
        self.logger.info(f"Request {request_id} added to queue with priority {priority.name}")
        
        if self.monitor:
            await self.monitor.record_request_queued(request_id)
        
        return request_id

    async def add_batch_requests(
        self,
        requests: List[Dict[str, Any]],
        priority: RequestPriority = RequestPriority.NORMAL,
        batch_callback: Optional[Callable] = None
    ) -> List[str]:
        """Add multiple requests as a batch"""
        request_ids = []
        
        for request_data in requests:
            request_id = await self.add_request(
                request_data,
                priority,
                metadata={"batch": True}
            )
            request_ids.append(request_id)
        
        if batch_callback:
            asyncio.create_task(
                self._handle_batch_callback(request_ids, batch_callback)
            )
        
        return request_ids

    async def _process_queue(self):
        """Main queue processing loop"""
        semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        
        while self._running:
            try:
                # Rate limiting
                await self._rate_limit()
                
                # Get next item from queue
                item = await self.queue_manager.get()
                if not item:
                    await asyncio.sleep(0.1)
                    continue
                
                # Process request concurrently
                asyncio.create_task(
                    self._process_request(item, semaphore)
                )
                
            except Exception as e:
                self.logger.error(f"Queue processing error: {e}")
                await asyncio.sleep(1)

    async def _process_request(self, item: Dict[str, Any], semaphore: asyncio.Semaphore):
        """Process a single request with retry logic"""
        async with semaphore:
            request_id = item["id"]
            endpoint = item["request"].get("url", "").split("?")[0]
            
            # Check circuit breaker
            if self._is_circuit_open(endpoint):
                self.logger.warning(f"Circuit breaker open for {endpoint}")
                await self._handle_request_failure(item, "Circuit breaker open")
                return
            
            try:
                # Send request with retries
                result = await self._send_with_retry(item)
                
                # Cache result if enabled
                if self.config.enable_caching and result.get("success"):
                    self._cache_result(request_id, result)
                
                # Handle callback
                if item.get("callback"):
                    await item["callback"](result)
                
                # Update metrics
                if self.monitor:
                    await self.monitor.record_request_completed(
                        request_id,
                        success=result.get("success", False),
                        duration=result.get("duration", 0)
                    )
                
                # Send webhook notification if configured
                if self.config.webhook_url:
                    await self._send_webhook_notification(item, result)
                
                # Update circuit breaker
                self._update_circuit_breaker(endpoint, success=True)
                
            except Exception as e:
                self.logger.error(f"Request {request_id} failed: {e}")
                await self._handle_request_failure(item, str(e))
                self._update_circuit_breaker(endpoint, success=False)

    async def _send_with_retry(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Send request with retry mechanism"""
        last_error = None
        
        for attempt in range(self.config.retry_count):
            try:
                item["attempts"] = attempt + 1
                
                # Exponential backoff
                if attempt > 0:
                    delay = self.config.retry_delay * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)
                
                # Send request
                result = await self.request_sender.send(item["request"])
                
                if result.get("success"):
                    return result
                
                last_error = result.get("error", "Unknown error")
                
            except Exception as e:
                last_error = str(e)
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
        
        raise NetworkAutomationError(f"All retry attempts failed: {last_error}")

    async def _handle_request_failure(self, item: Dict[str, Any], error: str):
        """Handle failed requests"""
        result = {
            "success": False,
            "error": error,
            "request_id": item["id"],
            "attempts": item.get("attempts", 0)
        }
        
        if item.get("callback"):
            await item["callback"](result)
        
        if self.monitor:
            await self.monitor.record_request_failed(item["id"], error)

    async def _rate_limit(self):
        """Implement rate limiting"""
        # Simple token bucket algorithm
        if not hasattr(self, "_rate_limiter"):
            self._rate_limiter = {
                "tokens": self.config.rate_limit_per_second,
                "last_update": time.time()
            }
        
        current_time = time.time()
        time_passed = current_time - self._rate_limiter["last_update"]
        
        # Refill tokens
        self._rate_limiter["tokens"] = min(
            self.config.rate_limit_per_second,
            self._rate_limiter["tokens"] + time_passed * self.config.rate_limit_per_second
        )
        self._rate_limiter["last_update"] = current_time
        
        # Wait if no tokens available
        if self._rate_limiter["tokens"] < 1:
            wait_time = (1 - self._rate_limiter["tokens"]) / self.config.rate_limit_per_second
            await asyncio.sleep(wait_time)
            self._rate_limiter["tokens"] = 0
        else:
            self._rate_limiter["tokens"] -= 1

    def _is_circuit_open(self, endpoint: str) -> bool:
        """Check if circuit breaker is open for an endpoint"""
        breaker = self._circuit_breakers.get(endpoint, {})
        
        if breaker.get("state") == "open":
            # Check if cool-down period has passed
            if time.time() - breaker.get("opened_at", 0) > 60:  # 1 minute cool-down
                self._circuit_breakers[endpoint]["state"] = "half-open"
                return False
            return True
        
        return False

    def _update_circuit_breaker(self, endpoint: str, success: bool):
        """Update circuit breaker state"""
        if endpoint not in self._circuit_breakers:
            self._circuit_breakers[endpoint] = {
                "state": "closed",
                "failures": 0,
                "successes": 0,
                "threshold": 5
            }
        
        breaker = self._circuit_breakers[endpoint]
        
        if success:
            breaker["successes"] += 1
            if breaker["state"] == "half-open" and breaker["successes"] > 3:
                breaker["state"] = "closed"
                breaker["failures"] = 0
        else:
            breaker["failures"] += 1
            if breaker["failures"] >= breaker["threshold"]:
                breaker["state"] = "open"
                breaker["opened_at"] = time.time()
                self.logger.warning(f"Circuit breaker opened for {endpoint}")

    async def _monitor_system(self):
        """Monitor system health and performance"""
        while self._running:
            try:
                if self.monitor:
                    metrics = await self.monitor.get_metrics()
                    
                    # Log important metrics
                    if metrics.get("queue_size", 0) > 500:
                        self.logger.warning(f"Queue size high: {metrics['queue_size']}")
                    
                    if metrics.get("error_rate", 0) > 0.1:
                        self.logger.warning(f"High error rate: {metrics['error_rate']:.2%}")
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")

    async def _cleanup_cache(self):
        """Periodically clean up expired cache entries"""
        while self._running:
            try:
                current_time = time.time()
                expired_keys = [
                    key for key, value in self._cache.items()
                    if current_time - value.get("timestamp", 0) > self.config.cache_ttl
                ]
                
                for key in expired_keys:
                    del self._cache[key]
                
                if expired_keys:
                    self.logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
                
                await asyncio.sleep(300)  # Clean every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Cache cleanup error: {e}")

    async def _health_check(self):
        """Perform periodic health checks"""
        while self._running:
            try:
                health_status = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": "healthy",
                    "queue_size": self.queue_manager.size(),
                    "cache_size": len(self._cache),
                    "open_circuits": sum(1 for b in self._circuit_breakers.values() if b.get("state") == "open")
                }
                
                # Write health status to file
                async with aiofiles.open("/Users/emrekocay/network_automation_sender/logs/health.json", "w") as f:
                    await f.write(json.dumps(health_status, indent=2))
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Health check error: {e}")

    async def _send_webhook_notification(self, item: Dict[str, Any], result: Dict[str, Any]):
        """Send webhook notification for completed requests"""
        try:
            webhook_data = {
                "request_id": item["id"],
                "timestamp": datetime.utcnow().isoformat(),
                "priority": item["priority"].name,
                "success": result.get("success", False),
                "duration": result.get("duration", 0),
                "metadata": item.get("metadata", {})
            }
            
            async with aiohttp.ClientSession() as session:
                await session.post(
                    self.config.webhook_url,
                    json=webhook_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                )
                
        except Exception as e:
            self.logger.error(f"Webhook notification failed: {e}")

    async def _handle_batch_callback(self, request_ids: List[str], callback: Callable):
        """Handle callback for batch requests"""
        results = {}
        
        # Wait for all requests to complete
        while len(results) < len(request_ids):
            await asyncio.sleep(0.5)
            # Check completed requests (would need to implement tracking)
        
        await callback(results)

    def _generate_request_id(self, request_data: Dict[str, Any]) -> str:
        """Generate unique request ID"""
        content = json.dumps(request_data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _get_cached_result(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get cached result if available"""
        cached = self._cache.get(request_id)
        if cached and time.time() - cached["timestamp"] < self.config.cache_ttl:
            return cached["result"]
        return None

    def _cache_result(self, request_id: str, result: Dict[str, Any]):
        """Cache request result"""
        self._cache[request_id] = {
            "result": result,
            "timestamp": time.time()
        }

    async def get_status(self) -> Dict[str, Any]:
        """Get current system status"""
        status = {
            "running": self._running,
            "queue_size": self.queue_manager.size(),
            "cache_entries": len(self._cache),
            "circuit_breakers": {
                endpoint: breaker["state"]
                for endpoint, breaker in self._circuit_breakers.items()
            }
        }
        
        if self.monitor:
            status["metrics"] = await self.monitor.get_metrics()
        
        return status