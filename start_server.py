#!/usr/bin/env python3
"""
Simple web server for network automation interface
"""

import http.server
import socketserver
import os
import sys
import webbrowser
import threading
import time

def find_free_port():
    """Find an available port"""
    import socket
    for port in range(8085, 8095):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    return 8085

def start_server():
    """Start the web server"""
    # Change to the correct directory
    os.chdir('/Users/emrekocay/network_automation_sender')
    
    port = find_free_port()
    
    class MyHandler(http.server.SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header('Cache-Control', 'no-cache')
            super().end_headers()
    
    try:
        with socketserver.TCPServer(("", port), MyHandler) as httpd:
            print(f"\n🌐 Web Server Started Successfully!")
            print(f"📱 Access the interface at: http://localhost:{port}/interface.html")
            print(f"🔧 Server running on port: {port}")
            print(f"🛑 Press Ctrl+C to stop the server")
            print("=" * 60)
            
            # Auto-open browser after 2 seconds
            def open_browser():
                time.sleep(2)
                try:
                    webbrowser.open(f'http://localhost:{port}/interface.html')
                    print(f"🌐 Opened browser to http://localhost:{port}/interface.html")
                except:
                    pass
            
            browser_thread = threading.Thread(target=open_browser)
            browser_thread.daemon = True
            browser_thread.start()
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")

if __name__ == "__main__":
    start_server()