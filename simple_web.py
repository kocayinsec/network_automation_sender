#!/usr/bin/env python3
"""
Simple Web Interface for Network Automation Request Sender
Uses only built-in Python modules
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import threading
import webbrowser
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from core import NetworkAutomation, AutomationConfig, RequestPriority
    HAS_AUTOMATION = True
except ImportError:
    HAS_AUTOMATION = False
    print("⚠️  Core automation modules not available. Running in demo mode.")


class SimpleWebHandler(BaseHTTPRequestHandler):
    """Simple HTTP request handler"""
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.get_main_page().encode())
        
        elif self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            status = {
                "running": True,
                "queue_size": 0,
                "cache_entries": 0,
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(status).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'404 Not Found')
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/api/request':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode())
                
                # Simulate request processing
                response = {
                    "success": True,
                    "request_id": f"req_{int(time.time())}",
                    "message": "Request queued successfully",
                    "data": data
                }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                
            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_response = {"success": False, "error": "Invalid JSON"}
                self.wfile.write(json.dumps(error_response).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'404 Not Found')
    
    def log_message(self, format, *args):
        """Override to reduce log spam"""
        pass
    
    def get_main_page(self):
        """Generate the main HTML page"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Network Automation Request Sender</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { 
            max-width: 1000px; 
            margin: 0 auto; 
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        .header { 
            background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
            color: white; 
            padding: 30px; 
            text-align: center;
        }
        .header h1 { 
            font-size: 2.5em; 
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .header p { 
            opacity: 0.9; 
            font-size: 1.1em;
        }
        .main-content { padding: 30px; }
        .status-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 20px; 
            margin-bottom: 30px; 
        }
        .status-card { 
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 20px; 
            border-radius: 10px; 
            text-align: center;
            border: 1px solid #dee2e6;
        }
        .status-card h3 { 
            margin-bottom: 10px; 
            color: #2c3e50;
            font-size: 1.1em;
        }
        .status-value { 
            font-size: 2em; 
            font-weight: bold; 
            color: #3498db;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
        }
        .form-section { 
            background: #f8f9fa;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 20px;
            border: 1px solid #dee2e6;
        }
        .form-section h2 { 
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 1.5em;
        }
        .form-group { 
            margin-bottom: 15px; 
        }
        .form-group label { 
            display: block; 
            margin-bottom: 5px; 
            font-weight: bold;
            color: #495057;
        }
        .form-group input, .form-group select, .form-group textarea { 
            width: 100%; 
            padding: 12px; 
            border: 2px solid #e9ecef; 
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s ease;
        }
        .form-group input:focus, .form-group select:focus, .form-group textarea:focus {
            outline: none;
            border-color: #3498db;
            box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
        }
        .form-group textarea { 
            height: 100px; 
            resize: vertical; 
            font-family: monospace;
        }
        .btn { 
            background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
            color: white; 
            padding: 12px 25px; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer; 
            font-size: 16px;
            font-weight: bold;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(52, 152, 219, 0.3);
        }
        .btn:hover { 
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(52, 152, 219, 0.4);
        }
        .btn:active {
            transform: translateY(0);
        }
        .grid-2 { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 20px; 
        }
        .response-area { 
            background: #2c3e50;
            color: #ecf0f1;
            padding: 20px;
            border-radius: 10px;
            margin-top: 20px;
            font-family: monospace;
            max-height: 300px;
            overflow-y: auto;
            border: 1px solid #34495e;
        }
        .response-area h3 {
            color: #3498db;
            margin-bottom: 10px;
        }
        .alert { 
            padding: 15px; 
            border-radius: 8px; 
            margin-bottom: 15px;
            border: 1px solid;
        }
        .alert-success { 
            background: #d4edda; 
            color: #155724; 
            border-color: #c3e6cb; 
        }
        .alert-danger { 
            background: #f8d7da; 
            color: #721c24; 
            border-color: #f5c6cb; 
        }
        .example-section {
            background: #e8f4f8;
            padding: 20px;
            border-radius: 10px;
            margin-top: 20px;
            border: 1px solid #bee5eb;
        }
        .example-section h3 {
            color: #2c3e50;
            margin-bottom: 15px;
        }
        .example-item {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            border: 1px solid #c3e6cb;
        }
        .example-item h4 {
            color: #495057;
            margin-bottom: 10px;
        }
        .example-item code {
            background: #f1f3f4;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Network Automation</h1>
            <p>Advanced HTTP Request Automation System</p>
        </div>
        
        <div class="main-content">
            <div class="status-grid">
                <div class="status-card">
                    <h3>System Status</h3>
                    <div class="status-value" id="systemStatus">Ready</div>
                </div>
                <div class="status-card">
                    <h3>Queue Size</h3>
                    <div class="status-value" id="queueSize">0</div>
                </div>
                <div class="status-card">
                    <h3>Requests Sent</h3>
                    <div class="status-value" id="requestCount">0</div>
                </div>
                <div class="status-card">
                    <h3>Success Rate</h3>
                    <div class="status-value" id="successRate">100%</div>
                </div>
            </div>
            
            <div class="form-section">
                <h2>📤 Send HTTP Request</h2>
                <form id="requestForm">
                    <div class="grid-2">
                        <div class="form-group">
                            <label>Method</label>
                            <select name="method" id="method">
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
                            <select name="priority" id="priority">
                                <option value="NORMAL">Normal</option>
                                <option value="HIGH">High</option>
                                <option value="CRITICAL">Critical</option>
                                <option value="LOW">Low</option>
                            </select>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>URL</label>
                        <input type="url" name="url" id="url" placeholder="https://api.example.com/endpoint" required>
                    </div>
                    <div class="form-group">
                        <label>Headers (JSON format)</label>
                        <textarea name="headers" id="headers" placeholder='{"Authorization": "Bearer your-token", "Content-Type": "application/json"}'></textarea>
                    </div>
                    <div class="form-group">
                        <label>Body (JSON format)</label>
                        <textarea name="body" id="body" placeholder='{"key": "value", "data": "your-data"}'></textarea>
                    </div>
                    <button type="submit" class="btn">🚀 Send Request</button>
                </form>
            </div>
            
            <div class="response-area" id="responseArea">
                <h3>📋 Response Log</h3>
                <div id="responseLog">Ready to send requests...</div>
            </div>
            
            <div class="example-section">
                <h3>💡 Quick Examples</h3>
                <div class="example-item">
                    <h4>GET Request</h4>
                    <p><strong>URL:</strong> <code>https://httpbin.org/get</code></p>
                    <p><strong>Headers:</strong> <code>{"User-Agent": "NetworkAutomation/1.0"}</code></p>
                </div>
                <div class="example-item">
                    <h4>POST Request</h4>
                    <p><strong>URL:</strong> <code>https://httpbin.org/post</code></p>
                    <p><strong>Headers:</strong> <code>{"Content-Type": "application/json"}</code></p>
                    <p><strong>Body:</strong> <code>{"message": "Hello World", "timestamp": "2024-01-01T12:00:00Z"}</code></p>
                </div>
                <div class="example-item">
                    <h4>With Authentication</h4>
                    <p><strong>URL:</strong> <code>https://httpbin.org/bearer</code></p>
                    <p><strong>Headers:</strong> <code>{"Authorization": "Bearer your-token-here"}</code></p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let requestCount = 0;
        let successCount = 0;
        
        function updateStats() {
            document.getElementById('requestCount').textContent = requestCount;
            const successRate = requestCount > 0 ? ((successCount / requestCount) * 100).toFixed(1) : 100;
            document.getElementById('successRate').textContent = successRate + '%';
        }
        
        function addToLog(message, isError = false) {
            const logDiv = document.getElementById('responseLog');
            const timestamp = new Date().toLocaleTimeString();
            const logEntry = document.createElement('div');
            logEntry.style.marginBottom = '10px';
            logEntry.style.padding = '10px';
            logEntry.style.borderRadius = '5px';
            logEntry.style.backgroundColor = isError ? '#e74c3c' : '#27ae60';
            logEntry.innerHTML = `<strong>${timestamp}:</strong> ${message}`;
            logDiv.appendChild(logEntry);
            logDiv.scrollTop = logDiv.scrollHeight;
        }
        
        function fillExample(type) {
            if (type === 'get') {
                document.getElementById('method').value = 'GET';
                document.getElementById('url').value = 'https://httpbin.org/get';
                document.getElementById('headers').value = '{"User-Agent": "NetworkAutomation/1.0"}';
                document.getElementById('body').value = '';
            } else if (type === 'post') {
                document.getElementById('method').value = 'POST';
                document.getElementById('url').value = 'https://httpbin.org/post';
                document.getElementById('headers').value = '{"Content-Type": "application/json"}';
                document.getElementById('body').value = '{"message": "Hello World", "timestamp": "' + new Date().toISOString() + '"}';
            }
        }
        
        document.getElementById('requestForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const data = {
                method: formData.get('method'),
                url: formData.get('url'),
                priority: formData.get('priority')
            };
            
            // Parse headers
            const headersText = formData.get('headers');
            if (headersText && headersText.trim()) {
                try {
                    data.headers = JSON.parse(headersText);
                } catch (err) {
                    addToLog('❌ Invalid JSON in headers: ' + err.message, true);
                    return;
                }
            }
            
            // Parse body
            const bodyText = formData.get('body');
            if (bodyText && bodyText.trim()) {
                try {
                    data.body = JSON.parse(bodyText);
                } catch (err) {
                    addToLog('❌ Invalid JSON in body: ' + err.message, true);
                    return;
                }
            }
            
            // Send request
            addToLog('📤 Sending request to ' + data.url);
            requestCount++;
            updateStats();
            
            fetch('/api/request', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    successCount++;
                    addToLog('✅ Request successful! ID: ' + result.request_id);
                    addToLog('📋 Method: ' + data.method + ', URL: ' + data.url);
                } else {
                    addToLog('❌ Request failed: ' + result.error, true);
                }
                updateStats();
            })
            .catch(error => {
                addToLog('❌ Network error: ' + error.message, true);
                updateStats();
            });
        });
        
        // Add example buttons
        document.addEventListener('DOMContentLoaded', function() {
            const examples = document.querySelectorAll('.example-item');
            examples.forEach((example, index) => {
                const button = document.createElement('button');
                button.textContent = '📋 Use This Example';
                button.className = 'btn';
                button.style.marginTop = '10px';
                button.style.fontSize = '14px';
                button.style.padding = '8px 15px';
                
                button.onclick = function() {
                    if (index === 0) fillExample('get');
                    else if (index === 1) fillExample('post');
                    else if (index === 2) {
                        document.getElementById('method').value = 'GET';
                        document.getElementById('url').value = 'https://httpbin.org/bearer';
                        document.getElementById('headers').value = '{"Authorization": "Bearer demo-token-123"}';
                        document.getElementById('body').value = '';
                    }
                };
                
                example.appendChild(button);
            });
        });
        
        // Update status periodically
        setInterval(function() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('queueSize').textContent = data.queue_size;
                })
                .catch(error => console.log('Status update failed:', error));
        }, 5000);
    </script>
</body>
</html>
        """


def start_server(port=8080):
    """Start the web server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, SimpleWebHandler)
    
    print(f"🌐 Starting web server on port {port}...")
    print(f"📱 Open your browser and go to: http://localhost:{port}")
    print(f"🛑 Press Ctrl+C to stop the server")
    
    try:
        # Try to open browser automatically
        def open_browser():
            time.sleep(1)
            webbrowser.open(f'http://localhost:{port}')
        
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
        
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
        httpd.shutdown()


if __name__ == "__main__":
    start_server()