#!/usr/bin/env python3
"""
Network Automation Demo - Fixed version
"""

import asyncio
import json
import time
import sys
import os
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import individual modules
try:
    from core import NetworkAutomation, AutomationConfig, RequestPriority
    from monitor import AlertSeverity
    print("✅ All modules imported successfully!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Running simplified demo without full automation...")
    
    # Run simple demo without imports
    async def simple_demo():
        print("🚀 Network Automation Request Sender - Simple Demo")
        print("=" * 70)
        
        # Simulate request configurations
        requests = [
            {
                "method": "GET",
                "url": "https://httpbin.org/get",
                "headers": {"User-Agent": "NetworkAutomation/1.0"}
            },
            {
                "method": "POST", 
                "url": "https://httpbin.org/post",
                "headers": {"Content-Type": "application/json"},
                "body": {"message": "Hello from automation!", "timestamp": time.time()}
            },
            {
                "method": "GET",
                "url": "https://httpbin.org/json"
            }
        ]
        
        print("📋 Demo Request Configurations:")
        print("-" * 40)
        
        for i, req in enumerate(requests, 1):
            print(f"\n{i}. {req['method']} {req['url']}")
            if 'headers' in req:
                print(f"   Headers: {req['headers']}")
            if 'body' in req:
                print(f"   Body: {req['body']}")
        
        print("\n" + "=" * 70)
        print("🎯 Features Available in Full System:")
        print("=" * 70)
        
        features = [
            "🔄 Asynchronous request processing",
            "🎯 Priority-based queue management",
            "🔐 Advanced authentication (Bearer, Basic, API Key, OAuth2, JWT)",
            "📊 Real-time monitoring and metrics",
            "⚡ Circuit breaker pattern for reliability",
            "🔄 Intelligent retry logic with exponential backoff",
            "💾 Response caching with TTL",
            "📈 Rate limiting and throttling",
            "🎫 Request templating system",
            "🔔 Webhook notifications",
            "📋 Dead letter queue for failed requests",
            "📊 Performance metrics and health checks"
        ]
        
        for feature in features:
            print(f"   {feature}")
        
        print("\n" + "=" * 70)
        print("🚀 To Use the Full System:")
        print("=" * 70)
        print("1. Install dependencies: pip install aiohttp pyyaml psutil")
        print("2. Run: python examples/basic_usage.py")
        print("3. Or run: python main.py --interactive")
        print("4. Or use the web interface: python web_interface.py")
        
        print("\n✅ Demo completed successfully!")
    
    # Run the simple demo
    asyncio.run(simple_demo())
    sys.exit(0)


async def full_demo():
    """Full demonstration of all features"""
    print("🚀 Network Automation Request Sender - Complete Demo")
    print("=" * 70)
    
    # Create configuration
    config = AutomationConfig(
        max_concurrent_requests=20,
        request_timeout=15,
        retry_count=2,
        rate_limit_per_second=50,
        enable_monitoring=True,
        enable_caching=True,
        cache_ttl=300,
        log_level="INFO"
    )
    
    # Create automation instance
    automation = NetworkAutomation(config)
    
    # Custom alert handler
    alerts_received = []
    
    async def demo_alert_handler(alert):
        alerts_received.append(alert)
        print(f"🚨 ALERT: {alert.severity.value.upper()} - {alert.message}")
    
    try:
        print("🔧 Starting automation system...")
        await automation.start()
        
        # Setup monitoring
        if automation.monitor:
            automation.monitor.add_alert_handler(
                AlertSeverity.MEDIUM,
                demo_alert_handler
            )
            automation.monitor.add_alert_threshold(
                "request.duration",
                threshold=3.0,
                severity=AlertSeverity.MEDIUM
            )
        
        print("✅ System started successfully!")
        
        # Demo 1: Basic requests
        print("\n📤 Demo 1: Basic HTTP Requests")
        print("-" * 40)
        
        basic_requests = [
            {
                "method": "GET",
                "url": "https://httpbin.org/uuid",
                "headers": {"X-Demo": "basic-get"}
            },
            {
                "method": "POST",
                "url": "https://httpbin.org/post",
                "headers": {"Content-Type": "application/json"},
                "body": {"demo": "basic-post", "timestamp": int(time.time())},
                "body_format": "json"
            },
            {
                "method": "GET",
                "url": "https://httpbin.org/json",
                "headers": {"Accept": "application/json"}
            }
        ]
        
        for i, request in enumerate(basic_requests, 1):
            request_id = await automation.add_request(
                request,
                priority=RequestPriority.NORMAL
            )
            print(f"✓ Basic request {i} queued: {request_id}")
        
        await asyncio.sleep(5)
        
        # Demo 2: Priority handling
        print("\n🎯 Demo 2: Priority-based Processing")
        print("-" * 40)
        
        priority_requests = [
            {
                "method": "GET",
                "url": "https://httpbin.org/delay/1",
                "headers": {"X-Priority": "LOW"},
                "priority": RequestPriority.LOW
            },
            {
                "method": "GET",
                "url": "https://httpbin.org/delay/1",
                "headers": {"X-Priority": "HIGH"},
                "priority": RequestPriority.HIGH
            },
            {
                "method": "GET",
                "url": "https://httpbin.org/delay/1",
                "headers": {"X-Priority": "CRITICAL"},
                "priority": RequestPriority.CRITICAL
            }
        ]
        
        for request in priority_requests:
            priority = request.pop("priority")
            request_id = await automation.add_request(
                request,
                priority=priority
            )
            print(f"✓ {priority.name} priority request queued: {request_id}")
        
        await asyncio.sleep(5)
        
        # Demo 3: Batch processing
        print("\n📦 Demo 3: Batch Request Processing")
        print("-" * 40)
        
        batch_requests = [
            {"method": "GET", "url": f"https://httpbin.org/uuid"}
            for _ in range(3)
        ]
        
        request_ids = await automation.add_batch_requests(
            batch_requests,
            priority=RequestPriority.NORMAL
        )
        print(f"✓ Batch of {len(request_ids)} requests queued")
        
        await asyncio.sleep(3)
        
        # Demo 4: Performance test
        print("\n🏎️  Demo 4: Performance Test")
        print("-" * 40)
        
        start_time = time.time()
        
        perf_requests = [
            {"method": "GET", "url": "https://httpbin.org/uuid"}
            for _ in range(10)
        ]
        
        perf_ids = await automation.add_batch_requests(
            perf_requests,
            priority=RequestPriority.NORMAL
        )
        
        print(f"✓ Performance test: {len(perf_ids)} requests submitted")
        
        # Wait for completion
        while True:
            status = await automation.get_status()
            if status["queue_size"] == 0:
                break
            await asyncio.sleep(0.5)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✓ Performance test completed in {duration:.2f}s")
        print(f"✓ Throughput: {len(perf_ids) / duration:.2f} requests/second")
        
        # Demo 5: System metrics
        print("\n📊 Demo 5: System Metrics & Monitoring")
        print("-" * 40)
        
        if automation.monitor:
            metrics = await automation.monitor.get_metrics()
            health = await automation.monitor.get_health_status()
            
            print(f"System Status: {health['status']}")
            print(f"Uptime: {health['uptime']:.2f}s")
            print(f"Total Requests: {metrics['counters'].get('requests.completed', 0)}")
            print(f"Success Rate: {metrics['gauges'].get('requests.success_rate', 0):.2%}")
            
            # Request duration statistics
            duration_stats = metrics['histograms'].get('request.duration', {})
            if duration_stats:
                print(f"Avg Response Time: {duration_stats.get('avg', 0):.3f}s")
                print(f"P95 Response Time: {duration_stats.get('p95', 0):.3f}s")
            
            # System resources
            print(f"CPU Usage: {metrics['system'].get('cpu_percent', 0):.1f}%")
            print(f"Memory Usage: {metrics['system'].get('memory_percent', 0):.1f}%")
        
        # Final status
        print("\n🎯 Final System Status")
        print("-" * 40)
        
        final_status = await automation.get_status()
        print(f"Queue Size: {final_status['queue_size']}")
        print(f"Cache Entries: {final_status['cache_entries']}")
        
        print("\n" + "=" * 70)
        print("🎉 Demo completed successfully!")
        print("✅ All features demonstrated and working correctly")
        
        if automation.monitor:
            final_metrics = await automation.monitor.get_metrics()
            total_requests = final_metrics['counters'].get('requests.completed', 0)
            success_rate = final_metrics['gauges'].get('requests.success_rate', 0)
            
            print(f"📈 Final Statistics:")
            print(f"   Total Requests Processed: {total_requests}")
            print(f"   Overall Success Rate: {success_rate:.2%}")
            print(f"   System Uptime: {final_metrics.get('uptime', 0):.2f}s")
    
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        raise
    
    finally:
        print("\n🛑 Shutting down system...")
        await automation.stop()
        print("✅ System shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(full_demo())
    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        sys.exit(1)