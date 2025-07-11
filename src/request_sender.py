"""
Advanced Request Sender
Handles the actual sending of network requests with advanced features
"""

import asyncio
import aiohttp
import time
from typing import Dict, Any, Optional, List, Tuple
import ssl
import certifi
from aiohttp import ClientTimeout, ClientError, ServerTimeoutError
import logging
from urllib.parse import urlparse
import socket
import json

from .exceptions import RequestSendError


class RequestSender:
    """
    Sophisticated request sender with:
    - Connection pooling
    - SSL/TLS support
    - Proxy support
    - Response parsing
    - Performance metrics
    - Error handling
    """

    def __init__(self, config: Any):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._sessions = {}
        self._connector_config = {
            "limit": 100,
            "limit_per_host": 30,
            "ttl_dns_cache": 300,
            "force_close": False
        }
        self._ssl_context = self._create_ssl_context()

    async def send(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a network request
        
        Args:
            request: Request dictionary with method, url, headers, etc.
            
        Returns:
            Response dictionary with status, data, headers, etc.
        """
        start_time = time.time()
        
        try:
            # Get or create session for the host
            session = await self._get_session(request["url"])
            
            # Prepare request parameters
            kwargs = self._prepare_request_kwargs(request)
            
            # Send request
            async with session.request(**kwargs) as response:
                # Parse response
                result = await self._parse_response(response)
                
                # Add performance metrics
                result["duration"] = time.time() - start_time
                result["request_id"] = request.get("headers", {}).get("X-Request-ID", "")
                
                return result
                
        except ServerTimeoutError:
            return {
                "success": False,
                "error": "Request timeout",
                "duration": time.time() - start_time,
                "error_type": "timeout"
            }
        except ClientError as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time,
                "error_type": "client_error"
            }
        except Exception as e:
            self.logger.error(f"Request failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time,
                "error_type": "unknown"
            }

    async def send_batch(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Send multiple requests concurrently"""
        tasks = [self.send(request) for request in requests]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def _get_session(self, url: str) -> aiohttp.ClientSession:
        """Get or create session for a host"""
        parsed_url = urlparse(url)
        host = parsed_url.netloc
        
        if host not in self._sessions:
            # Create connector with connection pooling
            connector = aiohttp.TCPConnector(
                **self._connector_config,
                ssl=self._ssl_context
            )
            
            # Create session
            timeout = ClientTimeout(
                total=self.config.request_timeout,
                connect=10,
                sock_connect=10,
                sock_read=self.config.request_timeout
            )
            
            self._sessions[host] = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                trust_env=True  # Use system proxy settings
            )
        
        return self._sessions[host]

    def _prepare_request_kwargs(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare kwargs for aiohttp request"""
        kwargs = {
            "method": request["method"],
            "url": request["url"],
            "headers": request.get("headers", {}),
            "timeout": ClientTimeout(total=request.get("timeout", self.config.request_timeout))
        }
        
        # Handle body/data
        if "data" in request:
            if isinstance(request["data"], (dict, list)):
                kwargs["json"] = request["data"]
            else:
                kwargs["data"] = request["data"]
        
        # Handle cookies
        if "cookies" in request:
            kwargs["cookies"] = request["cookies"]
        
        # Handle proxy
        if "proxy" in request:
            kwargs["proxy"] = request["proxy"]
        elif hasattr(self.config, "proxy_url") and self.config.proxy_url:
            kwargs["proxy"] = self.config.proxy_url
        
        # Handle SSL verification
        if "verify_ssl" in request:
            kwargs["ssl"] = request["verify_ssl"]
        
        # Handle redirects
        kwargs["allow_redirects"] = request.get("allow_redirects", True)
        kwargs["max_redirects"] = request.get("max_redirects", 10)
        
        return kwargs

    async def _parse_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Parse response into standardized format"""
        result = {
            "success": 200 <= response.status < 400,
            "status_code": response.status,
            "headers": dict(response.headers),
            "url": str(response.url),
            "method": response.method
        }
        
        # Parse body based on content type
        content_type = response.headers.get("Content-Type", "").lower()
        
        try:
            if "application/json" in content_type:
                result["data"] = await response.json()
                result["data_type"] = "json"
            elif "text/" in content_type or "xml" in content_type:
                result["data"] = await response.text()
                result["data_type"] = "text"
            else:
                result["data"] = await response.read()
                result["data_type"] = "binary"
        except Exception as e:
            self.logger.warning(f"Failed to parse response body: {e}")
            result["data"] = await response.read()
            result["data_type"] = "binary"
        
        # Add response metadata
        result["metadata"] = {
            "content_length": response.headers.get("Content-Length"),
            "content_type": content_type,
            "encoding": response.get_encoding(),
            "cookies": self._extract_cookies(response)
        }
        
        # Handle redirects
        if response.history:
            result["redirects"] = [
                {"status": r.status, "url": str(r.url)}
                for r in response.history
            ]
        
        return result

    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context with proper configuration"""
        context = ssl.create_default_context(cafile=certifi.where())
        
        # Configure SSL/TLS settings
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        
        # Set minimum TLS version
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        
        # Disable weak ciphers
        context.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS")
        
        return context

    def _extract_cookies(self, response: aiohttp.ClientResponse) -> Dict[str, str]:
        """Extract cookies from response"""
        cookies = {}
        for cookie in response.cookies.values():
            cookies[cookie.key] = cookie.value
        return cookies

    async def test_connectivity(self, url: str) -> Dict[str, Any]:
        """Test connectivity to a URL"""
        try:
            start_time = time.time()
            
            # DNS resolution
            parsed_url = urlparse(url)
            try:
                dns_start = time.time()
                addr_info = await asyncio.get_event_loop().getaddrinfo(
                    parsed_url.hostname,
                    parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
                )
                dns_time = time.time() - dns_start
                ip_addresses = list(set(info[4][0] for info in addr_info))
            except Exception as e:
                return {
                    "success": False,
                    "error": f"DNS resolution failed: {e}",
                    "dns_time": None
                }
            
            # TCP connection test
            tcp_start = time.time()
            for ip in ip_addresses:
                try:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(
                            ip,
                            parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
                        ),
                        timeout=5
                    )
                    writer.close()
                    await writer.wait_closed()
                    tcp_time = time.time() - tcp_start
                    break
                except Exception:
                    continue
            else:
                return {
                    "success": False,
                    "error": "TCP connection failed to all IPs",
                    "dns_time": dns_time
                }
            
            # HTTP request test
            http_start = time.time()
            response = await self.send({
                "method": "HEAD",
                "url": url,
                "timeout": 10
            })
            http_time = time.time() - http_start
            
            return {
                "success": response["success"],
                "total_time": time.time() - start_time,
                "dns_time": dns_time,
                "tcp_time": tcp_time,
                "http_time": http_time,
                "ip_addresses": ip_addresses,
                "status_code": response.get("status_code")
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "total_time": time.time() - start_time
            }

    async def download_file(self, url: str, file_path: str, chunk_size: int = 8192) -> Dict[str, Any]:
        """Download file with progress tracking"""
        try:
            session = await self._get_session(url)
            
            async with session.get(url) as response:
                if response.status != 200:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}",
                        "status_code": response.status
                    }
                
                total_size = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                
                with open(file_path, "wb") as file:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        file.write(chunk)
                        downloaded += len(chunk)
                        
                        # Progress callback could be added here
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            self.logger.debug(f"Download progress: {progress:.1f}%")
                
                return {
                    "success": True,
                    "file_path": file_path,
                    "size": downloaded,
                    "content_type": response.headers.get("Content-Type")
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def stream_response(self, request: Dict[str, Any], callback: callable):
        """Stream response data to a callback"""
        try:
            session = await self._get_session(request["url"])
            kwargs = self._prepare_request_kwargs(request)
            
            async with session.request(**kwargs) as response:
                async for chunk in response.content.iter_any():
                    await callback(chunk, response)
                    
                return {
                    "success": True,
                    "status_code": response.status,
                    "headers": dict(response.headers)
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def websocket_connect(self, url: str, **kwargs) -> aiohttp.ClientWebSocketResponse:
        """Establish WebSocket connection"""
        session = await self._get_session(url)
        return await session.ws_connect(url, **kwargs)

    async def close(self):
        """Close all sessions"""
        for session in self._sessions.values():
            await session.close()
        self._sessions.clear()

    def __del__(self):
        """Cleanup sessions on deletion"""
        if hasattr(self, "_sessions"):
            for session in self._sessions.values():
                if not session.closed:
                    asyncio.create_task(session.close())