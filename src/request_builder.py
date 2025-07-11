"""
Advanced Request Builder
Constructs complex network requests with validation and transformation
"""

import json
import re
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs
import base64
import hashlib
import hmac
import time
from datetime import datetime
import jwt
import xml.etree.ElementTree as ET
from dataclasses import dataclass
import yaml

from .exceptions import RequestBuildError


@dataclass
class AuthConfig:
    """Authentication configuration"""
    type: str  # basic, bearer, api_key, oauth2, jwt, custom
    credentials: Dict[str, Any]
    placement: str = "header"  # header, query, body


class RequestBuilder:
    """
    Sophisticated request builder with support for:
    - Multiple authentication methods
    - Dynamic parameter injection
    - Request templating
    - Protocol transformation
    - Payload encryption
    - Request signing
    """

    def __init__(self):
        self.templates = {}
        self.transformers = {}
        self.validators = {}
        self._setup_default_transformers()
        self._setup_default_validators()

    def build(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build a request from configuration
        
        Args:
            config: Request configuration including URL, method, headers, etc.
            
        Returns:
            Built request ready for sending
        """
        try:
            # Apply template if specified
            if "template" in config:
                config = self._apply_template(config)
            
            # Validate configuration
            self._validate_config(config)
            
            # Build base request
            request = {
                "method": config.get("method", "GET").upper(),
                "url": self._build_url(config),
                "headers": self._build_headers(config),
                "timeout": config.get("timeout", 30)
            }
            
            # Add authentication
            if "auth" in config:
                self._add_authentication(request, config["auth"])
            
            # Build body
            if config.get("method", "GET").upper() in ["POST", "PUT", "PATCH", "DELETE"]:
                request["data"] = self._build_body(config)
            
            # Apply transformations
            if "transformations" in config:
                request = self._apply_transformations(request, config["transformations"])
            
            # Sign request if required
            if config.get("sign_request"):
                self._sign_request(request, config.get("signing_config", {}))
            
            return request
            
        except Exception as e:
            raise RequestBuildError(f"Failed to build request: {str(e)}")

    def register_template(self, name: str, template: Dict[str, Any]):
        """Register a request template"""
        self.templates[name] = template

    def register_transformer(self, name: str, transformer: callable):
        """Register a custom transformer"""
        self.transformers[name] = transformer

    def register_validator(self, name: str, validator: callable):
        """Register a custom validator"""
        self.validators[name] = validator

    def _apply_template(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a template to the configuration"""
        template_name = config.pop("template")
        if template_name not in self.templates:
            raise RequestBuildError(f"Template '{template_name}' not found")
        
        template = self.templates[template_name].copy()
        
        # Merge config with template
        for key, value in config.items():
            if isinstance(value, dict) and key in template and isinstance(template[key], dict):
                template[key].update(value)
            else:
                template[key] = value
        
        return template

    def _validate_config(self, config: Dict[str, Any]):
        """Validate request configuration"""
        # Required fields
        if "url" not in config:
            raise RequestBuildError("URL is required")
        
        # Validate URL
        parsed_url = urlparse(config["url"])
        if not parsed_url.scheme:
            raise RequestBuildError("URL must include scheme (http/https)")
        
        # Validate method
        valid_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
        method = config.get("method", "GET").upper()
        if method not in valid_methods:
            raise RequestBuildError(f"Invalid method: {method}")
        
        # Run custom validators
        for validator_name in config.get("validators", []):
            if validator_name in self.validators:
                self.validators[validator_name](config)

    def _build_url(self, config: Dict[str, Any]) -> str:
        """Build complete URL with parameters"""
        url = config["url"]
        
        # Handle URL parameters
        if "url_params" in config:
            for key, value in config["url_params"].items():
                placeholder = f"{{{key}}}"
                if placeholder in url:
                    url = url.replace(placeholder, str(value))
        
        # Handle query parameters
        if "params" in config:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            
            # Merge with new params
            for key, value in config["params"].items():
                if isinstance(value, list):
                    query_params[key] = value
                else:
                    query_params[key] = [str(value)]
            
            # Rebuild URL
            new_query = urlencode(query_params, doseq=True)
            url = urlunparse(parsed_url._replace(query=new_query))
        
        return url

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Build request headers"""
        headers = {
            "User-Agent": "NetworkAutomation/1.0"
        }
        
        # Add custom headers
        if "headers" in config:
            headers.update(config["headers"])
        
        # Add content type based on body format
        if "body" in config and "Content-Type" not in headers:
            body_format = config.get("body_format", "json")
            content_types = {
                "json": "application/json",
                "xml": "application/xml",
                "form": "application/x-www-form-urlencoded",
                "multipart": "multipart/form-data",
                "text": "text/plain"
            }
            headers["Content-Type"] = content_types.get(body_format, "application/json")
        
        return headers

    def _build_body(self, config: Dict[str, Any]) -> Optional[Union[str, bytes, Dict]]:
        """Build request body"""
        if "body" not in config:
            return None
        
        body = config["body"]
        body_format = config.get("body_format", "json")
        
        if body_format == "json":
            return json.dumps(body)
        elif body_format == "xml":
            return self._dict_to_xml(body)
        elif body_format == "form":
            return urlencode(body)
        elif body_format == "yaml":
            return yaml.dump(body)
        elif body_format == "raw":
            return body
        else:
            return json.dumps(body)

    def _add_authentication(self, request: Dict[str, Any], auth_config: Union[Dict, AuthConfig]):
        """Add authentication to request"""
        if isinstance(auth_config, dict):
            auth_config = AuthConfig(**auth_config)
        
        auth_type = auth_config.type.lower()
        
        if auth_type == "basic":
            username = auth_config.credentials.get("username", "")
            password = auth_config.credentials.get("password", "")
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            request["headers"]["Authorization"] = f"Basic {credentials}"
        
        elif auth_type == "bearer":
            token = auth_config.credentials.get("token", "")
            request["headers"]["Authorization"] = f"Bearer {token}"
        
        elif auth_type == "api_key":
            key_name = auth_config.credentials.get("key_name", "X-API-Key")
            key_value = auth_config.credentials.get("key_value", "")
            
            if auth_config.placement == "header":
                request["headers"][key_name] = key_value
            elif auth_config.placement == "query":
                parsed_url = urlparse(request["url"])
                query_params = parse_qs(parsed_url.query)
                query_params[key_name] = [key_value]
                new_query = urlencode(query_params, doseq=True)
                request["url"] = urlunparse(parsed_url._replace(query=new_query))
        
        elif auth_type == "oauth2":
            self._add_oauth2_auth(request, auth_config.credentials)
        
        elif auth_type == "jwt":
            self._add_jwt_auth(request, auth_config.credentials)
        
        elif auth_type == "custom":
            custom_handler = auth_config.credentials.get("handler")
            if custom_handler and callable(custom_handler):
                custom_handler(request, auth_config.credentials)

    def _add_oauth2_auth(self, request: Dict[str, Any], credentials: Dict[str, Any]):
        """Add OAuth2 authentication"""
        flow_type = credentials.get("flow", "client_credentials")
        
        if flow_type == "client_credentials":
            # This would typically involve getting a token first
            access_token = credentials.get("access_token", "")
            request["headers"]["Authorization"] = f"Bearer {access_token}"
        
        elif flow_type == "authorization_code":
            # Handle authorization code flow
            access_token = credentials.get("access_token", "")
            request["headers"]["Authorization"] = f"Bearer {access_token}"

    def _add_jwt_auth(self, request: Dict[str, Any], credentials: Dict[str, Any]):
        """Add JWT authentication"""
        payload = credentials.get("payload", {})
        secret = credentials.get("secret", "")
        algorithm = credentials.get("algorithm", "HS256")
        
        # Add standard claims
        if "exp" not in payload:
            payload["exp"] = int(time.time()) + 3600  # 1 hour expiry
        if "iat" not in payload:
            payload["iat"] = int(time.time())
        
        token = jwt.encode(payload, secret, algorithm=algorithm)
        request["headers"]["Authorization"] = f"Bearer {token}"

    def _apply_transformations(self, request: Dict[str, Any], transformations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply transformations to the request"""
        for transformation in transformations:
            transform_type = transformation.get("type")
            
            if transform_type in self.transformers:
                request = self.transformers[transform_type](request, transformation.get("config", {}))
            else:
                raise RequestBuildError(f"Unknown transformation type: {transform_type}")
        
        return request

    def _sign_request(self, request: Dict[str, Any], signing_config: Dict[str, Any]):
        """Sign the request for integrity verification"""
        algorithm = signing_config.get("algorithm", "HMAC-SHA256")
        secret = signing_config.get("secret", "")
        include_body = signing_config.get("include_body", True)
        
        # Build signature base string
        signature_parts = [
            request["method"],
            request["url"],
            str(int(time.time()))
        ]
        
        if include_body and "data" in request:
            signature_parts.append(request["data"])
        
        signature_base = "\n".join(str(part) for part in signature_parts)
        
        # Generate signature
        if algorithm == "HMAC-SHA256":
            signature = hmac.new(
                secret.encode(),
                signature_base.encode(),
                hashlib.sha256
            ).hexdigest()
        elif algorithm == "HMAC-SHA512":
            signature = hmac.new(
                secret.encode(),
                signature_base.encode(),
                hashlib.sha512
            ).hexdigest()
        else:
            raise RequestBuildError(f"Unsupported signing algorithm: {algorithm}")
        
        # Add signature to headers
        request["headers"]["X-Signature"] = signature
        request["headers"]["X-Timestamp"] = str(int(time.time()))

    def _dict_to_xml(self, data: Dict[str, Any], root_name: str = "root") -> str:
        """Convert dictionary to XML"""
        root = ET.Element(root_name)
        
        def build_xml(parent, data):
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, list):
                        for item in value:
                            elem = ET.SubElement(parent, key)
                            build_xml(elem, item)
                    else:
                        elem = ET.SubElement(parent, key)
                        build_xml(elem, value)
            else:
                parent.text = str(data)
        
        build_xml(root, data)
        return ET.tostring(root, encoding="unicode")

    def _setup_default_transformers(self):
        """Setup default transformers"""
        
        def encrypt_body(request: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
            """Encrypt request body"""
            if "data" in request:
                # Simple base64 encoding as example
                encrypted = base64.b64encode(request["data"].encode()).decode()
                request["data"] = encrypted
                request["headers"]["X-Encrypted"] = "true"
            return request
        
        def add_timestamp(request: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
            """Add timestamp to request"""
            format_str = config.get("format", "%Y-%m-%dT%H:%M:%SZ")
            request["headers"]["X-Timestamp"] = datetime.utcnow().strftime(format_str)
            return request
        
        def add_request_id(request: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
            """Add unique request ID"""
            import uuid
            request["headers"]["X-Request-ID"] = str(uuid.uuid4())
            return request
        
        self.transformers["encrypt_body"] = encrypt_body
        self.transformers["add_timestamp"] = add_timestamp
        self.transformers["add_request_id"] = add_request_id

    def _setup_default_validators(self):
        """Setup default validators"""
        
        def validate_json_schema(config: Dict[str, Any]):
            """Validate request body against JSON schema"""
            if "body" in config and "json_schema" in config:
                import jsonschema
                try:
                    jsonschema.validate(config["body"], config["json_schema"])
                except jsonschema.ValidationError as e:
                    raise RequestBuildError(f"JSON schema validation failed: {e}")
        
        def validate_required_headers(config: Dict[str, Any]):
            """Validate required headers are present"""
            required_headers = config.get("required_headers", [])
            headers = config.get("headers", {})
            
            for header in required_headers:
                if header not in headers:
                    raise RequestBuildError(f"Required header missing: {header}")
        
        self.validators["json_schema"] = validate_json_schema
        self.validators["required_headers"] = validate_required_headers

    def build_batch(self, configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build multiple requests in batch"""
        return [self.build(config) for config in configs]

    def build_from_file(self, file_path: str) -> Dict[str, Any]:
        """Build request from configuration file"""
        with open(file_path, 'r') as f:
            if file_path.endswith('.json'):
                config = json.load(f)
            elif file_path.endswith('.yaml') or file_path.endswith('.yml'):
                config = yaml.safe_load(f)
            else:
                raise RequestBuildError("Unsupported file format")
        
        return self.build(config)