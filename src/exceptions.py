"""
Custom exceptions for the network automation system
"""


class NetworkAutomationError(Exception):
    """Base exception for network automation errors"""
    pass


class RequestBuildError(NetworkAutomationError):
    """Raised when request building fails"""
    pass


class RequestSendError(NetworkAutomationError):
    """Raised when request sending fails"""
    pass


class QueueError(NetworkAutomationError):
    """Raised when queue operations fail"""
    pass


class MonitorError(NetworkAutomationError):
    """Raised when monitoring fails"""
    pass


class ConfigurationError(NetworkAutomationError):
    """Raised when configuration is invalid"""
    pass


class AuthenticationError(NetworkAutomationError):
    """Raised when authentication fails"""
    pass


class RateLimitError(NetworkAutomationError):
    """Raised when rate limit is exceeded"""
    pass


class CircuitBreakerError(NetworkAutomationError):
    """Raised when circuit breaker is open"""
    pass