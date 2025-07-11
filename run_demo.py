#!/usr/bin/env python3
"""
Demo script to showcase the Network Automation Request Sender
"""

import asyncio
import json
import time
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core import NetworkAutomation, AutomationConfig, RequestPriority
from monitor import AlertSeverity


async def demo_showcase():
    """Comprehensive demo of all features"""
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
                "url": "https://httpbin.org/delay/2",
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
        
        await asyncio.sleep(8)
        
        # Demo 3: Authentication
        print("\n🔐 Demo 3: Authentication Methods")
        print("-" * 40)
        
        auth_requests = [
            {
                "method": "GET",
                "url": "https://httpbin.org/bearer",
                "auth": {
                    "type": "bearer",
                    "credentials": {"token": "demo-bearer-token"}
                }
            },
            {
                "method": "GET",
                "url": "https://httpbin.org/basic-auth/demo/password",
                "auth": {
                    "type": "basic",
                    "credentials": {"username": "demo", "password": "password"}
                }
            }
        ]
        
        for i, request in enumerate(auth_requests, 1):
            request_id = await automation.add_request(
                request,
                priority=RequestPriority.NORMAL
            )
            print(f"✓ Auth request {i} queued: {request_id}")
        
        await asyncio.sleep(3)
        
        # Demo 4: Batch processing
        print("\n📦 Demo 4: Batch Request Processing")
        print("-" * 40)
        
        batch_requests = [
            {"method": "GET", "url": f"https://httpbin.org/uuid"}
            for _ in range(5)
        ]
        
        request_ids = await automation.add_batch_requests(
            batch_requests,
            priority=RequestPriority.NORMAL
        )
        print(f"✓ Batch of {len(request_ids)} requests queued")
        
        await asyncio.sleep(5)
        
        # Demo 5: Error handling and retries
        print("\n⚠️  Demo 5: Error Handling & Retries")
        print("-" * 40)
        
        error_requests = [
            {
                "method": "GET",
                "url": "https://httpbin.org/status/500",
                "headers": {"X-Expected": "error-500"}
            },
            {
                "method": "GET",
                "url": "https://httpbin.org/status/404",
                "headers": {"X-Expected": "error-404"}
            }
        ]
        
        for i, request in enumerate(error_requests, 1):
            request_id = await automation.add_request(
                request,
                priority=RequestPriority.NORMAL
            )
            print(f"✓ Error test request {i} queued: {request_id}")
        
        await asyncio.sleep(5)
        
        # Demo 6: Performance test
        print("\n🏎️  Demo 6: Performance Test")
        print("-" * 40)
        
        start_time = time.time()
        
        perf_requests = [
            {"method": "GET", "url": "https://httpbin.org/uuid"}
            for _ in range(20)
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
        
        # Demo 7: System metrics
        print("\n📊 Demo 7: System Metrics & Monitoring")
        print("-" * 40)
        
        if automation.monitor:
            metrics = await automation.monitor.get_metrics()
            health = await automation.monitor.get_health_status()
            
            print(f"System Status: {health['status']}")
            print(f"Uptime: {health['uptime']:.2f}s")
            print(f"Total Requests: {metrics['counters'].get('requests.completed', 0)}")
            print(f"Success Rate: {metrics['gauges'].get('requests.success_rate', 0):.2%}")
            print(f"Failure Rate: {metrics['gauges'].get('requests.failure_rate', 0):.2%}")
            
            # Request duration statistics
            duration_stats = metrics['histograms'].get('request.duration', {})
            if duration_stats:
                print(f"Avg Response Time: {duration_stats.get('avg', 0):.3f}s")
                print(f"P95 Response Time: {duration_stats.get('p95', 0):.3f}s")
                print(f"P99 Response Time: {duration_stats.get('p99', 0):.3f}s")
            
            # System resources
            print(f"CPU Usage: {metrics['system'].get('cpu_percent', 0):.1f}%")
            print(f"Memory Usage: {metrics['system'].get('memory_percent', 0):.1f}%")
            
            # Alerts
            if alerts_received:
                print(f"Alerts Generated: {len(alerts_received)}")
                for alert in alerts_received[-3:]:  # Show last 3 alerts
                    print(f"  - {alert.severity.value}: {alert.message}")
        
        # Demo 8: Final status
        print("\n🎯 Demo 8: Final System Status")
        print("-" * 40)
        
        final_status = await automation.get_status()
        print(f"Queue Size: {final_status['queue_size']}")
        print(f"Cache Entries: {final_status['cache_entries']}")
        print(f"Circuit Breakers: {len(final_status.get('circuit_breakers', {}))}")
        
        # Show circuit breaker states
        if final_status.get('circuit_breakers'):
            print("Circuit Breaker States:")
            for endpoint, state in final_status['circuit_breakers'].items():
                print(f"  {endpoint}: {state}")
        
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


async def main():
    """Main entry point"""
    try:
        await demo_showcase()
    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())