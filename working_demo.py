#!/usr/bin/env python3
"""
Working Network Automation Demo
"""

import asyncio
import aiohttp
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List


class SimpleNetworkAutomation:
    """Simplified network automation for demo purposes"""
    
    def __init__(self):
        self.session = None
        self.request_count = 0
        self.success_count = 0
        self.start_time = None
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start the automation system"""
        self.session = aiohttp.ClientSession()
        self.start_time = time.time()
        self.logger.info("🚀 Network Automation System started")
    
    async def stop(self):
        """Stop the automation system"""
        if self.session:
            await self.session.close()
        self.logger.info("🛑 Network Automation System stopped")
    
    async def send_request(self, method: str, url: str, headers: Dict = None, 
                          body: Dict = None, timeout: int = 30) -> Dict[str, Any]:
        """Send a single HTTP request"""
        self.request_count += 1
        request_id = f"req_{self.request_count}_{int(time.time())}"
        
        try:
            start_time = time.time()
            
            # Prepare request parameters
            kwargs = {
                'method': method,
                'url': url,
                'headers': headers or {},
                'timeout': aiohttp.ClientTimeout(total=timeout)
            }
            
            if body and method.upper() in ['POST', 'PUT', 'PATCH']:
                kwargs['json'] = body
            
            # Send request
            async with self.session.request(**kwargs) as response:
                response_data = await response.text()
                
                # Try to parse as JSON
                try:
                    response_data = json.loads(response_data)
                except:
                    pass
                
                duration = time.time() - start_time
                
                # Determine success
                success = 200 <= response.status < 400
                if success:
                    self.success_count += 1
                
                result = {
                    'request_id': request_id,
                    'success': success,
                    'status_code': response.status,
                    'method': method,
                    'url': url,
                    'duration': duration,
                    'response_data': response_data,
                    'headers': dict(response.headers),
                    'timestamp': datetime.now().isoformat()
                }
                
                status_emoji = "✅" if success else "❌"
                self.logger.info(f"{status_emoji} {method} {url} - {response.status} ({duration:.3f}s)")
                
                return result
                
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"❌ {method} {url} - Error: {e}")
            
            return {
                'request_id': request_id,
                'success': False,
                'error': str(e),
                'method': method,
                'url': url,
                'duration': duration,
                'timestamp': datetime.now().isoformat()
            }
    
    async def send_batch(self, requests: List[Dict], max_concurrent: int = 10) -> List[Dict]:
        """Send multiple requests concurrently"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def send_single(request_config):
            async with semaphore:
                return await self.send_request(**request_config)
        
        tasks = [send_single(req) for req in requests]
        return await asyncio.gather(*tasks)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        uptime = time.time() - self.start_time if self.start_time else 0
        success_rate = (self.success_count / self.request_count) if self.request_count > 0 else 0
        
        return {
            'total_requests': self.request_count,
            'successful_requests': self.success_count,
            'success_rate': success_rate,
            'uptime_seconds': uptime,
            'requests_per_second': self.request_count / uptime if uptime > 0 else 0
        }


async def run_comprehensive_demo():
    """Run a comprehensive demonstration"""
    print("🚀 Network Automation Request Sender - Live Demo")
    print("=" * 70)
    
    automation = SimpleNetworkAutomation()
    
    try:
        # Start the system
        await automation.start()
        
        # Demo 1: Basic requests
        print("\n📤 Demo 1: Basic HTTP Requests")
        print("-" * 40)
        
        basic_requests = [
            {
                'method': 'GET',
                'url': 'https://httpbin.org/uuid',
                'headers': {'X-Demo': 'basic-get'}
            },
            {
                'method': 'POST',
                'url': 'https://httpbin.org/post',
                'headers': {'Content-Type': 'application/json'},
                'body': {'demo': 'basic-post', 'timestamp': int(time.time())}
            },
            {
                'method': 'GET',
                'url': 'https://httpbin.org/json',
                'headers': {'Accept': 'application/json'}
            }
        ]
        
        for i, request in enumerate(basic_requests, 1):
            print(f"🔄 Sending request {i}: {request['method']} {request['url']}")
            result = await automation.send_request(**request)
            
            if result['success']:
                print(f"✅ Request {i} completed successfully ({result['duration']:.3f}s)")
            else:
                print(f"❌ Request {i} failed: {result.get('error', 'Unknown error')}")
        
        print(f"\n📊 Stats after basic requests: {automation.get_stats()}")
        
        # Demo 2: Batch processing
        print("\n📦 Demo 2: Batch Request Processing")
        print("-" * 40)
        
        batch_requests = [
            {'method': 'GET', 'url': 'https://httpbin.org/uuid'},
            {'method': 'GET', 'url': 'https://httpbin.org/uuid'},
            {'method': 'GET', 'url': 'https://httpbin.org/uuid'},
            {'method': 'GET', 'url': 'https://httpbin.org/uuid'},
            {'method': 'GET', 'url': 'https://httpbin.org/uuid'}
        ]
        
        print(f"🔄 Sending batch of {len(batch_requests)} requests...")
        batch_start = time.time()
        
        results = await automation.send_batch(batch_requests)
        
        batch_duration = time.time() - batch_start
        successful_batch = sum(1 for r in results if r['success'])
        
        print(f"✅ Batch completed: {successful_batch}/{len(results)} successful")
        print(f"⏱️  Batch duration: {batch_duration:.3f}s")
        print(f"🚀 Throughput: {len(results) / batch_duration:.2f} requests/second")
        
        # Demo 3: Authentication example
        print("\n🔐 Demo 3: Authentication Example")
        print("-" * 40)
        
        auth_request = {
            'method': 'GET',
            'url': 'https://httpbin.org/bearer',
            'headers': {'Authorization': 'Bearer demo-token-12345'}
        }
        
        print(f"🔄 Sending authenticated request...")
        result = await automation.send_request(**auth_request)
        
        if result['success']:
            print(f"✅ Authentication request successful")
            print(f"📋 Response data: {json.dumps(result['response_data'], indent=2)}")
        else:
            print(f"❌ Authentication request failed")
        
        # Demo 4: Error handling
        print("\n⚠️  Demo 4: Error Handling")
        print("-" * 40)
        
        error_requests = [
            {'method': 'GET', 'url': 'https://httpbin.org/status/404'},
            {'method': 'GET', 'url': 'https://httpbin.org/status/500'},
            {'method': 'GET', 'url': 'https://httpbin.org/delay/2', 'timeout': 1}  # Timeout
        ]
        
        for i, request in enumerate(error_requests, 1):
            print(f"🔄 Testing error scenario {i}: {request['url']}")
            result = await automation.send_request(**request)
            
            if result['success']:
                print(f"✅ Request {i} unexpectedly succeeded")
            else:
                error_msg = result.get('error', f"HTTP {result.get('status_code', 'Unknown')}")
                print(f"❌ Request {i} failed as expected: {error_msg}")
        
        # Demo 5: Performance test
        print("\n🏎️  Demo 5: Performance Test")
        print("-" * 40)
        
        perf_requests = [
            {'method': 'GET', 'url': 'https://httpbin.org/uuid'}
            for _ in range(20)
        ]
        
        print(f"🔄 Performance test: {len(perf_requests)} concurrent requests...")
        perf_start = time.time()
        
        perf_results = await automation.send_batch(perf_requests, max_concurrent=10)
        
        perf_duration = time.time() - perf_start
        perf_successful = sum(1 for r in perf_results if r['success'])
        
        print(f"✅ Performance test completed:")
        print(f"   📊 {perf_successful}/{len(perf_results)} successful")
        print(f"   ⏱️  Duration: {perf_duration:.3f}s")
        print(f"   🚀 Throughput: {len(perf_results) / perf_duration:.2f} requests/second")
        
        # Final statistics
        print("\n📈 Final Statistics")
        print("-" * 40)
        
        final_stats = automation.get_stats()
        print(f"Total Requests: {final_stats['total_requests']}")
        print(f"Successful Requests: {final_stats['successful_requests']}")
        print(f"Success Rate: {final_stats['success_rate']:.2%}")
        print(f"Uptime: {final_stats['uptime_seconds']:.2f}s")
        print(f"Average RPS: {final_stats['requests_per_second']:.2f}")
        
        print("\n" + "=" * 70)
        print("🎉 Demo completed successfully!")
        print("✅ All network automation features demonstrated")
        
        print("\n🔧 System Features Demonstrated:")
        features = [
            "✅ Asynchronous HTTP request processing",
            "✅ Concurrent batch request handling",
            "✅ Authentication support (Bearer tokens)",
            "✅ Error handling and timeout management",
            "✅ Performance monitoring and statistics",
            "✅ Request/response logging",
            "✅ JSON data handling",
            "✅ HTTP status code handling",
            "✅ Custom headers support",
            "✅ Configurable timeouts"
        ]
        
        for feature in features:
            print(f"   {feature}")
    
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        raise
    
    finally:
        await automation.stop()


if __name__ == "__main__":
    try:
        asyncio.run(run_comprehensive_demo())
    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()