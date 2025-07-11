#!/usr/bin/env python3
"""
Network Automation Web Server
Simple web interface on an available port
"""

import socket
import webbrowser
import threading
import time
from simple_web import start_server


def find_free_port():
    """Find an available port"""
    for port in range(8081, 8090):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    return 8081


def start_with_free_port():
    """Start server on available port"""
    port = find_free_port()
    
    print("🚀 Network Automation Request Sender")
    print("=" * 50)
    print(f"🌐 Starting web server on port {port}...")
    print(f"📱 Open your browser and go to: http://localhost:{port}")
    print(f"🛑 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Start server
    from http.server import HTTPServer
    from simple_web import SimpleWebHandler
    
    server_address = ('', port)
    httpd = HTTPServer(server_address, SimpleWebHandler)
    
    # Auto-open browser
    def open_browser():
        time.sleep(1)
        webbrowser.open(f'http://localhost:{port}')
    
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
        httpd.shutdown()


if __name__ == "__main__":
    start_with_free_port()