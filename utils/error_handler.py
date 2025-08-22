#!/usr/bin/env python3
"""
Centralized Error Handling and Monitoring
Provides consistent error handling, monitoring, and recovery mechanisms
"""

import os
import sys
import traceback
import asyncio
import functools
import time
from typing import Dict, Any, Optional, Callable, List, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

# Import our logging configuration
from .logging_config import get_logger

logger = get_logger('error_handler', separate_file=True)

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories"""
    BROWSER = "browser"
    NETWORK = "network"
    CAPTCHA = "captcha"
    VNC = "vnc"
    SCREENSHOT = "screenshot"
    DROPBOX = "dropbox"
    AUTHENTICATION = "authentication"
    SYSTEM = "system"
    UNKNOWN = "unknown"

@dataclass
class ErrorInfo:
    """Information about an error occurrence"""
    timestamp: datetime
    error_type: str
    error_message: str
    traceback_str: str
    severity: ErrorSeverity
    category: ErrorCategory
    context: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    resolution_method: Optional[str] = None

class ErrorTracker:
    """Tracks and analyzes error patterns"""
    
    def __init__(self, max_errors: int = 1000):
        self.max_errors = max_errors
        self.errors: List[ErrorInfo] = []
        self.error_counts: Dict[str, int] = {}
        self.last_cleanup = datetime.now()
    
    def add_error(self, error_info: ErrorInfo):
        """Add an error to the tracker"""
        self.errors.append(error_info)
        
        # Update error counts
        error_key = f"{error_info.category.value}:{error_info.error_type}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Cleanup old errors if needed
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors:]
        
        # Periodic cleanup
        if datetime.now() - self.last_cleanup > timedelta(hours=1):
            self._cleanup_old_errors()
    
    def _cleanup_old_errors(self):
        """Remove errors older than 24 hours"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.errors = [e for e in self.errors if e.timestamp > cutoff_time]
        self.last_cleanup = datetime.now()
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        if not self.errors:
            return {"total_errors": 0}
        
        recent_errors = [e for e in self.errors if e.timestamp > datetime.now() - timedelta(hours=1)]
        
        severity_counts = {}
        category_counts = {}
        
        for error in self.errors:
            severity_counts[error.severity.value] = severity_counts.get(error.severity.value, 0) + 1
            category_counts[error.category.value] = category_counts.get(error.category.value, 0) + 1
        
        return {
            "total_errors": len(self.errors),
            "recent_errors_1h": len(recent_errors),
            "severity_breakdown": severity_counts,
            "category_breakdown": category_counts,
            "most_common_errors": sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "resolved_errors": len([e for e in self.errors if e.resolved])
        }
    
    def get_recent_errors(self, hours: int = 1) -> List[ErrorInfo]:
        """Get recent errors within specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [e for e in self.errors if e.timestamp > cutoff_time]

class ErrorHandler:
    """Centralized error handling system"""
    
    def __init__(self):
        self.tracker = ErrorTracker()
        self.recovery_strategies: Dict[str, Callable] = {}
        self.notification_callbacks: List[Callable] = []
    
    def register_recovery_strategy(self, error_pattern: str, strategy: Callable):
        """Register a recovery strategy for specific error patterns"""
        self.recovery_strategies[error_pattern] = strategy
        logger.info(f"Registered recovery strategy for: {error_pattern}")
    
    def add_notification_callback(self, callback: Callable):
        """Add a callback for error notifications"""
        self.notification_callbacks.append(callback)
    
    def handle_error(self, 
                    error: Exception,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    category: ErrorCategory = ErrorCategory.UNKNOWN,
                    context: Optional[Dict[str, Any]] = None,
                    attempt_recovery: bool = True) -> ErrorInfo:
        """Handle an error with tracking and potential recovery"""
        
        error_info = ErrorInfo(
            timestamp=datetime.now(),
            error_type=type(error).__name__,
            error_message=str(error),
            traceback_str=traceback.format_exc(),
            severity=severity,
            category=category,
            context=context or {}
        )
        
        # Log the error
        log_method = {
            ErrorSeverity.LOW: logger.info,
            ErrorSeverity.MEDIUM: logger.warning,
            ErrorSeverity.HIGH: logger.error,
            ErrorSeverity.CRITICAL: logger.critical
        }.get(severity, logger.error)
        
        log_method(f"[{category.value.upper()}] {error_info.error_type}: {error_info.error_message}")
        
        # Add to tracker
        self.tracker.add_error(error_info)
        
        # Attempt recovery if enabled
        if attempt_recovery:
            recovery_result = self._attempt_recovery(error_info)
            if recovery_result:
                error_info.resolved = True
                error_info.resolution_time = datetime.now()
                error_info.resolution_method = recovery_result
                logger.info(f"Error recovered using: {recovery_result}")
        
        # Send notifications for high/critical errors
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self._send_notifications(error_info)
        
        return error_info
    
    def _attempt_recovery(self, error_info: ErrorInfo) -> Optional[str]:
        """Attempt to recover from an error"""
        error_pattern = f"{error_info.category.value}:{error_info.error_type}"
        
        # Try specific recovery strategy
        if error_pattern in self.recovery_strategies:
            try:
                strategy = self.recovery_strategies[error_pattern]
                strategy(error_info)
                return f"specific_strategy:{error_pattern}"
            except Exception as e:
                logger.error(f"Recovery strategy failed: {e}")
        
        # Try generic recovery strategies
        return self._generic_recovery(error_info)
    
    def _generic_recovery(self, error_info: ErrorInfo) -> Optional[str]:
        """Generic recovery strategies"""
        try:
            # Browser-related errors
            if error_info.category == ErrorCategory.BROWSER:
                if "timeout" in error_info.error_message.lower():
                    # Wait and retry for timeout errors
                    time.sleep(2)
                    return "timeout_retry"
                elif "connection" in error_info.error_message.lower():
                    # Wait longer for connection errors
                    time.sleep(5)
                    return "connection_retry"
            
            # Network-related errors
            elif error_info.category == ErrorCategory.NETWORK:
                if "timeout" in error_info.error_message.lower():
                    time.sleep(3)
                    return "network_timeout_retry"
            
            # VNC-related errors
            elif error_info.category == ErrorCategory.VNC:
                if "port" in error_info.error_message.lower():
                    # Port conflict - could try different port
                    return "port_conflict_detected"
            
        except Exception as e:
            logger.error(f"Generic recovery failed: {e}")
        
        return None
    
    def _send_notifications(self, error_info: ErrorInfo):
        """Send error notifications"""
        for callback in self.notification_callbacks:
            try:
                callback(error_info)
            except Exception as e:
                logger.error(f"Notification callback failed: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status"""
        stats = self.tracker.get_error_stats()
        recent_errors = self.tracker.get_recent_errors(1)
        
        # Determine health status
        critical_errors = len([e for e in recent_errors if e.severity == ErrorSeverity.CRITICAL])
        high_errors = len([e for e in recent_errors if e.severity == ErrorSeverity.HIGH])
        
        if critical_errors > 0:
            health_status = "critical"
        elif high_errors > 3:
            health_status = "degraded"
        elif len(recent_errors) > 10:
            health_status = "warning"
        else:
            health_status = "healthy"
        
        return {
            "status": health_status,
            "recent_errors": len(recent_errors),
            "critical_errors": critical_errors,
            "high_errors": high_errors,
            "error_stats": stats,
            "timestamp": datetime.now().isoformat()
        }

# Global error handler instance
error_handler = ErrorHandler()

# Decorator for automatic error handling
def handle_errors(severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 category: ErrorCategory = ErrorCategory.UNKNOWN,
                 reraise: bool = False,
                 return_on_error: Any = None):
    """Decorator for automatic error handling"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler.handle_error(
                    e, 
                    severity=severity, 
                    category=category,
                    context={"function": func.__name__, "args": str(args)[:100]}
                )
                if reraise:
                    raise
                return return_on_error
        return wrapper
    return decorator

def handle_async_errors(severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                       category: ErrorCategory = ErrorCategory.UNKNOWN,
                       reraise: bool = False,
                       return_on_error: Any = None):
    """Decorator for automatic async error handling"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_handler.handle_error(
                    e, 
                    severity=severity, 
                    category=category,
                    context={"function": func.__name__, "args": str(args)[:100]}
                )
                if reraise:
                    raise
                return return_on_error
        return wrapper
    return decorator

# Recovery strategies registration
def register_browser_recovery():
    """Register browser-specific recovery strategies"""
    
    def browser_timeout_recovery(error_info: ErrorInfo):
        """Recovery for browser timeout errors"""
        logger.info("Attempting browser timeout recovery...")
        time.sleep(3)
    
    def browser_crash_recovery(error_info: ErrorInfo):
        """Recovery for browser crash errors"""
        logger.info("Attempting browser crash recovery...")
        # Could restart browser here
    
    error_handler.register_recovery_strategy("browser:TimeoutError", browser_timeout_recovery)
    error_handler.register_recovery_strategy("browser:BrowserError", browser_crash_recovery)

def register_vnc_recovery():
    """Register VNC-specific recovery strategies"""
    
    def vnc_port_conflict_recovery(error_info: ErrorInfo):
        """Recovery for VNC port conflicts"""
        logger.info("Attempting VNC port conflict recovery...")
        # Could try different ports here
    
    error_handler.register_recovery_strategy("vnc:PortError", vnc_port_conflict_recovery)

# Initialize recovery strategies
register_browser_recovery()
register_vnc_recovery()

if __name__ == "__main__":
    # Test error handling system
    logger.info("🧪 Testing Error Handling System")
    
    # Test error handling
    try:
        raise ValueError("Test error for demonstration")
    except Exception as e:
        error_info = error_handler.handle_error(
            e, 
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.SYSTEM,
            context={"test": True}
        )
        print(f"Error handled: {error_info.error_type}")
    
    # Test decorator
    @handle_errors(severity=ErrorSeverity.LOW, category=ErrorCategory.SYSTEM)
    def test_function():
        raise RuntimeError("Test decorator error")
    
    result = test_function()
    print(f"Decorator test result: {result}")
    
    # Get health status
    health = error_handler.get_health_status()
    print(f"System health: {health['status']}")
    
    print("✅ Error handling test completed")