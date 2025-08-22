#!/usr/bin/env python3
"""
System Health Checker
Comprehensive health monitoring for all system components
"""

import os
import sys
import asyncio
import time
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import psutil

from .logging_config import get_logger
from .error_handler import error_handler, ErrorSeverity, ErrorCategory
from .performance_monitor import performance_monitor

logger = get_logger('health_checker', separate_file=True)

class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

@dataclass
class HealthCheck:
    """Individual health check result"""
    component: str
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    check_duration: float

class SystemHealthChecker:
    """Comprehensive system health checker"""
    
    def __init__(self):
        self.health_checks: Dict[str, HealthCheck] = {}
        self.last_full_check: Optional[datetime] = None
        self.check_history: List[Dict[str, Any]] = []
        self.max_history = 100
    
    async def run_full_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check on all components"""
        logger.info("🏥 Starting full system health check...")
        start_time = time.time()
        
        # Run all health checks
        checks = await asyncio.gather(
            self._check_system_resources(),
            self._check_browser_automation(),
            self._check_vnc_system(),
            self._check_dropbox_integration(),
            self._check_screenshot_system(),
            self._check_file_system(),
            self._check_network_connectivity(),
            self._check_dependencies(),
            return_exceptions=True
        )
        
        # Process results
        check_results = {}
        for i, check in enumerate(checks):
            if isinstance(check, Exception):
                component_name = [
                    "system_resources", "browser_automation", "vnc_system",
                    "dropbox_integration", "screenshot_system", "file_system",
                    "network_connectivity", "dependencies"
                ][i]
                check_results[component_name] = HealthCheck(
                    component=component_name,
                    status=HealthStatus.CRITICAL,
                    message=f"Health check failed: {str(check)}",
                    details={"error": str(check)},
                    timestamp=datetime.now(),
                    check_duration=0.0
                )
            else:
                check_results[check.component] = check
        
        # Update health checks
        self.health_checks.update(check_results)
        self.last_full_check = datetime.now()
        
        # Calculate overall health
        overall_health = self._calculate_overall_health(check_results)
        
        # Create summary
        total_duration = time.time() - start_time
        summary = {
            "overall_status": overall_health.value,
            "check_timestamp": self.last_full_check.isoformat(),
            "total_duration": round(total_duration, 2),
            "components": {
                name: {
                    "status": check.status.value,
                    "message": check.message,
                    "details": check.details,
                    "duration": check.check_duration
                }
                for name, check in check_results.items()
            }
        }
        
        # Add to history
        self.check_history.append(summary)
        if len(self.check_history) > self.max_history:
            self.check_history = self.check_history[-self.max_history:]
        
        logger.info(f"✅ Health check completed in {total_duration:.2f}s - Overall: {overall_health.value}")
        return summary
    
    async def _check_system_resources(self) -> HealthCheck:
        """Check system resource usage"""
        start_time = time.time()
        
        try:
            # Get current system status
            status = performance_monitor.get_current_status()
            
            if "current_snapshot" not in status:
                return HealthCheck(
                    component="system_resources",
                    status=HealthStatus.WARNING,
                    message="Unable to get system resource information",
                    details={},
                    timestamp=datetime.now(),
                    check_duration=time.time() - start_time
                )
            
            snapshot = status["current_snapshot"]
            
            # Determine health status
            cpu_percent = snapshot["cpu_percent"]
            memory_percent = snapshot["memory_percent"]
            disk_percent = snapshot["disk_usage_percent"]
            
            issues = []
            if cpu_percent > 90:
                issues.append(f"Critical CPU usage: {cpu_percent:.1f}%")
            elif cpu_percent > 80:
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            
            if memory_percent > 95:
                issues.append(f"Critical memory usage: {memory_percent:.1f}%")
            elif memory_percent > 85:
                issues.append(f"High memory usage: {memory_percent:.1f}%")
            
            if disk_percent > 95:
                issues.append(f"Critical disk usage: {disk_percent:.1f}%")
            elif disk_percent > 90:
                issues.append(f"High disk usage: {disk_percent:.1f}%")
            
            # Determine status
            if any("Critical" in issue for issue in issues):
                health_status = HealthStatus.CRITICAL
            elif any("High" in issue for issue in issues):
                health_status = HealthStatus.WARNING
            else:
                health_status = HealthStatus.HEALTHY
            
            message = "System resources are healthy" if not issues else "; ".join(issues)
            
            return HealthCheck(
                component="system_resources",
                status=health_status,
                message=message,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "disk_percent": disk_percent,
                    "memory_used_mb": snapshot["memory_used_mb"],
                    "memory_available_mb": snapshot["memory_available_mb"],
                    "process_count": snapshot["process_count"]
                },
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
            
        except Exception as e:
            return HealthCheck(
                component="system_resources",
                status=HealthStatus.CRITICAL,
                message=f"Failed to check system resources: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
    
    async def _check_browser_automation(self) -> HealthCheck:
        """Check browser automation system"""
        start_time = time.time()
        
        try:
            # Check if playwright is available
            try:
                from playwright.async_api import async_playwright
                playwright_available = True
            except ImportError:
                playwright_available = False
            
            # Check browser factory
            try:
                from .browser_factory import browser_factory
                browser_factory_available = True
            except ImportError:
                browser_factory_available = False
            
            issues = []
            if not playwright_available:
                issues.append("Playwright not available")
            if not browser_factory_available:
                issues.append("Browser factory not available")
            
            # Try to get VNC sessions if available
            vnc_sessions = 0
            try:
                from .vnc_browser_manager import vnc_browser_manager
                vnc_sessions = len(vnc_browser_manager.browser_sessions)
            except Exception:
                pass
            
            # Determine status
            if issues:
                health_status = HealthStatus.CRITICAL
                message = "; ".join(issues)
            else:
                health_status = HealthStatus.HEALTHY
                message = "Browser automation system is healthy"
            
            return HealthCheck(
                component="browser_automation",
                status=health_status,
                message=message,
                details={
                    "playwright_available": playwright_available,
                    "browser_factory_available": browser_factory_available,
                    "active_vnc_sessions": vnc_sessions
                },
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
            
        except Exception as e:
            return HealthCheck(
                component="browser_automation",
                status=HealthStatus.CRITICAL,
                message=f"Failed to check browser automation: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
    
    async def _check_vnc_system(self) -> HealthCheck:
        """Check VNC system health"""
        start_time = time.time()
        
        try:
            # Check VNC dependencies
            vnc_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if any(vnc_name in proc.info['name'].lower() for vnc_name in ['xvfb', 'x11vnc', 'websockify', 'fluxbox']):
                        vnc_processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': ' '.join(proc.info['cmdline'][:3]) if proc.info['cmdline'] else ''
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Check VNC manager
            try:
                from .vnc_manager import vnc_manager
                vnc_sessions = len(vnc_manager.sessions)
                vnc_health = vnc_manager.health_check()
                healthy_sessions = sum(1 for h in vnc_health.values() if h)
            except Exception as e:
                vnc_sessions = 0
                healthy_sessions = 0
                vnc_health = {}
            
            # Check noVNC directory
            novnc_path = "/workspace/project/Exo-Mass/noVNC"
            novnc_available = os.path.exists(novnc_path)
            
            # Determine status
            issues = []
            if not novnc_available:
                issues.append("noVNC directory not found")
            
            if vnc_sessions > 0 and healthy_sessions < vnc_sessions:
                issues.append(f"Unhealthy VNC sessions: {vnc_sessions - healthy_sessions}/{vnc_sessions}")
            
            if issues:
                health_status = HealthStatus.WARNING if novnc_available else HealthStatus.CRITICAL
                message = "; ".join(issues)
            else:
                health_status = HealthStatus.HEALTHY
                message = "VNC system is healthy"
            
            return HealthCheck(
                component="vnc_system",
                status=health_status,
                message=message,
                details={
                    "novnc_available": novnc_available,
                    "vnc_processes": len(vnc_processes),
                    "vnc_sessions": vnc_sessions,
                    "healthy_sessions": healthy_sessions,
                    "process_details": vnc_processes[:5]  # Limit to first 5
                },
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
            
        except Exception as e:
            return HealthCheck(
                component="vnc_system",
                status=HealthStatus.CRITICAL,
                message=f"Failed to check VNC system: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
    
    async def _check_dropbox_integration(self) -> HealthCheck:
        """Check Dropbox integration"""
        start_time = time.time()
        
        try:
            # Check if dropbox module is available
            try:
                import dropbox
                dropbox_available = True
            except ImportError:
                dropbox_available = False
            
            # Check dropbox uploader
            try:
                from .dropbox_uploader import DropboxUploader
                uploader_available = True
            except ImportError:
                uploader_available = False
            
            # Check environment variables
            dropbox_token = os.getenv('DROPBOX_ACCESS_TOKEN')
            token_configured = bool(dropbox_token)
            
            issues = []
            if not dropbox_available:
                issues.append("Dropbox library not available")
            if not uploader_available:
                issues.append("Dropbox uploader not available")
            if not token_configured:
                issues.append("Dropbox access token not configured")
            
            # Determine status
            if issues:
                health_status = HealthStatus.WARNING
                message = "; ".join(issues)
            else:
                health_status = HealthStatus.HEALTHY
                message = "Dropbox integration is healthy"
            
            return HealthCheck(
                component="dropbox_integration",
                status=health_status,
                message=message,
                details={
                    "dropbox_library_available": dropbox_available,
                    "uploader_available": uploader_available,
                    "token_configured": token_configured
                },
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
            
        except Exception as e:
            return HealthCheck(
                component="dropbox_integration",
                status=HealthStatus.CRITICAL,
                message=f"Failed to check Dropbox integration: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
    
    async def _check_screenshot_system(self) -> HealthCheck:
        """Check screenshot system"""
        start_time = time.time()
        
        try:
            # Check screenshot monitor
            try:
                from .screenshot_monitor import ScreenshotMonitor
                monitor_available = True
            except ImportError:
                monitor_available = False
            
            issues = []
            if not monitor_available:
                issues.append("Screenshot monitor not available")
            
            # Determine status
            if issues:
                health_status = HealthStatus.WARNING
                message = "; ".join(issues)
            else:
                health_status = HealthStatus.HEALTHY
                message = "Screenshot system is healthy"
            
            return HealthCheck(
                component="screenshot_system",
                status=health_status,
                message=message,
                details={
                    "monitor_available": monitor_available
                },
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
            
        except Exception as e:
            return HealthCheck(
                component="screenshot_system",
                status=HealthStatus.CRITICAL,
                message=f"Failed to check screenshot system: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
    
    async def _check_file_system(self) -> HealthCheck:
        """Check file system health"""
        start_time = time.time()
        
        try:
            # Check important directories
            important_dirs = [
                "/workspace/project/Exo-Mass/logs",
                "/workspace/project/Exo-Mass/temp",
                "/workspace/project/Exo-Mass/utils",
                "/workspace/project/Exo-Mass/noVNC"
            ]
            
            missing_dirs = []
            for dir_path in important_dirs:
                if not os.path.exists(dir_path):
                    missing_dirs.append(dir_path)
            
            # Check disk space
            disk_usage = psutil.disk_usage('/')
            free_space_gb = disk_usage.free / (1024**3)
            
            issues = []
            if missing_dirs:
                issues.append(f"Missing directories: {', '.join(missing_dirs)}")
            
            if free_space_gb < 1.0:
                issues.append(f"Low disk space: {free_space_gb:.1f}GB free")
            
            # Determine status
            if missing_dirs:
                health_status = HealthStatus.WARNING
            elif free_space_gb < 0.5:
                health_status = HealthStatus.CRITICAL
            elif free_space_gb < 1.0:
                health_status = HealthStatus.WARNING
            else:
                health_status = HealthStatus.HEALTHY
            
            message = "File system is healthy" if not issues else "; ".join(issues)
            
            return HealthCheck(
                component="file_system",
                status=health_status,
                message=message,
                details={
                    "missing_directories": missing_dirs,
                    "free_space_gb": round(free_space_gb, 2),
                    "total_space_gb": round(disk_usage.total / (1024**3), 2),
                    "used_space_gb": round(disk_usage.used / (1024**3), 2)
                },
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
            
        except Exception as e:
            return HealthCheck(
                component="file_system",
                status=HealthStatus.CRITICAL,
                message=f"Failed to check file system: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
    
    async def _check_network_connectivity(self) -> HealthCheck:
        """Check network connectivity"""
        start_time = time.time()
        
        try:
            # Test basic connectivity
            import socket
            
            test_hosts = [
                ("8.8.8.8", 53),  # Google DNS
                ("1.1.1.1", 53),  # Cloudflare DNS
            ]
            
            connectivity_results = []
            for host, port in test_hosts:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex((host, port))
                    sock.close()
                    connectivity_results.append({
                        "host": host,
                        "port": port,
                        "connected": result == 0
                    })
                except Exception as e:
                    connectivity_results.append({
                        "host": host,
                        "port": port,
                        "connected": False,
                        "error": str(e)
                    })
            
            # Check if any connections succeeded
            successful_connections = sum(1 for r in connectivity_results if r["connected"])
            
            # Determine status
            if successful_connections == 0:
                health_status = HealthStatus.CRITICAL
                message = "No network connectivity"
            elif successful_connections < len(test_hosts):
                health_status = HealthStatus.WARNING
                message = f"Limited network connectivity ({successful_connections}/{len(test_hosts)})"
            else:
                health_status = HealthStatus.HEALTHY
                message = "Network connectivity is healthy"
            
            return HealthCheck(
                component="network_connectivity",
                status=health_status,
                message=message,
                details={
                    "connectivity_tests": connectivity_results,
                    "successful_connections": successful_connections,
                    "total_tests": len(test_hosts)
                },
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
            
        except Exception as e:
            return HealthCheck(
                component="network_connectivity",
                status=HealthStatus.CRITICAL,
                message=f"Failed to check network connectivity: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
    
    async def _check_dependencies(self) -> HealthCheck:
        """Check critical dependencies"""
        start_time = time.time()
        
        try:
            critical_modules = [
                "playwright",
                "psutil",
                "aiofiles",
                "flask",
                "websockify"
            ]
            
            missing_modules = []
            available_modules = []
            
            for module in critical_modules:
                try:
                    __import__(module)
                    available_modules.append(module)
                except ImportError:
                    missing_modules.append(module)
            
            # Check system commands
            system_commands = ["x11vnc", "Xvfb", "fluxbox"]
            missing_commands = []
            available_commands = []
            
            for cmd in system_commands:
                try:
                    result = subprocess.run(["which", cmd], capture_output=True, text=True)
                    if result.returncode == 0:
                        available_commands.append(cmd)
                    else:
                        missing_commands.append(cmd)
                except Exception:
                    missing_commands.append(cmd)
            
            # Determine status
            issues = []
            if missing_modules:
                issues.append(f"Missing Python modules: {', '.join(missing_modules)}")
            if missing_commands:
                issues.append(f"Missing system commands: {', '.join(missing_commands)}")
            
            if missing_modules:
                health_status = HealthStatus.CRITICAL
            elif missing_commands:
                health_status = HealthStatus.WARNING
            else:
                health_status = HealthStatus.HEALTHY
            
            message = "All dependencies are available" if not issues else "; ".join(issues)
            
            return HealthCheck(
                component="dependencies",
                status=health_status,
                message=message,
                details={
                    "available_modules": available_modules,
                    "missing_modules": missing_modules,
                    "available_commands": available_commands,
                    "missing_commands": missing_commands
                },
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
            
        except Exception as e:
            return HealthCheck(
                component="dependencies",
                status=HealthStatus.CRITICAL,
                message=f"Failed to check dependencies: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
    
    def _calculate_overall_health(self, checks: Dict[str, HealthCheck]) -> HealthStatus:
        """Calculate overall system health from individual checks"""
        if not checks:
            return HealthStatus.UNKNOWN
        
        statuses = [check.status for check in checks.values()]
        
        # Priority: CRITICAL > DEGRADED > WARNING > HEALTHY
        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get current health summary"""
        if not self.health_checks:
            return {
                "status": "unknown",
                "message": "No health checks performed yet",
                "last_check": None
            }
        
        overall_status = self._calculate_overall_health(self.health_checks)
        
        return {
            "status": overall_status.value,
            "last_check": self.last_full_check.isoformat() if self.last_full_check else None,
            "component_count": len(self.health_checks),
            "healthy_components": len([c for c in self.health_checks.values() if c.status == HealthStatus.HEALTHY]),
            "warning_components": len([c for c in self.health_checks.values() if c.status == HealthStatus.WARNING]),
            "critical_components": len([c for c in self.health_checks.values() if c.status == HealthStatus.CRITICAL])
        }

# Global health checker instance
health_checker = SystemHealthChecker()

async def main():
    """Test the health checker"""
    logger.info("🧪 Testing System Health Checker")
    
    # Run full health check
    result = await health_checker.run_full_health_check()
    
    print(f"Overall Status: {result['overall_status']}")
    print(f"Check Duration: {result['total_duration']}s")
    print(f"Components Checked: {len(result['components'])}")
    
    # Print component statuses
    for component, details in result['components'].items():
        status_emoji = {
            'healthy': '✅',
            'warning': '⚠️',
            'degraded': '🔶',
            'critical': '❌',
            'unknown': '❓'
        }.get(details['status'], '❓')
        
        print(f"{status_emoji} {component}: {details['message']}")
    
    print("✅ Health check test completed")

if __name__ == "__main__":
    asyncio.run(main())