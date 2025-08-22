#!/usr/bin/env python3
"""
Browser Factory
Creates browser instances with optional VNC integration for visual monitoring
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, Tuple
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from .vnc_browser_manager import vnc_browser_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrowserFactory:
    """Factory for creating browser instances with optional VNC integration"""
    
    def __init__(self):
        self.use_vnc = os.getenv('USE_VNC', 'false').lower() == 'true'
        self.vnc_sessions: Dict[str, Any] = {}
    
    async def create_browser_session(
        self, 
        user_id: str, 
        headless: Optional[bool] = None,
        use_vnc: Optional[bool] = None
    ) -> Tuple[Browser, BrowserContext, Page, Optional[str]]:
        """
        Create a browser session with optional VNC integration
        
        Args:
            user_id: Unique identifier for the user/session
            headless: Override headless mode (None = use default)
            use_vnc: Override VNC usage (None = use environment setting)
            
        Returns:
            Tuple of (browser, context, page, vnc_session_id)
        """
        try:
            # Determine if we should use VNC
            should_use_vnc = use_vnc if use_vnc is not None else self.use_vnc
            
            if should_use_vnc:
                # Create VNC-integrated browser session
                return await self._create_vnc_browser_session(user_id)
            else:
                # Create regular headless browser session
                return await self._create_regular_browser_session(user_id, headless)
                
        except Exception as e:
            logger.error(f"❌ Error creating browser session for user {user_id}: {e}")
            raise
    
    async def _create_vnc_browser_session(self, user_id: str) -> Tuple[Browser, BrowserContext, Page, str]:
        """Create a browser session with VNC integration"""
        logger.info(f"🖥️ Creating VNC browser session for user {user_id}")
        
        session_info = await vnc_browser_manager.create_browser_session(user_id)
        if not session_info:
            raise RuntimeError(f"Failed to create VNC browser session for user {user_id}")
        
        session_id = session_info['session_id']
        self.vnc_sessions[session_id] = session_info
        
        logger.info(f"✅ VNC browser session created: {session_id}")
        logger.info(f"🌐 Access via: {session_info['novnc_url']}")
        
        return (
            session_info['browser'],
            session_info['context'],
            session_info['page'],
            session_id
        )
    
    async def _create_regular_browser_session(
        self, 
        user_id: str, 
        headless: Optional[bool] = None
    ) -> Tuple[Browser, BrowserContext, Page, None]:
        """Create a regular browser session without VNC"""
        logger.info(f"🌐 Creating regular browser session for user {user_id}")
        
        # Default to headless if not specified
        is_headless = headless if headless is not None else True
        
        playwright = await async_playwright().start()
        
        browser = await playwright.chromium.launch(
            headless=is_headless,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        logger.info(f"✅ Regular browser session created for user {user_id} (headless: {is_headless})")
        
        return browser, context, page, None
    
    async def destroy_browser_session(
        self, 
        browser: Browser, 
        context: BrowserContext, 
        page: Page, 
        vnc_session_id: Optional[str] = None
    ) -> None:
        """Destroy a browser session and clean up resources"""
        try:
            if vnc_session_id:
                # VNC session cleanup
                logger.info(f"🧹 Destroying VNC browser session: {vnc_session_id}")
                await vnc_browser_manager.destroy_browser_session(vnc_session_id)
                if vnc_session_id in self.vnc_sessions:
                    del self.vnc_sessions[vnc_session_id]
            else:
                # Regular session cleanup
                logger.info("🧹 Destroying regular browser session")
                if page and not page.is_closed():
                    await page.close()
                if context:
                    await context.close()
                if browser and browser.is_connected():
                    await browser.close()
            
            logger.info("✅ Browser session destroyed successfully")
            
        except Exception as e:
            logger.error(f"❌ Error destroying browser session: {e}")
    
    async def get_vnc_url(self, vnc_session_id: str) -> Optional[str]:
        """Get the noVNC URL for a VNC session"""
        if vnc_session_id in self.vnc_sessions:
            return self.vnc_sessions[vnc_session_id]['novnc_url']
        return None
    
    def list_vnc_sessions(self) -> Dict[str, Dict[str, Any]]:
        """List all active VNC sessions"""
        return {
            session_id: {
                'user_id': info['user_id'],
                'novnc_url': info['novnc_url'],
                'display': info['display']
            }
            for session_id, info in self.vnc_sessions.items()
        }
    
    async def cleanup_all_sessions(self) -> None:
        """Clean up all browser sessions"""
        logger.info("🧹 Cleaning up all browser sessions")
        
        # Clean up VNC sessions
        vnc_session_ids = list(self.vnc_sessions.keys())
        for session_id in vnc_session_ids:
            try:
                await vnc_browser_manager.destroy_browser_session(session_id)
                if session_id in self.vnc_sessions:
                    del self.vnc_sessions[session_id]
            except Exception as e:
                logger.error(f"❌ Error cleaning up VNC session {session_id}: {e}")

# Global browser factory instance
browser_factory = BrowserFactory()

async def main():
    """Test the Browser Factory"""
    logger.info("🧪 Testing Browser Factory")
    
    try:
        # Test VNC browser session
        logger.info("Testing VNC browser session...")
        browser, context, page, vnc_session_id = await browser_factory.create_browser_session(
            "test_user_789", 
            use_vnc=True
        )
        
        if vnc_session_id:
            logger.info(f"✅ VNC session created: {vnc_session_id}")
            vnc_url = await browser_factory.get_vnc_url(vnc_session_id)
            logger.info(f"🌐 Access via: {vnc_url}")
            
            # Navigate to a test page
            await page.goto("https://www.example.com")
            logger.info("📄 Navigated to example.com")
            
            # Wait a bit for testing
            await asyncio.sleep(10)
            
            # Cleanup
            await browser_factory.destroy_browser_session(browser, context, page, vnc_session_id)
        
        # Test regular browser session
        logger.info("Testing regular browser session...")
        browser, context, page, _ = await browser_factory.create_browser_session(
            "test_user_regular", 
            use_vnc=False,
            headless=True
        )
        
        await page.goto("https://www.example.com")
        logger.info("📄 Navigated to example.com (headless)")
        
        # Cleanup
        await browser_factory.destroy_browser_session(browser, context, page)
        
        logger.info("✅ All tests completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
    finally:
        await browser_factory.cleanup_all_sessions()

if __name__ == "__main__":
    asyncio.run(main())