#!/usr/bin/env python3
"""
VNC Manager for noVNC Integration
Handles multiple VNC sessions for browser monitoring and interaction
"""

import os
import sys
import time
import signal
import subprocess
import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import threading
import psutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class VNCSession:
    """Represents a VNC session"""
    session_id: str
    user_id: str
    display_num: int
    vnc_port: int
    websocket_port: int
    xvfb_process: Optional[subprocess.Popen] = None
    x11vnc_process: Optional[subprocess.Popen] = None
    websockify_process: Optional[subprocess.Popen] = None
    fluxbox_process: Optional[subprocess.Popen] = None
    is_active: bool = False

class VNCManager:
    """Manages multiple VNC sessions for noVNC integration"""
    
    def __init__(self, base_display: int = 10, base_vnc_port: int = 5900, base_websocket_port: int = 6080):
        self.base_display = base_display
        self.base_vnc_port = base_vnc_port
        self.base_websocket_port = base_websocket_port
        self.sessions: Dict[str, VNCSession] = {}
        self.max_sessions = 10
        self.novnc_path = "/workspace/project/Exo-Mass/noVNC"
        self.lock = threading.Lock()
        
        # Ensure noVNC directory exists
        if not os.path.exists(self.novnc_path):
            logger.error(f"noVNC directory not found at {self.novnc_path}")
            raise FileNotFoundError(f"noVNC directory not found at {self.novnc_path}")
    
    def _get_next_available_ports(self) -> Tuple[int, int, int]:
        """Get next available display, VNC port, and websocket port"""
        with self.lock:
            for i in range(self.max_sessions):
                display_num = self.base_display + i
                vnc_port = self.base_vnc_port + i
                websocket_port = self.base_websocket_port + i
                
                # Check if ports are available
                if not self._is_port_in_use(vnc_port) and not self._is_port_in_use(websocket_port):
                    return display_num, vnc_port, websocket_port
            
            raise RuntimeError("No available ports for new VNC session")
    
    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is currently in use"""
        try:
            for conn in psutil.net_connections():
                if conn.laddr.port == port:
                    return True
            return False
        except Exception:
            return False
    
    def _kill_process_safely(self, process: Optional[subprocess.Popen], name: str) -> None:
        """Safely kill a process"""
        if process and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=5)
                logger.info(f"✅ {name} process terminated successfully")
            except subprocess.TimeoutExpired:
                logger.warning(f"⚠️ {name} process didn't terminate, killing forcefully")
                process.kill()
                process.wait()
            except Exception as e:
                logger.error(f"❌ Error terminating {name} process: {e}")
    
    def create_session(self, user_id: str, session_id: Optional[str] = None) -> Optional[VNCSession]:
        """Create a new VNC session for a user"""
        try:
            if len(self.sessions) >= self.max_sessions:
                logger.error(f"❌ Maximum number of VNC sessions ({self.max_sessions}) reached")
                return None
            
            if not session_id:
                session_id = f"vnc_{user_id}_{int(time.time())}"
            
            # Get available ports
            display_num, vnc_port, websocket_port = self._get_next_available_ports()
            
            # Create session object
            session = VNCSession(
                session_id=session_id,
                user_id=user_id,
                display_num=display_num,
                vnc_port=vnc_port,
                websocket_port=websocket_port
            )
            
            # Start Xvfb (virtual framebuffer)
            logger.info(f"🖥️ Starting Xvfb for display :{display_num}")
            xvfb_cmd = [
                "Xvfb", f":{display_num}",
                "-screen", "0", "1920x1080x24",
                "-ac", "+extension", "GLX", "+render", "-noreset"
            ]
            session.xvfb_process = subprocess.Popen(
                xvfb_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for Xvfb to start
            time.sleep(2)
            
            # Start Fluxbox window manager
            logger.info(f"🪟 Starting Fluxbox for display :{display_num}")
            env = os.environ.copy()
            env['DISPLAY'] = f":{display_num}"
            session.fluxbox_process = subprocess.Popen(
                ["fluxbox"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for Fluxbox to start
            time.sleep(1)
            
            # Start x11vnc
            logger.info(f"📡 Starting x11vnc on port {vnc_port} for display :{display_num}")
            x11vnc_cmd = [
                "x11vnc",
                "-display", f":{display_num}",
                "-rfbport", str(vnc_port),
                "-forever",
                "-shared",
                "-noxdamage",
                "-noxfixes",
                "-noxrandr",
                "-wait", "5",
                "-defer", "5"
            ]
            session.x11vnc_process = subprocess.Popen(
                x11vnc_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for x11vnc to start
            time.sleep(2)
            
            # Start websockify for noVNC
            logger.info(f"🌐 Starting websockify on port {websocket_port}")
            websockify_cmd = [
                "websockify",
                "--web", self.novnc_path,
                str(websocket_port),
                f"localhost:{vnc_port}"
            ]
            session.websockify_process = subprocess.Popen(
                websockify_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for websockify to start
            time.sleep(2)
            
            # Mark session as active
            session.is_active = True
            self.sessions[session_id] = session
            
            logger.info(f"✅ VNC session created successfully:")
            logger.info(f"   Session ID: {session_id}")
            logger.info(f"   User ID: {user_id}")
            logger.info(f"   Display: :{display_num}")
            logger.info(f"   VNC Port: {vnc_port}")
            logger.info(f"   WebSocket Port: {websocket_port}")
            logger.info(f"   noVNC URL: http://localhost:{websocket_port}/vnc.html")
            
            return session
            
        except Exception as e:
            logger.error(f"❌ Error creating VNC session: {e}")
            # Cleanup on failure
            if 'session' in locals():
                self._cleanup_session(session)
            return None
    
    def _cleanup_session(self, session: VNCSession) -> None:
        """Clean up a VNC session"""
        logger.info(f"🧹 Cleaning up VNC session {session.session_id}")
        
        # Kill processes in reverse order
        self._kill_process_safely(session.websockify_process, "websockify")
        self._kill_process_safely(session.x11vnc_process, "x11vnc")
        self._kill_process_safely(session.fluxbox_process, "fluxbox")
        self._kill_process_safely(session.xvfb_process, "Xvfb")
        
        session.is_active = False
    
    def destroy_session(self, session_id: str) -> bool:
        """Destroy a VNC session"""
        try:
            if session_id not in self.sessions:
                logger.warning(f"⚠️ Session {session_id} not found")
                return False
            
            session = self.sessions[session_id]
            self._cleanup_session(session)
            del self.sessions[session_id]
            
            logger.info(f"✅ VNC session {session_id} destroyed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error destroying VNC session {session_id}: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[VNCSession]:
        """Get a VNC session by ID"""
        return self.sessions.get(session_id)
    
    def get_user_sessions(self, user_id: str) -> List[VNCSession]:
        """Get all VNC sessions for a user"""
        return [session for session in self.sessions.values() if session.user_id == user_id]
    
    def list_sessions(self) -> List[VNCSession]:
        """List all active VNC sessions"""
        return list(self.sessions.values())
    
    def get_display_for_session(self, session_id: str) -> Optional[str]:
        """Get the DISPLAY environment variable for a session"""
        session = self.get_session(session_id)
        if session and session.is_active:
            return f":{session.display_num}"
        return None
    
    def get_novnc_url(self, session_id: str) -> Optional[str]:
        """Get the noVNC URL for a session"""
        session = self.get_session(session_id)
        if session and session.is_active:
            return f"http://localhost:{session.websocket_port}/vnc.html"
        return None
    
    def cleanup_all_sessions(self) -> None:
        """Clean up all VNC sessions"""
        logger.info("🧹 Cleaning up all VNC sessions")
        session_ids = list(self.sessions.keys())
        for session_id in session_ids:
            self.destroy_session(session_id)
    
    def health_check(self) -> Dict[str, bool]:
        """Check health of all VNC sessions"""
        health_status = {}
        
        for session_id, session in self.sessions.items():
            is_healthy = True
            
            # Check if processes are still running
            processes = [
                ("xvfb", session.xvfb_process),
                ("fluxbox", session.fluxbox_process),
                ("x11vnc", session.x11vnc_process),
                ("websockify", session.websockify_process)
            ]
            
            for name, process in processes:
                if not process or process.poll() is not None:
                    logger.warning(f"⚠️ {name} process died for session {session_id}")
                    is_healthy = False
            
            health_status[session_id] = is_healthy
            
            # Mark unhealthy sessions as inactive
            if not is_healthy:
                session.is_active = False
        
        return health_status
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.cleanup_all_sessions()
        except Exception:
            pass

# Global VNC manager instance
vnc_manager = VNCManager()

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("🛑 Received shutdown signal, cleaning up VNC sessions...")
    vnc_manager.cleanup_all_sessions()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    # Test the VNC manager
    logger.info("🧪 Testing VNC Manager")
    
    # Create a test session
    session = vnc_manager.create_session("test_user_123")
    if session:
        logger.info(f"✅ Test session created: {session.session_id}")
        logger.info(f"🌐 Access via: {vnc_manager.get_novnc_url(session.session_id)}")
        
        # Keep running for testing
        try:
            logger.info("🔄 VNC Manager running... Press Ctrl+C to stop")
            while True:
                time.sleep(10)
                health = vnc_manager.health_check()
                logger.info(f"💓 Health check: {health}")
        except KeyboardInterrupt:
            logger.info("🛑 Shutting down...")
            vnc_manager.cleanup_all_sessions()
    else:
        logger.error("❌ Failed to create test session")