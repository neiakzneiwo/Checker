#!/usr/bin/env python3
"""
VNC Configuration Settings
Centralized configuration for noVNC and browser automation
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class VNCConfig:
    """VNC system configuration"""
    
    # VNC Display Settings
    base_display: int = 10
    base_vnc_port: int = 5900
    base_websocket_port: int = 6080
    max_sessions: int = 10
    
    # Screen Resolution
    screen_width: int = 1920
    screen_height: int = 1080
    screen_depth: int = 24
    
    # noVNC Web Interface
    web_host: str = "0.0.0.0"
    web_port: int = 8080
    
    # Browser Settings
    browser_headless: bool = False  # False for VNC visibility
    browser_args: list = None
    
    # Health Check Settings
    health_check_interval: int = 30  # seconds
    process_timeout: int = 5  # seconds
    
    # Paths
    novnc_path: str = "/workspace/project/Exo-Mass/noVNC"
    
    def __post_init__(self):
        """Initialize default browser args if not provided"""
        if self.browser_args is None:
            self.browser_args = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                f'--window-size={self.screen_width},{self.screen_height}',
                '--start-maximized'
            ]
    
    @classmethod
    def from_env(cls) -> 'VNCConfig':
        """Create configuration from environment variables"""
        return cls(
            base_display=int(os.getenv('VNC_BASE_DISPLAY', '10')),
            base_vnc_port=int(os.getenv('VNC_BASE_PORT', '5900')),
            base_websocket_port=int(os.getenv('VNC_BASE_WEBSOCKET_PORT', '6080')),
            max_sessions=int(os.getenv('VNC_MAX_SESSIONS', '10')),
            screen_width=int(os.getenv('VNC_SCREEN_WIDTH', '1920')),
            screen_height=int(os.getenv('VNC_SCREEN_HEIGHT', '1080')),
            screen_depth=int(os.getenv('VNC_SCREEN_DEPTH', '24')),
            web_host=os.getenv('VNC_WEB_HOST', '0.0.0.0'),
            web_port=int(os.getenv('VNC_WEB_PORT', '8080')),
            browser_headless=os.getenv('VNC_BROWSER_HEADLESS', 'false').lower() == 'true',
            health_check_interval=int(os.getenv('VNC_HEALTH_CHECK_INTERVAL', '30')),
            process_timeout=int(os.getenv('VNC_PROCESS_TIMEOUT', '5')),
            novnc_path=os.getenv('VNC_NOVNC_PATH', '/workspace/project/Exo-Mass/noVNC')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'base_display': self.base_display,
            'base_vnc_port': self.base_vnc_port,
            'base_websocket_port': self.base_websocket_port,
            'max_sessions': self.max_sessions,
            'screen_width': self.screen_width,
            'screen_height': self.screen_height,
            'screen_depth': self.screen_depth,
            'web_host': self.web_host,
            'web_port': self.web_port,
            'browser_headless': self.browser_headless,
            'browser_args': self.browser_args,
            'health_check_interval': self.health_check_interval,
            'process_timeout': self.process_timeout,
            'novnc_path': self.novnc_path
        }

@dataclass
class ScreenshotConfig:
    """Screenshot system configuration"""
    
    # Screenshot Settings
    enabled: bool = True
    interval_seconds: int = 10
    full_page: bool = True
    quality: int = 90
    
    # Dropbox Settings
    upload_enabled: bool = True
    folder_structure: str = "user_id"  # "user_id" or "date" or "session_id"
    
    # Restrictions
    allowed_processes: list = None
    
    def __post_init__(self):
        """Initialize default allowed processes"""
        if self.allowed_processes is None:
            self.allowed_processes = ["account_check"]
    
    @classmethod
    def from_env(cls) -> 'ScreenshotConfig':
        """Create configuration from environment variables"""
        return cls(
            enabled=os.getenv('SCREENSHOT_ENABLED', 'true').lower() == 'true',
            interval_seconds=int(os.getenv('SCREENSHOT_INTERVAL', '10')),
            full_page=os.getenv('SCREENSHOT_FULL_PAGE', 'true').lower() == 'true',
            quality=int(os.getenv('SCREENSHOT_QUALITY', '90')),
            upload_enabled=os.getenv('SCREENSHOT_UPLOAD_ENABLED', 'true').lower() == 'true',
            folder_structure=os.getenv('SCREENSHOT_FOLDER_STRUCTURE', 'user_id')
        )

@dataclass
class SystemConfig:
    """Overall system configuration"""
    
    # Environment
    debug_mode: bool = False
    log_level: str = "INFO"
    
    # Feature Flags
    use_vnc: bool = False
    enhanced_features: bool = True
    
    # Performance
    max_concurrent_sessions: int = 5
    session_timeout: int = 3600  # seconds
    
    # Security
    api_key_required: bool = False
    allowed_origins: list = None
    
    def __post_init__(self):
        """Initialize default allowed origins"""
        if self.allowed_origins is None:
            self.allowed_origins = ["*"]
    
    @classmethod
    def from_env(cls) -> 'SystemConfig':
        """Create configuration from environment variables"""
        return cls(
            debug_mode=os.getenv('DEBUG_MODE', 'false').lower() == 'true',
            log_level=os.getenv('LOG_LEVEL', 'INFO').upper(),
            use_vnc=os.getenv('USE_VNC', 'false').lower() == 'true',
            enhanced_features=os.getenv('ENHANCED_FEATURES', 'true').lower() == 'true',
            max_concurrent_sessions=int(os.getenv('MAX_CONCURRENT_SESSIONS', '5')),
            session_timeout=int(os.getenv('SESSION_TIMEOUT', '3600')),
            api_key_required=os.getenv('API_KEY_REQUIRED', 'false').lower() == 'true'
        )

# Global configuration instances
vnc_config = VNCConfig.from_env()
screenshot_config = ScreenshotConfig.from_env()
system_config = SystemConfig.from_env()

def get_config_summary() -> Dict[str, Any]:
    """Get a summary of all configurations"""
    return {
        'vnc': vnc_config.to_dict(),
        'screenshot': screenshot_config.__dict__,
        'system': system_config.__dict__
    }

def validate_config() -> Dict[str, bool]:
    """Validate configuration settings"""
    validation_results = {}
    
    # Validate VNC configuration
    validation_results['vnc_novnc_path_exists'] = os.path.exists(vnc_config.novnc_path)
    validation_results['vnc_ports_valid'] = (
        vnc_config.base_vnc_port > 1024 and 
        vnc_config.base_websocket_port > 1024 and
        vnc_config.web_port > 1024
    )
    validation_results['vnc_max_sessions_valid'] = 1 <= vnc_config.max_sessions <= 50
    
    # Validate screenshot configuration
    validation_results['screenshot_interval_valid'] = screenshot_config.interval_seconds >= 1
    validation_results['screenshot_quality_valid'] = 1 <= screenshot_config.quality <= 100
    
    # Validate system configuration
    validation_results['system_max_sessions_valid'] = system_config.max_concurrent_sessions >= 1
    validation_results['system_timeout_valid'] = system_config.session_timeout >= 60
    
    return validation_results

if __name__ == "__main__":
    # Print configuration summary
    import json
    
    print("🔧 Configuration Summary:")
    print(json.dumps(get_config_summary(), indent=2))
    
    print("\n✅ Configuration Validation:")
    validation = validate_config()
    for key, is_valid in validation.items():
        status = "✅" if is_valid else "❌"
        print(f"   {status} {key}: {is_valid}")
    
    # Check if all validations passed
    all_valid = all(validation.values())
    print(f"\n🎯 Overall Configuration: {'✅ Valid' if all_valid else '❌ Invalid'}")