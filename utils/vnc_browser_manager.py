#!/usr/bin/env python3
"""
VNC Browser Manager
Integrates browser automation with VNC sessions for visual monitoring
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from .vnc_manager import vnc_manager, VNCSession

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VNCBrowserManager:
    """Manages browser instances within VNC sessions"""
    
    def __init__(self):
        self.browser_sessions: Dict[str, Dict[str, Any]] = {}
    
    async def create_browser_session(self, user_id: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Create a new browser session within a VNC display"""
        try:
            # Create VNC session first
            vnc_session = vnc_manager.create_session(user_id, session_id)
            if not vnc_session:
                logger.error(f"❌ Failed to create VNC session for user {user_id}")
                return None
            
            # Get display environment
            display = vnc_manager.get_display_for_session(vnc_session.session_id)
            if not display:
                logger.error(f"❌ Failed to get display for session {vnc_session.session_id}")
                vnc_manager.destroy_session(vnc_session.session_id)
                return None
            
            # Set up environment for browser
            env = os.environ.copy()
            env['DISPLAY'] = display
            
            # Launch Playwright with non-headless browser
            playwright = await async_playwright().start()
            
            # Configure browser for VNC display
            browser = await playwright.chromium.launch(
                headless=False,  # Non-headless for VNC visibility
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--window-size=1920,1080',
                    '--start-maximized'
                ],
                env=env
            )
            
            # Create browser context
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # Create initial page
            page = await context.new_page()
            
            # Store session info
            session_info = {
                'vnc_session': vnc_session,
                'playwright': playwright,
                'browser': browser,
                'context': context,
                'page': page,
                'user_id': user_id,
                'session_id': vnc_session.session_id,
                'display': display,
                'novnc_url': vnc_manager.get_novnc_url(vnc_session.session_id)
            }
            
            self.browser_sessions[vnc_session.session_id] = session_info
            
            logger.info(f"✅ Browser session created successfully:")
            logger.info(f"   Session ID: {vnc_session.session_id}")
            logger.info(f"   User ID: {user_id}")
            logger.info(f"   Display: {display}")
            logger.info(f"   noVNC URL: {session_info['novnc_url']}")
            
            return session_info
            
        except Exception as e:
            logger.error(f"❌ Error creating browser session: {e}")
            # Cleanup on failure
            if 'vnc_session' in locals() and vnc_session:
                vnc_manager.destroy_session(vnc_session.session_id)
            return None
    
    async def get_browser_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get an existing browser session"""
        return self.browser_sessions.get(session_id)
    
    async def destroy_browser_session(self, session_id: str) -> bool:
        """Destroy a browser session and its VNC session"""
        try:
            if session_id not in self.browser_sessions:
                logger.warning(f"⚠️ Browser session {session_id} not found")
                return False
            
            session_info = self.browser_sessions[session_id]
            
            # Close browser components
            try:
                if session_info.get('page'):
                    await session_info['page'].close()
                if session_info.get('context'):
                    await session_info['context'].close()
                if session_info.get('browser'):
                    await session_info['browser'].close()
                if session_info.get('playwright'):
                    await session_info['playwright'].stop()
            except Exception as e:
                logger.warning(f"⚠️ Error closing browser components: {e}")
            
            # Destroy VNC session
            vnc_manager.destroy_session(session_id)
            
            # Remove from tracking
            del self.browser_sessions[session_id]
            
            logger.info(f"✅ Browser session {session_id} destroyed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error destroying browser session {session_id}: {e}")
            return False
    
    async def navigate_to_url(self, session_id: str, url: str) -> bool:
        """Navigate to a URL in the specified session"""
        try:
            session_info = await self.get_browser_session(session_id)
            if not session_info:
                logger.error(f"❌ Session {session_id} not found")
                return False
            
            page = session_info['page']
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            logger.info(f"✅ Navigated to {url} in session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error navigating to {url} in session {session_id}: {e}")
            return False
    
    async def take_screenshot(self, session_id: str, filename: Optional[str] = None) -> Optional[bytes]:
        """Take a screenshot of the browser session"""
        try:
            session_info = await self.get_browser_session(session_id)
            if not session_info:
                logger.error(f"❌ Session {session_id} not found")
                return None
            
            page = session_info['page']
            screenshot_bytes = await page.screenshot(full_page=True)
            
            if filename:
                with open(filename, 'wb') as f:
                    f.write(screenshot_bytes)
                logger.info(f"📸 Screenshot saved to {filename}")
            
            return screenshot_bytes
            
        except Exception as e:
            logger.error(f"❌ Error taking screenshot for session {session_id}: {e}")
            return None
    
    def list_sessions(self) -> Dict[str, Dict[str, Any]]:
        """List all active browser sessions"""
        return {
            session_id: {
                'user_id': info['user_id'],
                'display': info['display'],
                'novnc_url': info['novnc_url'],
                'session_id': session_id
            }
            for session_id, info in self.browser_sessions.items()
        }
    
    async def cleanup_all_sessions(self) -> None:
        """Clean up all browser sessions"""
        logger.info("🧹 Cleaning up all browser sessions")
        session_ids = list(self.browser_sessions.keys())
        for session_id in session_ids:
            await self.destroy_browser_session(session_id)
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all browser sessions"""
        health_status = {}
        
        for session_id, session_info in self.browser_sessions.items():
            try:
                # Check if browser is still connected
                browser = session_info.get('browser')
                if browser and browser.is_connected():
                    health_status[session_id] = True
                else:
                    health_status[session_id] = False
                    logger.warning(f"⚠️ Browser disconnected for session {session_id}")
            except Exception as e:
                health_status[session_id] = False
                logger.warning(f"⚠️ Health check failed for session {session_id}: {e}")
        
        return health_status

# Global browser manager instance
vnc_browser_manager = VNCBrowserManager()

async def main():
    """Test the VNC Browser Manager"""
    logger.info("🧪 Testing VNC Browser Manager")
    
    try:
        # Create a test browser session
        session_info = await vnc_browser_manager.create_browser_session("test_user_456")
        if session_info:
            session_id = session_info['session_id']
            logger.info(f"✅ Test browser session created: {session_id}")
            logger.info(f"🌐 Access via: {session_info['novnc_url']}")
            
            # Navigate to a test page
            await vnc_browser_manager.navigate_to_url(session_id, "https://www.google.com")
            
            # Take a screenshot
            screenshot = await vnc_browser_manager.take_screenshot(session_id, "test_screenshot.png")
            if screenshot:
                logger.info("📸 Screenshot taken successfully")
            
            # Keep running for testing
            logger.info("🔄 Browser session running... Press Ctrl+C to stop")
            await asyncio.sleep(30)  # Run for 30 seconds for testing
            
            # Cleanup
            await vnc_browser_manager.destroy_browser_session(session_id)
        else:
            logger.error("❌ Failed to create test browser session")
            
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down...")
    finally:
        await vnc_browser_manager.cleanup_all_sessions()

if __name__ == "__main__":
    asyncio.run(main())