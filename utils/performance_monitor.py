#!/usr/bin/env python3
"""
Performance Monitoring System
Monitors system performance, resource usage, and optimization opportunities
"""

import os
import sys
import time
import psutil
import asyncio
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import functools

from .logging_config import get_logger

logger = get_logger('performance_monitor', separate_file=True)

@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    timestamp: datetime
    metric_name: str
    value: float
    unit: str
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SystemSnapshot:
    """System resource snapshot"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    process_count: int
    load_average: Optional[List[float]] = None

class PerformanceTracker:
    """Tracks performance metrics over time"""
    
    def __init__(self, max_metrics: int = 10000):
        self.max_metrics = max_metrics
        self.metrics: deque = deque(maxlen=max_metrics)
        self.system_snapshots: deque = deque(maxlen=1000)
        self.function_timings: Dict[str, deque] = {}
        self.lock = threading.Lock()
    
    def add_metric(self, metric: PerformanceMetric):
        """Add a performance metric"""
        with self.lock:
            self.metrics.append(metric)
    
    def add_system_snapshot(self, snapshot: SystemSnapshot):
        """Add a system resource snapshot"""
        with self.lock:
            self.system_snapshots.append(snapshot)
    
    def add_function_timing(self, function_name: str, duration: float, context: Dict[str, Any] = None):
        """Add function execution timing"""
        with self.lock:
            if function_name not in self.function_timings:
                self.function_timings[function_name] = deque(maxlen=1000)
            
            metric = PerformanceMetric(
                timestamp=datetime.now(),
                metric_name=f"function_timing_{function_name}",
                value=duration,
                unit="seconds",
                context=context or {}
            )
            
            self.function_timings[function_name].append(metric)
            self.metrics.append(metric)
    
    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get summary of metrics for the specified time period"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self.lock:
            recent_metrics = [m for m in self.metrics if m.timestamp > cutoff_time]
            recent_snapshots = [s for s in self.system_snapshots if s.timestamp > cutoff_time]
        
        if not recent_metrics and not recent_snapshots:
            return {"message": "No metrics available for the specified period"}
        
        # System resource summary
        system_summary = {}
        if recent_snapshots:
            cpu_values = [s.cpu_percent for s in recent_snapshots]
            memory_values = [s.memory_percent for s in recent_snapshots]
            
            system_summary = {
                "cpu": {
                    "avg": sum(cpu_values) / len(cpu_values),
                    "max": max(cpu_values),
                    "min": min(cpu_values)
                },
                "memory": {
                    "avg": sum(memory_values) / len(memory_values),
                    "max": max(memory_values),
                    "min": min(memory_values)
                },
                "snapshots_count": len(recent_snapshots)
            }
        
        # Function timing summary
        function_summary = {}
        for func_name, timings in self.function_timings.items():
            recent_timings = [t for t in timings if t.timestamp > cutoff_time]
            if recent_timings:
                durations = [t.value for t in recent_timings]
                function_summary[func_name] = {
                    "calls": len(recent_timings),
                    "avg_duration": sum(durations) / len(durations),
                    "max_duration": max(durations),
                    "min_duration": min(durations),
                    "total_duration": sum(durations)
                }
        
        return {
            "period_hours": hours,
            "total_metrics": len(recent_metrics),
            "system_resources": system_summary,
            "function_timings": function_summary,
            "timestamp": datetime.now().isoformat()
        }

class PerformanceMonitor:
    """Main performance monitoring system"""
    
    def __init__(self, monitoring_interval: int = 30):
        self.monitoring_interval = monitoring_interval
        self.tracker = PerformanceTracker()
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.alert_callbacks: List[Callable] = []
        
        # Performance thresholds
        self.thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_usage_percent": 90.0,
            "function_duration": 30.0  # seconds
        }
    
    def add_alert_callback(self, callback: Callable):
        """Add callback for performance alerts"""
        self.alert_callbacks.append(callback)
    
    def set_threshold(self, metric: str, value: float):
        """Set performance threshold"""
        self.thresholds[metric] = value
        logger.info(f"Set {metric} threshold to {value}")
    
    def start_monitoring(self):
        """Start continuous performance monitoring"""
        if self.monitoring_active:
            logger.warning("Performance monitoring already active")
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"Started performance monitoring (interval: {self.monitoring_interval}s)")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Stopped performance monitoring")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                snapshot = self._take_system_snapshot()
                self.tracker.add_system_snapshot(snapshot)
                
                # Check for threshold violations
                self._check_thresholds(snapshot)
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitoring_interval)
    
    def _take_system_snapshot(self) -> SystemSnapshot:
        """Take a snapshot of current system resources"""
        try:
            # CPU and memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Network
            network = psutil.net_io_counters()
            
            # Process count
            process_count = len(psutil.pids())
            
            # Load average (Unix-like systems only)
            load_avg = None
            if hasattr(os, 'getloadavg'):
                try:
                    load_avg = list(os.getloadavg())
                except OSError:
                    pass
            
            return SystemSnapshot(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                memory_available_mb=memory.available / (1024 * 1024),
                disk_usage_percent=disk.percent,
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv,
                process_count=process_count,
                load_average=load_avg
            )
            
        except Exception as e:
            logger.error(f"Error taking system snapshot: {e}")
            # Return minimal snapshot
            return SystemSnapshot(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0,
                disk_usage_percent=0.0,
                network_bytes_sent=0,
                network_bytes_recv=0,
                process_count=0
            )
    
    def _check_thresholds(self, snapshot: SystemSnapshot):
        """Check if any thresholds are violated"""
        alerts = []
        
        if snapshot.cpu_percent > self.thresholds["cpu_percent"]:
            alerts.append(f"High CPU usage: {snapshot.cpu_percent:.1f}%")
        
        if snapshot.memory_percent > self.thresholds["memory_percent"]:
            alerts.append(f"High memory usage: {snapshot.memory_percent:.1f}%")
        
        if snapshot.disk_usage_percent > self.thresholds["disk_usage_percent"]:
            alerts.append(f"High disk usage: {snapshot.disk_usage_percent:.1f}%")
        
        # Send alerts
        for alert in alerts:
            logger.warning(f"Performance alert: {alert}")
            self._send_alert(alert, snapshot)
    
    def _send_alert(self, message: str, snapshot: SystemSnapshot):
        """Send performance alert"""
        for callback in self.alert_callbacks:
            try:
                callback(message, snapshot)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current system performance status"""
        try:
            snapshot = self._take_system_snapshot()
            
            # Get recent performance summary
            summary = self.tracker.get_metrics_summary(hours=1)
            
            return {
                "current_snapshot": {
                    "timestamp": snapshot.timestamp.isoformat(),
                    "cpu_percent": snapshot.cpu_percent,
                    "memory_percent": snapshot.memory_percent,
                    "memory_used_mb": snapshot.memory_used_mb,
                    "memory_available_mb": snapshot.memory_available_mb,
                    "disk_usage_percent": snapshot.disk_usage_percent,
                    "process_count": snapshot.process_count,
                    "load_average": snapshot.load_average
                },
                "monitoring_active": self.monitoring_active,
                "thresholds": self.thresholds,
                "recent_summary": summary
            }
            
        except Exception as e:
            logger.error(f"Error getting current status: {e}")
            return {"error": str(e)}
    
    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        summary = self.tracker.get_metrics_summary(hours=hours)
        current_status = self.get_current_status()
        
        # Calculate performance score (0-100)
        score = 100
        if "current_snapshot" in current_status:
            snapshot = current_status["current_snapshot"]
            score -= min(snapshot["cpu_percent"] / 2, 40)  # Max 40 points deduction
            score -= min(snapshot["memory_percent"] / 2, 30)  # Max 30 points deduction
            score -= min(snapshot["disk_usage_percent"] / 10, 20)  # Max 20 points deduction
            score = max(0, score)
        
        return {
            "report_period_hours": hours,
            "performance_score": round(score, 1),
            "current_status": current_status,
            "summary": summary,
            "recommendations": self._generate_recommendations(current_status, summary),
            "generated_at": datetime.now().isoformat()
        }
    
    def _generate_recommendations(self, current_status: Dict[str, Any], summary: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []
        
        if "current_snapshot" in current_status:
            snapshot = current_status["current_snapshot"]
            
            if snapshot["cpu_percent"] > 70:
                recommendations.append("Consider reducing concurrent operations or optimizing CPU-intensive tasks")
            
            if snapshot["memory_percent"] > 80:
                recommendations.append("Monitor memory usage and consider implementing memory cleanup routines")
            
            if snapshot["disk_usage_percent"] > 85:
                recommendations.append("Clean up old log files and temporary data")
        
        # Function timing recommendations
        if "function_timings" in summary:
            slow_functions = [
                func for func, stats in summary["function_timings"].items()
                if stats["avg_duration"] > self.thresholds["function_duration"]
            ]
            if slow_functions:
                recommendations.append(f"Optimize slow functions: {', '.join(slow_functions)}")
        
        if not recommendations:
            recommendations.append("System performance is within acceptable ranges")
        
        return recommendations

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

# Decorator for timing function execution
def time_function(category: str = "general"):
    """Decorator to time function execution"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                performance_monitor.tracker.add_function_timing(
                    f"{category}.{func.__name__}",
                    duration,
                    {"success": True}
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                performance_monitor.tracker.add_function_timing(
                    f"{category}.{func.__name__}",
                    duration,
                    {"success": False, "error": str(e)}
                )
                raise
        return wrapper
    return decorator

def time_async_function(category: str = "general"):
    """Decorator to time async function execution"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                performance_monitor.tracker.add_function_timing(
                    f"{category}.{func.__name__}",
                    duration,
                    {"success": True}
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                performance_monitor.tracker.add_function_timing(
                    f"{category}.{func.__name__}",
                    duration,
                    {"success": False, "error": str(e)}
                )
                raise
        return wrapper
    return decorator

if __name__ == "__main__":
    # Test performance monitoring
    logger.info("🧪 Testing Performance Monitoring System")
    
    # Start monitoring
    performance_monitor.start_monitoring()
    
    # Test function timing
    @time_function("test")
    def test_function():
        time.sleep(0.1)
        return "test result"
    
    # Run test function
    result = test_function()
    print(f"Test function result: {result}")
    
    # Wait for a monitoring cycle
    time.sleep(2)
    
    # Get current status
    status = performance_monitor.get_current_status()
    print(f"Current CPU: {status['current_snapshot']['cpu_percent']:.1f}%")
    print(f"Current Memory: {status['current_snapshot']['memory_percent']:.1f}%")
    
    # Generate report
    report = performance_monitor.get_performance_report(hours=1)
    print(f"Performance Score: {report['performance_score']}")
    print(f"Recommendations: {report['recommendations']}")
    
    # Stop monitoring
    performance_monitor.stop_monitoring()
    
    print("✅ Performance monitoring test completed")