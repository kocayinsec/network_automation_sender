#!/usr/bin/env python3
"""
Advanced usage examples for Network Automation Request Sender
"""

import asyncio
import json
import time
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core import NetworkAutomation, AutomationConfig, RequestPriority
from monitor import AlertSeverity


async def template_example():
    """Example using request templates"""
    print("=== Request Templates Example ===")
    
    config = AutomationConfig(
        max_concurrent_requests=10,
        enable_monitoring=True
    )
    
    automation = NetworkAutomation(config)
    
    # Register custom templates
    rest_api_template = {
        "method": "GET",
        "headers": {
            "Content-Type": "application/json",
            "User-Agent": "NetworkAutomation/1.0",
            "Accept": "application/json"
        },
        "timeout": 30,
        "validators": ["required_headers"]
    }
    
    automation.request_builder.register_template("rest_api", rest_api_template)
    
    try:
        await automation.start()
        
        # Use template
        request_config = {
            "template": "rest_api",
            "url": "https://httpbin.org/json",
            "headers": {
                "X-Custom-Header": "custom-value"  # This will be merged with template
            }
        }
        
        request_id = await automation.add_request(
            request_config,
            priority=RequestPriority.NORMAL
        )
        
        print(f"✓ Template-based request added: {request_id}")
        
        await asyncio.sleep(3)
        
    finally:
        await automation.stop()


async def queue_partitioning_example():
    """Example with queue partitioning"""
    print("\n=== Queue Partitioning Example ===")
    
    config = AutomationConfig(
        max_concurrent_requests=15,
        enable_monitoring=True
    )
    
    automation = NetworkAutomation(config)
    
    try:
        await automation.start()
        
        # Set partition limits
        await automation.queue_manager.set_partition_limit("high_priority", 10)
        await automation.queue_manager.set_partition_limit("low_priority", 5)
        
        # Add requests to different partitions
        print("Adding requests to different partitions...")
        
        # High priority partition
        for i in range(3):
            request_config = {
                "method": "GET",
                "url": f"https://httpbin.org/delay/{i}",
                "partition": "high_priority"
            }
            
            request_id = await automation.add_request(
                request_config,
                priority=RequestPriority.HIGH,
                metadata={"partition": "high_priority"}
            )
            print(f"✓ High priority request {i+1} added: {request_id}")
        
        # Low priority partition
        for i in range(2):
            request_config = {
                "method": "GET",
                "url": f"https://httpbin.org/delay/{i+3}",
                "partition": "low_priority"
            }
            
            request_id = await automation.add_request(
                request_config,
                priority=RequestPriority.LOW,
                metadata={"partition": "low_priority"}
            )
            print(f"✓ Low priority request {i+1} added: {request_id}")
        
        # Wait for processing
        await asyncio.sleep(8)
        
        # Get partition statistics
        stats = await automation.queue_manager.get_stats()
        print(f"\n--- Queue Statistics ---")
        print(f"Total processed: {stats['total_dequeued']}")
        print(f"Partition sizes: {stats['partitions']}")
        
    finally:
        await automation.stop()


async def circuit_breaker_example():
    """Example demonstrating circuit breaker functionality"""
    print("\n=== Circuit Breaker Example ===")
    
    config = AutomationConfig(
        max_concurrent_requests=5,
        retry_count=1,  # Reduce retries for faster demo
        enable_monitoring=True
    )
    
    automation = NetworkAutomation(config)
    
    try:
        await automation.start()
        
        # First, send some requests to a failing endpoint
        print("Sending requests to failing endpoint...")
        
        failing_url = "https://httpbin.org/status/500"
        
        for i in range(6):  # More than circuit breaker threshold
            request_config = {
                "method": "GET",
                "url": failing_url,
                "timeout": 5
            }
            
            request_id = await automation.add_request(
                request_config,
                priority=RequestPriority.NORMAL
            )
            print(f"✓ Request {i+1} to failing endpoint added: {request_id}")
        
        # Wait for requests to fail
        await asyncio.sleep(10)
        
        # Now try to send another request - should be blocked by circuit breaker
        print("\nTrying to send another request (should be blocked)...")
        
        request_config = {
            "method": "GET",
            "url": failing_url,
            "timeout": 5
        }
        
        request_id = await automation.add_request(
            request_config,
            priority=RequestPriority.NORMAL
        )
        print(f"✓ Request added: {request_id}")
        
        await asyncio.sleep(5)
        
        # Check system status
        status = await automation.get_status()
        print(f"\n--- Circuit Breaker Status ---")
        print(f"Circuit breakers: {status.get('circuit_breakers', {})}")
        
    finally:
        await automation.stop()


async def monitoring_alerts_example():
    """Example with custom monitoring and alerts"""
    print("\n=== Monitoring & Alerts Example ===")
    
    config = AutomationConfig(
        max_concurrent_requests=10,
        enable_monitoring=True,
        request_timeout=5  # Short timeout for demo
    )
    
    automation = NetworkAutomation(config)
    
    # Custom alert handler
    async def custom_alert_handler(alert):
        print(f"🚨 ALERT: {alert.severity.value.upper()} - {alert.message}")
    
    try:
        await automation.start()
        
        # Add custom alert handler
        automation.monitor.add_alert_handler(
            AlertSeverity.HIGH,
            custom_alert_handler
        )
        
        # Add custom alert threshold
        automation.monitor.add_alert_threshold(
            "request.duration",
            threshold=3.0,
            severity=AlertSeverity.HIGH
        )
        
        # Add custom metrics
        automation.monitor.add_custom_metric("example.counter", 100, "counter")
        automation.monitor.add_custom_metric("example.gauge", 75.5, "gauge")
        
        # Send requests that might trigger alerts
        print("Sending requests that might trigger alerts...")
        
        request_configs = [
            {
                "method": "GET",
                "url": "https://httpbin.org/delay/2",  # 2 second delay
                "timeout": 10
            },
            {
                "method": "GET",
                "url": "https://httpbin.org/delay/4",  # 4 second delay - should trigger alert
                "timeout": 10
            },
            {
                "method": "GET",
                "url": "https://httpbin.org/status/500",  # Error response
                "timeout": 10
            }
        ]
        
        for i, config in enumerate(request_configs):
            request_id = await automation.add_request(
                config,
                priority=RequestPriority.NORMAL
            )
            print(f"✓ Request {i+1} added: {request_id}")
        
        # Wait for processing and alerts
        await asyncio.sleep(15)
        
        # Get health status
        health = await automation.monitor.get_health_status()
        print(f"\n--- Health Status ---")
        print(f"Status: {health['status']}")
        print(f"Active alerts: {health['active_alerts']}")
        
        # Get detailed metrics
        metrics = await automation.monitor.get_metrics()
        print(f"\n--- Metrics ---")
        print(f"Success rate: {metrics['gauges'].get('requests.success_rate', 0):.2%}")
        print(f"Failure rate: {metrics['gauges'].get('requests.failure_rate', 0):.2%}")
        
        duration_stats = metrics['histograms'].get('request.duration', {})
        if duration_stats:
            print(f"Request duration (avg): {duration_stats.get('avg', 0):.2f}s")
            print(f"Request duration (p95): {duration_stats.get('p95', 0):.2f}s")
        
    finally:
        await automation.stop()


async def file_download_example():
    """Example of file download functionality"""
    print("\n=== File Download Example ===")
    
    config = AutomationConfig(
        max_concurrent_requests=5,
        enable_monitoring=True
    )
    
    automation = NetworkAutomation(config)
    
    try:
        await automation.start()
        
        # Download a file
        print("Downloading file...")
        
        download_result = await automation.request_sender.download_file(
            url="https://httpbin.org/json",
            file_path="/tmp/downloaded_file.json"
        )
        
        if download_result["success"]:
            print(f"✓ File downloaded successfully")
            print(f"  Path: {download_result['file_path']}")
            print(f"  Size: {download_result['size']} bytes")
            print(f"  Content-Type: {download_result['content_type']}")
        else:
            print(f"✗ Download failed: {download_result['error']}")
        
        # Test connectivity
        print("\nTesting connectivity...")
        
        connectivity_result = await automation.request_sender.test_connectivity(
            "https://httpbin.org/get"
        )
        
        if connectivity_result["success"]:
            print(f"✓ Connectivity test passed")
            print(f"  Total time: {connectivity_result['total_time']:.2f}s")
            print(f"  DNS time: {connectivity_result['dns_time']:.2f}s")
            print(f"  TCP time: {connectivity_result['tcp_time']:.2f}s")
            print(f"  HTTP time: {connectivity_result['http_time']:.2f}s")
            print(f"  IP addresses: {connectivity_result['ip_addresses']}")
        else:
            print(f"✗ Connectivity test failed: {connectivity_result['error']}")
        
    finally:
        await automation.stop()


async def webhook_notifications_example():
    """Example with webhook notifications"""
    print("\n=== Webhook Notifications Example ===")
    
    config = AutomationConfig(
        max_concurrent_requests=5,
        enable_monitoring=True,
        webhook_url="https://httpbin.org/post"  # Example webhook endpoint
    )
    
    automation = NetworkAutomation(config)
    
    try:
        await automation.start()
        
        print("Sending request with webhook notification...")
        
        # This request will trigger a webhook notification
        request_config = {
            "method": "GET",
            "url": "https://httpbin.org/json",
            "headers": {
                "X-Test-Header": "webhook-test"
            }
        }
        
        request_id = await automation.add_request(
            request_config,
            priority=RequestPriority.NORMAL,
            metadata={"webhook_test": True, "timestamp": time.time()}
        )
        
        print(f"✓ Request with webhook notification added: {request_id}")
        
        # Wait for processing
        await asyncio.sleep(5)
        
        print("✓ Webhook notification should have been sent")
        
    finally:
        await automation.stop()


async def performance_test():
    """Performance test with many concurrent requests"""
    print("\n=== Performance Test ===")
    
    config = AutomationConfig(
        max_concurrent_requests=50,
        rate_limit_per_second=200,
        enable_monitoring=True,
        enable_caching=True
    )
    
    automation = NetworkAutomation(config)
    
    try:
        await automation.start()
        
        print("Starting performance test with 100 requests...")
        
        start_time = time.time()
        
        # Create 100 requests
        batch_requests = []
        for i in range(100):
            request_config = {
                "method": "GET",
                "url": f"https://httpbin.org/uuid",
                "headers": {
                    "X-Request-Number": str(i)
                }
            }
            batch_requests.append(request_config)
        
        # Submit all requests
        request_ids = await automation.add_batch_requests(
            batch_requests,
            priority=RequestPriority.NORMAL
        )
        
        print(f"✓ {len(request_ids)} requests submitted")
        
        # Wait for completion
        while True:
            status = await automation.get_status()
            if status["queue_size"] == 0:
                break
            await asyncio.sleep(0.5)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"\n--- Performance Results ---")
        print(f"Total time: {total_time:.2f}s")
        print(f"Requests per second: {len(request_ids) / total_time:.2f}")
        
        # Get detailed metrics
        if automation.monitor:
            metrics = await automation.monitor.get_metrics()
            print(f"Total completed: {metrics['counters'].get('requests.completed', 0)}")
            print(f"Success rate: {metrics['gauges'].get('requests.success_rate', 0):.2%}")
            
            duration_stats = metrics['histograms'].get('request.duration', {})
            if duration_stats:
                print(f"Avg response time: {duration_stats.get('avg', 0):.2f}s")
                print(f"P95 response time: {duration_stats.get('p95', 0):.2f}s")
        
    finally:
        await automation.stop()


async def main():
    """Run all advanced examples"""
    print("🚀 Advanced Network Automation Examples")
    print("=" * 60)
    
    await template_example()
    await queue_partitioning_example()
    await circuit_breaker_example()
    await monitoring_alerts_example()
    await file_download_example()
    await webhook_notifications_example()
    await performance_test()
    
    print("\n" + "=" * 60)
    print("✅ All advanced examples completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())