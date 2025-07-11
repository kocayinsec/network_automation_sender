#!/usr/bin/env python3
"""
Basic usage example for Network Automation Request Sender
"""

import asyncio
import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core import NetworkAutomation, AutomationConfig, RequestPriority


async def basic_example():
    """Basic usage example"""
    print("=== Basic Network Automation Example ===")
    
    # Create configuration
    config = AutomationConfig(
        max_concurrent_requests=10,
        request_timeout=15,
        retry_count=2,
        enable_monitoring=True,
        log_level="INFO"
    )
    
    # Create automation instance
    automation = NetworkAutomation(config)
    
    try:
        # Start the system
        await automation.start()
        print("✓ Automation system started")
        
        # Simple GET request
        request_config = {
            "method": "GET",
            "url": "https://httpbin.org/get",
            "headers": {
                "User-Agent": "NetworkAutomation-Example/1.0"
            }
        }
        
        print("\n--- Adding simple GET request ---")
        request_id = await automation.add_request(
            request_config,
            priority=RequestPriority.NORMAL
        )
        print(f"✓ Request {request_id} added to queue")
        
        # Wait a bit for processing
        await asyncio.sleep(3)
        
        # Get system status
        status = await automation.get_status()
        print(f"\n--- System Status ---")
        print(f"Running: {status['running']}")
        print(f"Queue size: {status['queue_size']}")
        print(f"Cache entries: {status['cache_entries']}")
        
        # Add multiple requests
        print("\n--- Adding multiple requests ---")
        urls = [
            "https://httpbin.org/uuid",
            "https://httpbin.org/json",
            "https://httpbin.org/headers"
        ]
        
        for url in urls:
            request_config = {
                "method": "GET",
                "url": url
            }
            
            request_id = await automation.add_request(
                request_config,
                priority=RequestPriority.NORMAL
            )
            print(f"✓ Request to {url} added: {request_id}")
        
        # Wait for processing
        await asyncio.sleep(5)
        
        # Get final status
        final_status = await automation.get_status()
        print(f"\n--- Final Status ---")
        print(f"Queue size: {final_status['queue_size']}")
        
        if automation.monitor:
            metrics = await automation.monitor.get_metrics()
            print(f"Total requests processed: {metrics['counters'].get('requests.completed', 0)}")
            print(f"Success rate: {metrics['gauges'].get('requests.success_rate', 0):.2%}")
        
    finally:
        # Clean shutdown
        await automation.stop()
        print("\n✓ Automation system stopped")


async def authentication_example():
    """Example with authentication"""
    print("\n\n=== Authentication Example ===")
    
    config = AutomationConfig(
        max_concurrent_requests=5,
        enable_monitoring=True
    )
    
    automation = NetworkAutomation(config)
    
    try:
        await automation.start()
        
        # API Key authentication
        request_config = {
            "method": "GET",
            "url": "https://httpbin.org/bearer",
            "auth": {
                "type": "bearer",
                "credentials": {
                    "token": "your-api-token-here"
                }
            }
        }
        
        request_id = await automation.add_request(
            request_config,
            priority=RequestPriority.HIGH
        )
        print(f"✓ Authenticated request added: {request_id}")
        
        # Basic authentication
        request_config = {
            "method": "GET",
            "url": "https://httpbin.org/basic-auth/user/pass",
            "auth": {
                "type": "basic",
                "credentials": {
                    "username": "user",
                    "password": "pass"
                }
            }
        }
        
        request_id = await automation.add_request(
            request_config,
            priority=RequestPriority.HIGH
        )
        print(f"✓ Basic auth request added: {request_id}")
        
        await asyncio.sleep(3)
        
    finally:
        await automation.stop()


async def batch_request_example():
    """Example with batch requests"""
    print("\n\n=== Batch Request Example ===")
    
    config = AutomationConfig(
        max_concurrent_requests=20,
        enable_monitoring=True
    )
    
    automation = NetworkAutomation(config)
    
    try:
        await automation.start()
        
        # Create batch of requests
        batch_requests = []
        for i in range(5):
            request_config = {
                "method": "GET",
                "url": f"https://httpbin.org/delay/{i}",
                "timeout": 10
            }
            batch_requests.append(request_config)
        
        print(f"Adding batch of {len(batch_requests)} requests...")
        
        request_ids = await automation.add_batch_requests(
            batch_requests,
            priority=RequestPriority.NORMAL
        )
        
        print(f"✓ Batch added with IDs: {request_ids}")
        
        # Wait for processing
        await asyncio.sleep(8)
        
        # Get metrics
        if automation.monitor:
            metrics = await automation.monitor.get_metrics()
            print(f"Completed requests: {metrics['counters'].get('requests.completed', 0)}")
            
            # Show histogram stats
            duration_stats = metrics['histograms'].get('request.duration', {})
            if duration_stats:
                print(f"Request duration stats:")
                print(f"  Min: {duration_stats.get('min', 0):.2f}s")
                print(f"  Max: {duration_stats.get('max', 0):.2f}s")
                print(f"  Avg: {duration_stats.get('avg', 0):.2f}s")
        
    finally:
        await automation.stop()


async def advanced_example():
    """Advanced usage with custom handlers"""
    print("\n\n=== Advanced Example ===")
    
    config = AutomationConfig(
        max_concurrent_requests=10,
        enable_monitoring=True,
        webhook_url="https://httpbin.org/post"  # Example webhook
    )
    
    automation = NetworkAutomation(config)
    
    # Custom callback function
    async def request_callback(result):
        print(f"📝 Request completed: Success={result.get('success', False)}, "
              f"Status={result.get('status_code', 'N/A')}")
    
    try:
        await automation.start()
        
        # Request with custom callback
        request_config = {
            "method": "POST",
            "url": "https://httpbin.org/post",
            "headers": {
                "Content-Type": "application/json",
                "X-Custom-Header": "test-value"
            },
            "body": {
                "message": "Hello from Network Automation!",
                "timestamp": "2024-01-01T12:00:00Z"
            },
            "body_format": "json"
        }
        
        request_id = await automation.add_request(
            request_config,
            priority=RequestPriority.HIGH,
            callback=request_callback,
            metadata={"source": "advanced_example", "version": "1.0"}
        )
        
        print(f"✓ Advanced request added: {request_id}")
        
        # Wait for processing
        await asyncio.sleep(3)
        
        # Get health status
        health = await automation.monitor.get_health_status()
        print(f"\n--- Health Status ---")
        print(f"Status: {health['status']}")
        print(f"Uptime: {health['uptime']:.2f}s")
        print(f"Active requests: {health['active_requests']}")
        
    finally:
        await automation.stop()


async def main():
    """Run all examples"""
    print("🚀 Network Automation Request Sender Examples")
    print("=" * 50)
    
    await basic_example()
    await authentication_example()
    await batch_request_example()
    await advanced_example()
    
    print("\n" + "=" * 50)
    print("✅ All examples completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())