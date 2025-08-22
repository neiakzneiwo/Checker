#!/usr/bin/env python3
"""
VNC Integration for Captcha Solver
Provides visual monitoring capabilities for captcha solving process
"""

import os
import sys
import asyncio
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from utils.vnc_manager import vnc_manager
    from utils.vnc_browser_manager import VNCBrowserManager
    VNC_AVAILABLE = True
except ImportError:
    VNC_AVAILABLE = False

logger = logging.getLogger("VNCIntegration")

class CaptchaSolverVNC:
    """VNC integration for captcha solver with visual monitoring"""
    
    def __init__(self):
        self.vnc_enabled = os.getenv('USE_VNC', 'false').lower() == 'true' and VNC_AVAILABLE
        self.vnc_browser_manager = VNCBrowserManager() if self.vnc_enabled else None
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        if self.vnc_enabled:
            logger.info("✅ VNC integration enabled for captcha solver")
        else:
            if not VNC_AVAILABLE:
                logger.warning("⚠️ VNC components not available - install VNC dependencies")
            else:
                logger.info("ℹ️ VNC integration disabled (set USE_VNC=true to enable)")
    
    async def create_solver_session(self, solver_id: str, task_type: str = "captcha") -> Optional[Dict[str, Any]]:
        """Create a VNC session for captcha solving with visual monitoring"""
        if not self.vnc_enabled:
            return None
        
        try:
            session_id = f"solver_{solver_id}_{task_type}"
            
            # Create browser session with VNC
            browser_session = await self.vnc_browser_manager.create_browser_session(
                user_id=solver_id,
                session_id=session_id
            )
            
            if browser_session:
                # Get VNC access URLs
                vnc_session = browser_session.get('vnc_session')
                if vnc_session:
                    vnc_urls = {
                        'vnc_direct': f"http://localhost:{vnc_session.websocket_port}/vnc.html",
                        'session_info': {
                            'session_id': vnc_session.session_id,
                            'display': vnc_session.display,
                            'vnc_port': vnc_session.vnc_port,
                            'websocket_port': vnc_session.websocket_port
                        }
                    }
                    
                    browser_session['vnc_urls'] = vnc_urls
                    self.active_sessions[session_id] = browser_session
                    
                    logger.info(f"🖥️ VNC session created for solver {solver_id}")
                    logger.info(f"🌐 VNC Access: {vnc_urls['vnc_direct']}")
                    
                    return browser_session
            
            logger.error(f"❌ Failed to create VNC session for solver {solver_id}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error creating VNC session: {e}")
            return None
    
    async def get_browser_for_session(self, session_id: str) -> Optional[Any]:
        """Get browser instance for VNC session"""
        if not self.vnc_enabled or session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        return session.get('browser')
    
    async def create_page_in_session(self, session_id: str) -> Optional[Any]:
        """Create a new page in the VNC browser session"""
        if not self.vnc_enabled or session_id not in self.active_sessions:
            return None
        
        try:
            session = self.active_sessions[session_id]
            browser = session.get('browser')
            
            if browser:
                page = await browser.new_page()
                
                # Configure page for captcha solving
                await page.set_viewport_size({"width": 1280, "height": 720})
                await page.set_extra_http_headers({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                })
                
                logger.info(f"📄 New page created in VNC session {session_id}")
                return page
            
        except Exception as e:
            logger.error(f"❌ Error creating page in VNC session: {e}")
        
        return None
    
    async def take_screenshot_in_session(self, session_id: str, path: Optional[str] = None) -> Optional[bytes]:
        """Take screenshot of VNC session"""
        if not self.vnc_enabled or session_id not in self.active_sessions:
            return None
        
        try:
            session = self.active_sessions[session_id]
            browser = session.get('browser')
            
            if browser:
                pages = browser.contexts[0].pages if browser.contexts else []
                if pages:
                    page = pages[0]  # Use first page
                    screenshot = await page.screenshot(path=path, full_page=True)
                    logger.info(f"📸 Screenshot taken for VNC session {session_id}")
                    return screenshot
            
        except Exception as e:
            logger.error(f"❌ Error taking screenshot in VNC session: {e}")
        
        return None
    
    async def monitor_captcha_solving(self, session_id: str, url: str, 
                                    callback: Optional[callable] = None) -> Dict[str, Any]:
        """Monitor captcha solving process with visual feedback"""
        if not self.vnc_enabled:
            return {"status": "vnc_disabled"}
        
        try:
            page = await self.create_page_in_session(session_id)
            if not page:
                return {"status": "error", "message": "Failed to create page"}
            
            logger.info(f"🔍 Starting captcha monitoring for {url}")
            
            # Navigate to URL
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # Take initial screenshot
            initial_screenshot = await self.take_screenshot_in_session(session_id)
            
            # Monitor for captcha elements
            monitoring_result = {
                "status": "monitoring",
                "url": url,
                "session_id": session_id,
                "initial_screenshot": bool(initial_screenshot),
                "vnc_url": self.active_sessions[session_id]['vnc_urls']['vnc_direct']
            }
            
            # Call callback if provided
            if callback:
                try:
                    await callback(page, monitoring_result)
                except Exception as e:
                    logger.error(f"❌ Callback error: {e}")
            
            return monitoring_result
            
        except Exception as e:
            logger.error(f"❌ Error monitoring captcha solving: {e}")
            return {"status": "error", "message": str(e)}
    
    async def highlight_captcha_elements(self, session_id: str, elements: List[str]) -> bool:
        """Highlight captcha elements in VNC session for visual feedback"""
        if not self.vnc_enabled or session_id not in self.active_sessions:
            return False
        
        try:
            session = self.active_sessions[session_id]
            browser = session.get('browser')
            
            if browser and browser.contexts:
                pages = browser.contexts[0].pages
                if pages:
                    page = pages[0]
                    
                    # Add highlighting CSS
                    await page.add_style_tag(content="""
                        .captcha-highlight {
                            border: 3px solid #ff0000 !important;
                            box-shadow: 0 0 10px #ff0000 !important;
                            animation: pulse 1s infinite !important;
                        }
                        @keyframes pulse {
                            0% { opacity: 1; }
                            50% { opacity: 0.5; }
                            100% { opacity: 1; }
                        }
                    """)
                    
                    # Highlight elements
                    for element_selector in elements:
                        try:
                            await page.evaluate(f"""
                                const elements = document.querySelectorAll('{element_selector}');
                                elements.forEach(el => el.classList.add('captcha-highlight'));
                            """)
                        except:
                            continue
                    
                    logger.info(f"🎯 Highlighted {len(elements)} captcha elements in VNC session")
                    return True
            
        except Exception as e:
            logger.error(f"❌ Error highlighting elements: {e}")
        
        return False
    
    async def show_solving_progress(self, session_id: str, progress: Dict[str, Any]) -> bool:
        """Show solving progress overlay in VNC session"""
        if not self.vnc_enabled or session_id not in self.active_sessions:
            return False
        
        try:
            session = self.active_sessions[session_id]
            browser = session.get('browser')
            
            if browser and browser.contexts:
                pages = browser.contexts[0].pages
                if pages:
                    page = pages[0]
                    
                    # Create progress overlay
                    overlay_html = f"""
                    <div id="captcha-solver-overlay" style="
                        position: fixed;
                        top: 10px;
                        right: 10px;
                        background: rgba(0, 0, 0, 0.8);
                        color: white;
                        padding: 15px;
                        border-radius: 8px;
                        font-family: Arial, sans-serif;
                        font-size: 14px;
                        z-index: 10000;
                        max-width: 300px;
                    ">
                        <h3 style="margin: 0 0 10px 0; color: #4CAF50;">🤖 Captcha Solver</h3>
                        <div><strong>Status:</strong> {progress.get('status', 'Unknown')}</div>
                        <div><strong>Model:</strong> {progress.get('model', 'N/A')}</div>
                        <div><strong>Progress:</strong> {progress.get('step', 'N/A')}</div>
                        {f"<div><strong>Result:</strong> {progress.get('result', 'N/A')}</div>" if progress.get('result') else ""}
                        <div style="margin-top: 10px; font-size: 12px; color: #ccc;">
                            Session: {session_id}
                        </div>
                    </div>
                    """
                    
                    # Remove existing overlay and add new one
                    await page.evaluate("""
                        const existing = document.getElementById('captcha-solver-overlay');
                        if (existing) existing.remove();
                    """)
                    
                    await page.evaluate(f"""
                        document.body.insertAdjacentHTML('beforeend', `{overlay_html}`);
                    """)
                    
                    logger.info(f"📊 Updated solving progress in VNC session")
                    return True
            
        except Exception as e:
            logger.error(f"❌ Error showing progress: {e}")
        
        return False
    
    async def cleanup_session(self, session_id: str) -> bool:
        """Clean up VNC session"""
        if not self.vnc_enabled or session_id not in self.active_sessions:
            return False
        
        try:
            session = self.active_sessions[session_id]
            
            # Close browser
            browser = session.get('browser')
            if browser:
                await browser.close()
            
            # Close playwright
            playwright = session.get('playwright')
            if playwright:
                await playwright.stop()
            
            # Destroy VNC session
            vnc_session = session.get('vnc_session')
            if vnc_session:
                vnc_manager.destroy_session(vnc_session.session_id)
            
            # Remove from active sessions
            del self.active_sessions[session_id]
            
            logger.info(f"🧹 Cleaned up VNC session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up VNC session: {e}")
            return False
    
    async def cleanup_all_sessions(self):
        """Clean up all active VNC sessions"""
        if not self.vnc_enabled:
            return
        
        session_ids = list(self.active_sessions.keys())
        for session_id in session_ids:
            await self.cleanup_session(session_id)
        
        logger.info("🧹 All VNC sessions cleaned up")
    
    def get_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get information about active VNC sessions"""
        if not self.vnc_enabled:
            return {}
        
        return {
            session_id: {
                'session_id': session_id,
                'vnc_urls': session.get('vnc_urls', {}),
                'created_at': session.get('created_at'),
                'status': 'active'
            }
            for session_id, session in self.active_sessions.items()
        }
    
    def is_vnc_enabled(self) -> bool:
        """Check if VNC is enabled and available"""
        return self.vnc_enabled

# Global instance
captcha_solver_vnc = CaptchaSolverVNC()
