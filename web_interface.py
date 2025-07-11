#!/usr/bin/env python3
"""
Web Interface for Network Automation Request Sender
Simple web UI for managing and monitoring requests
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import aiohttp
from aiohttp import web, WSMsgType
import aiohttp_jinja2
import jinja2
import weakref
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core import NetworkAutomation, AutomationConfig, RequestPriority
from monitor import AlertSeverity


class WebInterface:
    """Web interface for the network automation system"""
    
    def __init__(self, automation: NetworkAutomation):
        self.automation = automation
        self.app = web.Application()
        self.websockets = weakref.WeakSet()
        self.request_results = {}
        self.setup_routes()
        self.setup_templates()
        
    def setup_routes(self):
        """Setup web routes"""
        # Static routes
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/dashboard', self.dashboard)
        self.app.router.add_get('/api/status', self.api_status)
        self.app.router.add_get('/api/metrics', self.api_metrics)
        self.app.router.add_get('/api/health', self.api_health)
        
        # Request management
        self.app.router.add_post('/api/request', self.api_send_request)
        self.app.router.add_post('/api/batch', self.api_send_batch)
        self.app.router.add_get('/api/requests', self.api_list_requests)
        
        # WebSocket for real-time updates
        self.app.router.add_get('/ws', self.websocket_handler)
        
        # Static files
        self.app.router.add_static('/static', Path(__file__).parent / 'static')
        
    def setup_templates(self):
        """Setup Jinja2 templates"""
        templates_dir = Path(__file__).parent / 'templates'
        templates_dir.mkdir(exist_ok=True)
        
        aiohttp_jinja2.setup(
            self.app,
            loader=jinja2.FileSystemLoader(str(templates_dir))
        )
        
    async def index(self, request):
        """Main page"""
        return web.Response(text=self.get_index_html(), content_type='text/html')
    
    async def dashboard(self, request):
        """Dashboard page"""
        return web.Response(text=self.get_dashboard_html(), content_type='text/html')
    
    async def api_status(self, request):
        """API endpoint for system status"""
        try:
            status = await self.automation.get_status()
            return web.json_response(status)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def api_metrics(self, request):
        """API endpoint for system metrics"""
        try:
            if self.automation.monitor:
                metrics = await self.automation.monitor.get_metrics()
                return web.json_response(metrics)
            else:
                return web.json_response({'error': 'Monitoring not enabled'}, status=400)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def api_health(self, request):
        """API endpoint for health status"""
        try:
            if self.automation.monitor:
                health = await self.automation.monitor.get_health_status()
                return web.json_response(health)
            else:
                return web.json_response({'error': 'Monitoring not enabled'}, status=400)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def api_send_request(self, request):
        """API endpoint to send a single request"""
        try:
            data = await request.json()
            
            # Extract priority
            priority_str = data.pop('priority', 'NORMAL')
            priority = getattr(RequestPriority, priority_str.upper())
            
            # Custom callback to store result
            async def result_callback(result):
                self.request_results[request_id] = result
                await self.broadcast_update({
                    'type': 'request_completed',
                    'request_id': request_id,
                    'result': result
                })
            
            # Send request
            request_id = await self.automation.add_request(
                data,
                priority=priority,
                callback=result_callback
            )
            
            return web.json_response({
                'success': True,
                'request_id': request_id,
                'message': 'Request queued successfully'
            })
            
        except Exception as e:
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)
    
    async def api_send_batch(self, request):
        """API endpoint to send batch requests"""
        try:
            data = await request.json()
            requests = data.get('requests', [])
            priority_str = data.get('priority', 'NORMAL')
            priority = getattr(RequestPriority, priority_str.upper())
            
            request_ids = await self.automation.add_batch_requests(
                requests,
                priority=priority
            )
            
            return web.json_response({
                'success': True,
                'request_ids': request_ids,
                'message': f'{len(request_ids)} requests queued successfully'
            })
            
        except Exception as e:
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)
    
    async def api_list_requests(self, request):
        """API endpoint to list recent requests"""
        try:
            # Return stored request results
            recent_results = dict(list(self.request_results.items())[-50:])  # Last 50
            return web.json_response({
                'success': True,
                'requests': recent_results
            })
        except Exception as e:
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)
    
    async def websocket_handler(self, request):
        """WebSocket handler for real-time updates"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websockets.add(ws)
        
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    if data.get('type') == 'ping':
                        await ws.send_str(json.dumps({'type': 'pong'}))
                except json.JSONDecodeError:
                    pass
            elif msg.type == WSMsgType.ERROR:
                print(f'WebSocket error: {ws.exception()}')
        
        return ws
    
    async def broadcast_update(self, message):
        """Broadcast message to all connected WebSockets"""
        if self.websockets:
            message_str = json.dumps(message)
            for ws in list(self.websockets):
                try:
                    await ws.send_str(message_str)
                except ConnectionResetError:
                    pass
    
    def get_index_html(self):
        """Generate main page HTML"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Network Automation Request Sender</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 10px; margin-bottom: 30px; }
        .header h1 { margin-bottom: 10px; }
        .header p { opacity: 0.8; }
        .card { background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .form-group input, .form-group select, .form-group textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        .form-group textarea { height: 100px; resize: vertical; }
        .btn { background: #3498db; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
        .btn:hover { background: #2980b9; }
        .btn-success { background: #27ae60; }
        .btn-success:hover { background: #219a52; }
        .btn-danger { background: #e74c3c; }
        .btn-danger:hover { background: #c0392b; }
        .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .status-card { background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .status-card h3 { margin-bottom: 10px; color: #2c3e50; }
        .status-value { font-size: 2em; font-weight: bold; color: #3498db; }
        .log-area { background: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 5px; height: 200px; overflow-y: auto; font-family: monospace; }
        .tabs { display: flex; margin-bottom: 20px; }
        .tab { padding: 10px 20px; background: #ecf0f1; border: 1px solid #bdc3c7; cursor: pointer; }
        .tab.active { background: #3498db; color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .alert { padding: 15px; border-radius: 5px; margin-bottom: 15px; }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-danger { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .request-item { background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 10px; }
        .request-item .method { font-weight: bold; color: #2c3e50; }
        .request-item .url { color: #3498db; word-break: break-all; }
        .request-item .status { float: right; padding: 5px 10px; border-radius: 3px; color: white; }
        .status-success { background: #27ae60; }
        .status-error { background: #e74c3c; }
        .status-pending { background: #f39c12; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Network Automation Request Sender</h1>
            <p>Advanced HTTP request automation with monitoring and queue management</p>
        </div>
        
        <div class="status-grid" id="statusGrid">
            <div class="status-card">
                <h3>Queue Size</h3>
                <div class="status-value" id="queueSize">0</div>
            </div>
            <div class="status-card">
                <h3>Active Requests</h3>
                <div class="status-value" id="activeRequests">0</div>
            </div>
            <div class="status-card">
                <h3>Success Rate</h3>
                <div class="status-value" id="successRate">0%</div>
            </div>
            <div class="status-card">
                <h3>Total Processed</h3>
                <div class="status-value" id="totalProcessed">0</div>
            </div>
        </div>
        
        <div class="tabs">
            <div class="tab active" onclick="showTab('single')">Single Request</div>
            <div class="tab" onclick="showTab('batch')">Batch Requests</div>
            <div class="tab" onclick="showTab('monitor')">Monitor</div>
            <div class="tab" onclick="showTab('history')">History</div>
        </div>
        
        <div id="single" class="tab-content active">
            <div class="card">
                <h2>Send Single Request</h2>
                <form id="singleForm">
                    <div class="grid-2">
                        <div class="form-group">
                            <label>Method</label>
                            <select name="method">
                                <option value="GET">GET</option>
                                <option value="POST">POST</option>
                                <option value="PUT">PUT</option>
                                <option value="DELETE">DELETE</option>
                                <option value="PATCH">PATCH</option>
                                <option value="HEAD">HEAD</option>
                                <option value="OPTIONS">OPTIONS</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Priority</label>
                            <select name="priority">
                                <option value="NORMAL">Normal</option>
                                <option value="HIGH">High</option>
                                <option value="CRITICAL">Critical</option>
                                <option value="LOW">Low</option>
                            </select>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>URL</label>
                        <input type="url" name="url" placeholder="https://api.example.com/endpoint" required>
                    </div>
                    <div class="form-group">
                        <label>Headers (JSON)</label>
                        <textarea name="headers" placeholder='{"Authorization": "Bearer token", "Content-Type": "application/json"}'></textarea>
                    </div>
                    <div class="form-group">
                        <label>Body (JSON)</label>
                        <textarea name="body" placeholder='{"key": "value"}'></textarea>
                    </div>
                    <button type="submit" class="btn">Send Request</button>
                </form>
            </div>
        </div>
        
        <div id="batch" class="tab-content">
            <div class="card">
                <h2>Send Batch Requests</h2>
                <form id="batchForm">
                    <div class="form-group">
                        <label>Priority</label>
                        <select name="priority">
                            <option value="NORMAL">Normal</option>
                            <option value="HIGH">High</option>
                            <option value="CRITICAL">Critical</option>
                            <option value="LOW">Low</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Requests (JSON Array)</label>
                        <textarea name="requests" rows="10" placeholder='[{"method": "GET", "url": "https://api.example.com/1"}, {"method": "POST", "url": "https://api.example.com/2", "body": {"data": "value"}}]'></textarea>
                    </div>
                    <button type="submit" class="btn">Send Batch</button>
                </form>
            </div>
        </div>
        
        <div id="monitor" class="tab-content">
            <div class="card">
                <h2>System Monitor</h2>
                <div class="grid-2">
                    <div>
                        <h3>System Health</h3>
                        <div id="healthStatus">Loading...</div>
                    </div>
                    <div>
                        <h3>Performance Metrics</h3>
                        <div id="performanceMetrics">Loading...</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div id="history" class="tab-content">
            <div class="card">
                <h2>Request History</h2>
                <div id="requestHistory">Loading...</div>
            </div>
        </div>
        
        <div class="card">
            <h2>Live Log</h2>
            <div class="log-area" id="liveLog">
                <div>System ready. Waiting for requests...</div>
            </div>
        </div>
    </div>
    
    <script>
        let ws;
        let requestHistory = [];
        
        function connectWebSocket() {
            ws = new WebSocket('ws://localhost:8080/ws');
            
            ws.onopen = function() {
                addLog('WebSocket connected');
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            };
            
            ws.onclose = function() {
                addLog('WebSocket disconnected. Reconnecting...');
                setTimeout(connectWebSocket, 3000);
            };
            
            ws.onerror = function(error) {
                addLog('WebSocket error: ' + error);
            };
        }
        
        function handleWebSocketMessage(data) {
            if (data.type === 'request_completed') {
                addLog('Request ' + data.request_id + ' completed: ' + (data.result.success ? 'SUCCESS' : 'FAILED'));
                requestHistory.push({
                    id: data.request_id,
                    result: data.result,
                    timestamp: new Date()
                });
                updateHistory();
            }
        }
        
        function showTab(tabName) {
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            event.target.classList.add('active');
            document.getElementById(tabName).classList.add('active');
        }
        
        function addLog(message) {
            const logArea = document.getElementById('liveLog');
            const timestamp = new Date().toLocaleTimeString();
            const logEntry = document.createElement('div');
            logEntry.textContent = timestamp + ' - ' + message;
            logArea.appendChild(logEntry);
            logArea.scrollTop = logArea.scrollHeight;
        }
        
        function updateStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('queueSize').textContent = data.queue_size || 0;
                    if (data.metrics) {
                        document.getElementById('activeRequests').textContent = data.metrics.requests?.active || 0;
                        document.getElementById('totalProcessed').textContent = data.metrics.requests?.total_processed || 0;
                    }
                })
                .catch(error => console.error('Error fetching status:', error));
            
            fetch('/api/metrics')
                .then(response => response.json())
                .then(data => {
                    if (data.gauges) {
                        const successRate = (data.gauges.requests_success_rate || 0) * 100;
                        document.getElementById('successRate').textContent = successRate.toFixed(1) + '%';
                    }
                })
                .catch(error => console.error('Error fetching metrics:', error));
        }
        
        function updateHistory() {
            const historyDiv = document.getElementById('requestHistory');
            historyDiv.innerHTML = '';
            
            requestHistory.slice(-20).reverse().forEach(item => {
                const div = document.createElement('div');
                div.className = 'request-item';
                div.innerHTML = `
                    <div class="method">${item.result.method || 'UNKNOWN'}</div>
                    <div class="url">${item.result.url || 'N/A'}</div>
                    <div class="status ${item.result.success ? 'status-success' : 'status-error'}">
                        ${item.result.success ? 'SUCCESS' : 'FAILED'}
                    </div>
                    <div style="clear: both; margin-top: 5px; font-size: 0.9em; color: #666;">
                        ${item.timestamp.toLocaleString()}
                    </div>
                `;
                historyDiv.appendChild(div);
            });
        }
        
        document.getElementById('singleForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = {
                method: formData.get('method'),
                url: formData.get('url'),
                priority: formData.get('priority')
            };
            
            if (formData.get('headers')) {
                try {
                    data.headers = JSON.parse(formData.get('headers'));
                } catch (err) {
                    alert('Invalid JSON in headers');
                    return;
                }
            }
            
            if (formData.get('body')) {
                try {
                    data.body = JSON.parse(formData.get('body'));
                } catch (err) {
                    alert('Invalid JSON in body');
                    return;
                }
            }
            
            fetch('/api/request', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    addLog('Request queued: ' + result.request_id);
                    e.target.reset();
                } else {
                    addLog('Error: ' + result.error);
                }
            })
            .catch(error => {
                addLog('Network error: ' + error);
            });
        });
        
        document.getElementById('batchForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(e.target);
            
            let requests;
            try {
                requests = JSON.parse(formData.get('requests'));
            } catch (err) {
                alert('Invalid JSON in requests');
                return;
            }
            
            const data = {
                requests: requests,
                priority: formData.get('priority')
            };
            
            fetch('/api/batch', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    addLog('Batch queued: ' + result.request_ids.length + ' requests');
                    e.target.reset();
                } else {
                    addLog('Error: ' + result.error);
                }
            })
            .catch(error => {
                addLog('Network error: ' + error);
            });
        });
        
        // Initialize
        connectWebSocket();
        updateStatus();
        setInterval(updateStatus, 5000);
    </script>
</body>
</html>
        """
    
    async def start_server(self, host='localhost', port=8080):
        """Start the web server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        print(f"🌐 Web interface available at http://{host}:{port}")
        return runner


async def main():
    """Main function to run web interface"""
    # Create automation config
    config = AutomationConfig(
        max_concurrent_requests=20,
        enable_monitoring=True,
        enable_caching=True,
        log_level="INFO"
    )
    
    # Create automation instance
    automation = NetworkAutomation(config)
    
    # Create web interface
    web_interface = WebInterface(automation)
    
    try:
        # Start automation system
        print("🚀 Starting Network Automation System...")
        await automation.start()
        
        # Start web server
        runner = await web_interface.start_server(host='localhost', port=8080)
        
        print("\n" + "="*60)
        print("🎯 Network Automation Web Interface")
        print("="*60)
        print("📱 Open your browser and go to: http://localhost:8080")
        print("💡 Features available:")
        print("   • Send single HTTP requests")
        print("   • Send batch requests")
        print("   • Real-time monitoring")
        print("   • Request history")
        print("   • Live system logs")
        print("   • System health metrics")
        print("\n⌨️  Press Ctrl+C to stop the server")
        print("="*60)
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
        
    finally:
        # Clean shutdown
        await automation.stop()
        await runner.cleanup()
        print("✅ Server stopped")


if __name__ == "__main__":
    asyncio.run(main())