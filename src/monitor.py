"""
Network Monitor
Real-time monitoring and metrics collection for network automation
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import psutil
import aiofiles
from dataclasses import dataclass
from enum import Enum
import statistics

from .exceptions import MonitorError


class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert data structure"""
    id: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    metric: str
    value: float
    threshold: float
    resolved: bool = False


class MetricCollector:
    """Collects and aggregates metrics"""
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.metrics = defaultdict(lambda: deque(maxlen=window_size))
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.histograms = defaultdict(list)
        
    def record(self, metric: str, value: float, timestamp: Optional[datetime] = None):
        """Record a metric value"""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        self.metrics[metric].append((timestamp, value))
        
    def increment(self, metric: str, value: float = 1.0):
        """Increment a counter"""
        self.counters[metric] += value
        
    def set_gauge(self, metric: str, value: float):
        """Set a gauge value"""
        self.gauges[metric] = value
        
    def record_histogram(self, metric: str, value: float):
        """Record a histogram value"""
        self.histograms[metric].append(value)
        
        # Keep only recent values
        if len(self.histograms[metric]) > self.window_size:
            self.histograms[metric] = self.histograms[metric][-self.window_size:]
    
    def get_stats(self, metric: str) -> Dict[str, float]:
        """Get statistics for a metric"""
        if metric not in self.metrics:
            return {}
        
        values = [v for _, v in self.metrics[metric]]
        if not values:
            return {}
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": statistics.mean(values),
            "median": statistics.median(values),
            "p95": statistics.quantiles(values, n=20)[18] if len(values) > 1 else values[0],
            "p99": statistics.quantiles(values, n=100)[98] if len(values) > 1 else values[0]
        }
    
    def get_histogram_stats(self, metric: str) -> Dict[str, float]:
        """Get histogram statistics"""
        if metric not in self.histograms:
            return {}
        
        values = self.histograms[metric]
        if not values:
            return {}
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": statistics.mean(values),
            "median": statistics.median(values),
            "p95": statistics.quantiles(values, n=20)[18] if len(values) > 1 else values[0],
            "p99": statistics.quantiles(values, n=100)[98] if len(values) > 1 else values[0]
        }


class AlertManager:
    """Manages alerts and notifications"""
    
    def __init__(self, max_alerts: int = 1000):
        self.max_alerts = max_alerts
        self.alerts: List[Alert] = []
        self.alert_handlers: Dict[AlertSeverity, List[Callable]] = defaultdict(list)
        self.thresholds: Dict[str, Dict[str, float]] = {}
        
    def add_threshold(self, metric: str, severity: AlertSeverity, threshold: float, 
                     comparison: str = "gt"):
        """Add an alert threshold"""
        self.thresholds[metric] = {
            "severity": severity,
            "threshold": threshold,
            "comparison": comparison
        }
    
    def add_alert_handler(self, severity: AlertSeverity, handler: Callable):
        """Add an alert handler"""
        self.alert_handlers[severity].append(handler)
    
    async def check_metric(self, metric: str, value: float):
        """Check if metric value triggers an alert"""
        if metric not in self.thresholds:
            return
        
        config = self.thresholds[metric]
        threshold = config["threshold"]
        comparison = config["comparison"]
        severity = config["severity"]
        
        should_alert = False
        
        if comparison == "gt" and value > threshold:
            should_alert = True
        elif comparison == "lt" and value < threshold:
            should_alert = True
        elif comparison == "eq" and value == threshold:
            should_alert = True
        
        if should_alert:
            await self.create_alert(metric, value, threshold, severity)
    
    async def create_alert(self, metric: str, value: float, threshold: float, 
                          severity: AlertSeverity):
        """Create a new alert"""
        alert = Alert(
            id=f"{metric}_{int(time.time())}",
            severity=severity,
            message=f"Metric {metric} value {value} exceeded threshold {threshold}",
            timestamp=datetime.utcnow(),
            metric=metric,
            value=value,
            threshold=threshold
        )
        
        self.alerts.append(alert)
        
        # Maintain max alerts limit
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]
        
        # Notify handlers
        for handler in self.alert_handlers[severity]:
            try:
                await handler(alert)
            except Exception as e:
                logging.error(f"Alert handler failed: {e}")
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return [alert for alert in self.alerts if not alert.resolved]
    
    def resolve_alert(self, alert_id: str):
        """Resolve an alert"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.resolved = True
                break


class NetworkMonitor:
    """
    Comprehensive network monitoring system with:
    - Real-time metrics collection
    - Performance monitoring
    - Alert management
    - Health checks
    - Resource monitoring
    """
    
    def __init__(self, collect_interval: int = 5):
        self.collect_interval = collect_interval
        self.logger = logging.getLogger(__name__)
        
        # Components
        self.metric_collector = MetricCollector()
        self.alert_manager = AlertManager()
        
        # State
        self.running = False
        self.start_time = None
        self.tasks: List[asyncio.Task] = []
        
        # Request tracking
        self.active_requests: Dict[str, datetime] = {}
        self.request_history: deque = deque(maxlen=10000)
        
        # System metrics
        self.system_metrics: Dict[str, Any] = {}
        
        # Setup default thresholds
        self._setup_default_thresholds()
    
    async def start(self):
        """Start monitoring"""
        if self.running:
            return
        
        self.running = True
        self.start_time = datetime.utcnow()
        
        # Start monitoring tasks
        self.tasks = [
            asyncio.create_task(self._collect_metrics()),
            asyncio.create_task(self._monitor_system()),
            asyncio.create_task(self._check_alerts()),
            asyncio.create_task(self._export_metrics())
        ]
        
        self.logger.info("Network monitor started")
    
    async def stop(self):
        """Stop monitoring"""
        if not self.running:
            return
        
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        self.logger.info("Network monitor stopped")
    
    async def record_request_queued(self, request_id: str):
        """Record when a request is queued"""
        self.metric_collector.increment("requests.queued")
        self.metric_collector.record("queue.size", len(self.active_requests))
    
    async def record_request_started(self, request_id: str):
        """Record when a request starts processing"""
        self.active_requests[request_id] = datetime.utcnow()
        self.metric_collector.increment("requests.started")
        self.metric_collector.record("requests.active", len(self.active_requests))
    
    async def record_request_completed(self, request_id: str, success: bool, duration: float):
        """Record when a request completes"""
        if request_id in self.active_requests:
            del self.active_requests[request_id]
        
        # Update metrics
        self.metric_collector.increment("requests.completed")
        self.metric_collector.record_histogram("request.duration", duration)
        
        if success:
            self.metric_collector.increment("requests.success")
        else:
            self.metric_collector.increment("requests.failed")
        
        # Calculate success rate
        total_requests = (self.metric_collector.counters["requests.success"] + 
                         self.metric_collector.counters["requests.failed"])
        
        if total_requests > 0:
            success_rate = self.metric_collector.counters["requests.success"] / total_requests
            self.metric_collector.set_gauge("requests.success_rate", success_rate)
        
        # Record in history
        self.request_history.append({
            "id": request_id,
            "timestamp": datetime.utcnow(),
            "success": success,
            "duration": duration
        })
        
        # Check for alerts
        await self.alert_manager.check_metric("request.duration", duration)
        await self.alert_manager.check_metric("requests.success_rate", 
                                             self.metric_collector.gauges.get("requests.success_rate", 1.0))
    
    async def record_request_failed(self, request_id: str, error: str):
        """Record when a request fails"""
        if request_id in self.active_requests:
            del self.active_requests[request_id]
        
        self.metric_collector.increment("requests.failed")
        self.metric_collector.increment(f"errors.{error}")
        
        # Update failure rate
        total_requests = (self.metric_collector.counters["requests.success"] + 
                         self.metric_collector.counters["requests.failed"])
        
        if total_requests > 0:
            failure_rate = self.metric_collector.counters["requests.failed"] / total_requests
            self.metric_collector.set_gauge("requests.failure_rate", failure_rate)
            
            # Check for alerts
            await self.alert_manager.check_metric("requests.failure_rate", failure_rate)
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get all current metrics"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": self._get_uptime(),
            "counters": dict(self.metric_collector.counters),
            "gauges": dict(self.metric_collector.gauges),
            "histograms": {
                metric: self.metric_collector.get_histogram_stats(metric)
                for metric in self.metric_collector.histograms
            },
            "system": self.system_metrics,
            "alerts": {
                "active": len(self.alert_manager.get_active_alerts()),
                "total": len(self.alert_manager.alerts)
            },
            "requests": {
                "active": len(self.active_requests),
                "total_processed": len(self.request_history)
            }
        }
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status"""
        active_alerts = self.alert_manager.get_active_alerts()
        critical_alerts = [a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]
        
        # Determine health status
        if critical_alerts:
            status = "critical"
        elif len(active_alerts) > 10:
            status = "degraded"
        elif len(active_alerts) > 0:
            status = "warning"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "uptime": self._get_uptime(),
            "active_alerts": len(active_alerts),
            "critical_alerts": len(critical_alerts),
            "system_load": self.system_metrics.get("cpu_percent", 0),
            "memory_usage": self.system_metrics.get("memory_percent", 0),
            "active_requests": len(self.active_requests)
        }
    
    def add_custom_metric(self, name: str, value: float, metric_type: str = "gauge"):
        """Add a custom metric"""
        if metric_type == "gauge":
            self.metric_collector.set_gauge(name, value)
        elif metric_type == "counter":
            self.metric_collector.increment(name, value)
        elif metric_type == "histogram":
            self.metric_collector.record_histogram(name, value)
        else:
            self.metric_collector.record(name, value)
    
    def add_alert_threshold(self, metric: str, threshold: float, 
                          severity: AlertSeverity = AlertSeverity.MEDIUM,
                          comparison: str = "gt"):
        """Add an alert threshold"""
        self.alert_manager.add_threshold(metric, severity, threshold, comparison)
    
    def add_alert_handler(self, severity: AlertSeverity, handler: Callable):
        """Add an alert handler"""
        self.alert_manager.add_alert_handler(severity, handler)
    
    async def _collect_metrics(self):
        """Collect metrics periodically"""
        while self.running:
            try:
                # Collect queue metrics
                self.metric_collector.record("requests.active", len(self.active_requests))
                
                # Collect throughput metrics
                if self.request_history:
                    recent_requests = [
                        r for r in self.request_history
                        if r["timestamp"] > datetime.utcnow() - timedelta(minutes=1)
                    ]
                    self.metric_collector.record("requests.per_minute", len(recent_requests))
                
                # Collect custom metrics
                await self._collect_custom_metrics()
                
                await asyncio.sleep(self.collect_interval)
                
            except Exception as e:
                self.logger.error(f"Metrics collection failed: {e}")
                await asyncio.sleep(self.collect_interval)
    
    async def _monitor_system(self):
        """Monitor system resources"""
        while self.running:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.metric_collector.record("system.cpu_percent", cpu_percent)
                self.system_metrics["cpu_percent"] = cpu_percent
                
                # Memory usage
                memory = psutil.virtual_memory()
                self.metric_collector.record("system.memory_percent", memory.percent)
                self.system_metrics["memory_percent"] = memory.percent
                self.system_metrics["memory_available"] = memory.available
                
                # Disk usage
                disk = psutil.disk_usage('/')
                self.metric_collector.record("system.disk_percent", disk.percent)
                self.system_metrics["disk_percent"] = disk.percent
                
                # Network stats
                net_io = psutil.net_io_counters()
                self.metric_collector.record("system.bytes_sent", net_io.bytes_sent)
                self.metric_collector.record("system.bytes_recv", net_io.bytes_recv)
                
                # Check system thresholds
                await self.alert_manager.check_metric("system.cpu_percent", cpu_percent)
                await self.alert_manager.check_metric("system.memory_percent", memory.percent)
                await self.alert_manager.check_metric("system.disk_percent", disk.percent)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"System monitoring failed: {e}")
                await asyncio.sleep(30)
    
    async def _check_alerts(self):
        """Check for alert conditions"""
        while self.running:
            try:
                # Check for stuck requests
                stuck_threshold = timedelta(minutes=5)
                for request_id, start_time in self.active_requests.items():
                    if datetime.utcnow() - start_time > stuck_threshold:
                        await self.alert_manager.create_alert(
                            "requests.stuck",
                            (datetime.utcnow() - start_time).total_seconds(),
                            stuck_threshold.total_seconds(),
                            AlertSeverity.HIGH
                        )
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Alert checking failed: {e}")
                await asyncio.sleep(60)
    
    async def _export_metrics(self):
        """Export metrics to file"""
        while self.running:
            try:
                metrics = await self.get_metrics()
                
                # Write to metrics file
                metrics_file = "/Users/emrekocay/network_automation_sender/logs/metrics.json"
                async with aiofiles.open(metrics_file, "w") as f:
                    await f.write(json.dumps(metrics, indent=2))
                
                await asyncio.sleep(60)  # Export every minute
                
            except Exception as e:
                self.logger.error(f"Metrics export failed: {e}")
                await asyncio.sleep(60)
    
    async def _collect_custom_metrics(self):
        """Collect any custom metrics"""
        # Override this method to add custom metrics collection
        pass
    
    def _setup_default_thresholds(self):
        """Setup default alert thresholds"""
        self.alert_manager.add_threshold("system.cpu_percent", AlertSeverity.HIGH, 80)
        self.alert_manager.add_threshold("system.memory_percent", AlertSeverity.HIGH, 85)
        self.alert_manager.add_threshold("system.disk_percent", AlertSeverity.HIGH, 90)
        self.alert_manager.add_threshold("requests.failure_rate", AlertSeverity.MEDIUM, 0.1)
        self.alert_manager.add_threshold("request.duration", AlertSeverity.MEDIUM, 30)
    
    def _get_uptime(self) -> float:
        """Get system uptime in seconds"""
        if self.start_time is None:
            return 0
        return (datetime.utcnow() - self.start_time).total_seconds()