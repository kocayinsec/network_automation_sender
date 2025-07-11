#!/usr/bin/env python3
"""
Main entry point for Network Automation Request Sender
Command-line interface for the automation system
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
import yaml
import logging
from typing import Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core import NetworkAutomation, AutomationConfig, RequestPriority
from exceptions import NetworkAutomationError


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from file"""
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_file, 'r') as f:
        if config_file.suffix.lower() in ['.yaml', '.yml']:
            return yaml.safe_load(f)
        elif config_file.suffix.lower() == '.json':
            return json.load(f)
        else:
            raise ValueError(f"Unsupported config file format: {config_file.suffix}")


def create_automation_config(config_data: Dict[str, Any]) -> AutomationConfig:
    """Create AutomationConfig from configuration data"""
    system_config = config_data.get('system', {})
    
    return AutomationConfig(
        max_concurrent_requests=system_config.get('max_concurrent_requests', 50),
        request_timeout=system_config.get('request_timeout', 30),
        retry_count=system_config.get('retry_count', 3),
        retry_delay=system_config.get('retry_delay', 1.0),
        rate_limit_per_second=system_config.get('rate_limit_per_second', 100),
        enable_monitoring=system_config.get('enable_monitoring', True),
        enable_caching=system_config.get('enable_caching', True),
        cache_ttl=system_config.get('cache_ttl', 3600),
        log_level=system_config.get('log_level', 'INFO'),
        webhook_url=system_config.get('webhook_url'),
        custom_headers=system_config.get('custom_headers', {})
    )


def setup_logging(log_level: str = 'INFO'):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/automation.log')
        ]
    )


async def run_interactive_mode(automation: NetworkAutomation):
    """Run interactive mode for manual request submission"""
    print("🚀 Network Automation Request Sender - Interactive Mode")
    print("=" * 60)
    print("Commands:")
    print("  send <method> <url> [headers] [body] - Send a request")
    print("  status - Show system status")
    print("  metrics - Show metrics")
    print("  health - Show health status")
    print("  quit - Exit interactive mode")
    print("=" * 60)
    
    while True:
        try:
            command = input("\n> ").strip()
            
            if not command:
                continue
                
            if command == "quit":
                break
                
            parts = command.split()
            cmd = parts[0].lower()
            
            if cmd == "send":
                if len(parts) < 3:
                    print("Usage: send <method> <url> [headers] [body]")
                    continue
                
                method = parts[1].upper()
                url = parts[2]
                
                request_config = {
                    "method": method,
                    "url": url
                }
                
                # Parse headers if provided
                if len(parts) > 3:
                    try:
                        headers = json.loads(parts[3])
                        request_config["headers"] = headers
                    except json.JSONDecodeError:
                        print("Invalid JSON for headers")
                        continue
                
                # Parse body if provided
                if len(parts) > 4:
                    try:
                        body = json.loads(parts[4])
                        request_config["body"] = body
                    except json.JSONDecodeError:
                        print("Invalid JSON for body")
                        continue
                
                # Send request
                request_id = await automation.add_request(
                    request_config,
                    priority=RequestPriority.NORMAL
                )
                print(f"✓ Request {request_id} added to queue")
                
            elif cmd == "status":
                status = await automation.get_status()
                print(f"Status: {json.dumps(status, indent=2)}")
                
            elif cmd == "metrics":
                if automation.monitor:
                    metrics = await automation.monitor.get_metrics()
                    print(f"Metrics: {json.dumps(metrics, indent=2)}")
                else:
                    print("Monitoring not enabled")
                    
            elif cmd == "health":
                if automation.monitor:
                    health = await automation.monitor.get_health_status()
                    print(f"Health: {json.dumps(health, indent=2)}")
                else:
                    print("Monitoring not enabled")
                    
            else:
                print(f"Unknown command: {cmd}")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")


async def run_batch_mode(automation: NetworkAutomation, batch_file: str):
    """Run batch mode from file"""
    print(f"📄 Loading batch requests from: {batch_file}")
    
    with open(batch_file, 'r') as f:
        if batch_file.endswith('.json'):
            batch_data = json.load(f)
        else:
            batch_data = yaml.safe_load(f)
    
    requests = batch_data.get('requests', [])
    
    print(f"📤 Submitting {len(requests)} requests...")
    
    for i, request_config in enumerate(requests):
        priority_str = request_config.pop('priority', 'NORMAL')
        priority = getattr(RequestPriority, priority_str.upper())
        
        request_id = await automation.add_request(
            request_config,
            priority=priority
        )
        print(f"✓ Request {i+1} added: {request_id}")
    
    print("⏳ Waiting for requests to complete...")
    
    # Wait for queue to empty
    while True:
        status = await automation.get_status()
        if status['queue_size'] == 0:
            break
        await asyncio.sleep(1)
    
    print("✅ All requests completed")
    
    # Show final metrics
    if automation.monitor:
        metrics = await automation.monitor.get_metrics()
        print(f"\n📊 Final Metrics:")
        print(f"  Total completed: {metrics['counters'].get('requests.completed', 0)}")
        print(f"  Success rate: {metrics['gauges'].get('requests.success_rate', 0):.2%}")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Network Automation Request Sender')
    parser.add_argument('--config', '-c', default='config/default.yaml',
                       help='Configuration file path')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Run in interactive mode')
    parser.add_argument('--batch', '-b', type=str,
                       help='Run batch requests from file')
    parser.add_argument('--log-level', '-l', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    parser.add_argument('--dry-run', action='store_true',
                       help='Validate configuration without starting')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        logger.info(f"Loading configuration from: {args.config}")
        config_data = load_config(args.config)
        automation_config = create_automation_config(config_data)
        
        if args.dry_run:
            logger.info("✅ Configuration validation successful")
            return
        
        # Create automation instance
        automation = NetworkAutomation(automation_config)
        
        # Start system
        logger.info("🚀 Starting Network Automation System...")
        await automation.start()
        
        try:
            if args.interactive:
                await run_interactive_mode(automation)
            elif args.batch:
                await run_batch_mode(automation, args.batch)
            else:
                # Default mode - keep running
                logger.info("📡 System running... Press Ctrl+C to stop")
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    logger.info("⏹️  Shutdown requested by user")
        
        finally:
            logger.info("🛑 Stopping Network Automation System...")
            await automation.stop()
            logger.info("✅ System stopped successfully")
    
    except FileNotFoundError as e:
        logger.error(f"❌ Configuration file not found: {e}")
        sys.exit(1)
    except NetworkAutomationError as e:
        logger.error(f"❌ Automation error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())