#!/usr/bin/env python3
"""
Centralized Logging Configuration
Provides consistent logging across all modules
"""

import os
import sys
import logging
import logging.handlers
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record):
        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        
        # Format the message
        formatted = super().format(record)
        
        # Add emoji based on level
        emoji_map = {
            'DEBUG': '🔍',
            'INFO': 'ℹ️',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'CRITICAL': '🚨'
        }
        
        level_name = record.levelname.replace(self.COLORS.get(record.levelname.split('\033')[0], ''), '').replace(self.COLORS['RESET'], '')
        emoji = emoji_map.get(level_name, 'ℹ️')
        
        return f"{emoji} {formatted}"

class LoggingConfig:
    """Centralized logging configuration manager"""
    
    def __init__(self, 
                 log_dir: str = "logs",
                 log_level: str = "INFO",
                 console_output: bool = True,
                 file_output: bool = True,
                 max_file_size: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5):
        
        self.log_dir = Path(log_dir)
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.console_output = console_output
        self.file_output = file_output
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        
        # Create log directory
        self.log_dir.mkdir(exist_ok=True)
        
        # Configure root logger
        self._setup_root_logger()
        
        # Module-specific loggers
        self.loggers: Dict[str, logging.Logger] = {}
    
    def _setup_root_logger(self):
        """Set up the root logger"""
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        if self.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level)
            console_formatter = ColoredFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
        
        # File handler
        if self.file_output:
            log_file = self.log_dir / "system.log"
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count
            )
            file_handler.setLevel(self.log_level)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
    
    def get_logger(self, name: str, 
                   separate_file: bool = False,
                   file_level: Optional[str] = None) -> logging.Logger:
        """Get a logger for a specific module"""
        
        if name in self.loggers:
            return self.loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(self.log_level)
        
        # Add separate file handler if requested
        if separate_file and self.file_output:
            log_file = self.log_dir / f"{name.replace('.', '_')}.log"
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count
            )
            
            file_level = file_level or logging.getLevelName(self.log_level)
            file_handler.setLevel(getattr(logging, file_level.upper(), self.log_level))
            
            file_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        self.loggers[name] = logger
        return logger
    
    def set_level(self, level: str):
        """Change logging level for all loggers"""
        new_level = getattr(logging, level.upper(), logging.INFO)
        self.log_level = new_level
        
        # Update root logger
        logging.getLogger().setLevel(new_level)
        
        # Update all handlers
        for handler in logging.getLogger().handlers:
            handler.setLevel(new_level)
        
        # Update module loggers
        for logger in self.loggers.values():
            logger.setLevel(new_level)
    
    def get_log_files(self) -> Dict[str, Dict[str, Any]]:
        """Get information about log files"""
        log_files = {}
        
        for log_file in self.log_dir.glob("*.log"):
            try:
                stat = log_file.stat()
                log_files[log_file.name] = {
                    'path': str(log_file),
                    'size': stat.st_size,
                    'size_mb': round(stat.st_size / (1024 * 1024), 2),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'lines': self._count_lines(log_file)
                }
            except Exception as e:
                log_files[log_file.name] = {'error': str(e)}
        
        return log_files
    
    def _count_lines(self, file_path: Path) -> int:
        """Count lines in a file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return sum(1 for _ in f)
        except Exception:
            return 0
    
    def cleanup_old_logs(self, days: int = 7):
        """Clean up log files older than specified days"""
        import time
        
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        cleaned_files = []
        
        for log_file in self.log_dir.glob("*.log*"):
            try:
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    cleaned_files.append(str(log_file))
            except Exception as e:
                logging.warning(f"Failed to clean up {log_file}: {e}")
        
        if cleaned_files:
            logging.info(f"Cleaned up {len(cleaned_files)} old log files")
        
        return cleaned_files

# Global logging configuration
logging_config = LoggingConfig(
    log_level=os.getenv('LOG_LEVEL', 'INFO'),
    console_output=os.getenv('LOG_CONSOLE', 'true').lower() == 'true',
    file_output=os.getenv('LOG_FILE', 'true').lower() == 'true'
)

# Convenience functions
def get_logger(name: str, separate_file: bool = False) -> logging.Logger:
    """Get a logger instance"""
    return logging_config.get_logger(name, separate_file=separate_file)

def set_log_level(level: str):
    """Set logging level"""
    logging_config.set_level(level)

def get_log_info() -> Dict[str, Any]:
    """Get logging system information"""
    return {
        'level': logging.getLevelName(logging_config.log_level),
        'log_dir': str(logging_config.log_dir),
        'console_output': logging_config.console_output,
        'file_output': logging_config.file_output,
        'log_files': logging_config.get_log_files()
    }

# Module-specific loggers
vnc_logger = get_logger('vnc_system', separate_file=True)
browser_logger = get_logger('browser_automation', separate_file=True)
screenshot_logger = get_logger('screenshot_system', separate_file=True)
captcha_logger = get_logger('captcha_solver', separate_file=True)
api_logger = get_logger('api_server', separate_file=True)

if __name__ == "__main__":
    # Test logging configuration
    import json
    
    print("🔧 Logging Configuration Test")
    print(json.dumps(get_log_info(), indent=2))
    
    # Test different log levels
    test_logger = get_logger('test_module')
    
    test_logger.debug("This is a debug message")
    test_logger.info("This is an info message")
    test_logger.warning("This is a warning message")
    test_logger.error("This is an error message")
    test_logger.critical("This is a critical message")
    
    print("\n✅ Logging test completed")