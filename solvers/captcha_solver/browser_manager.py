#!/usr/bin/env python3
"""
Browser Manager for Captcha Solver
Manages browser instances with anti-detection features and VNC integration
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
import random
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import VNC integration
try:
    from vnc_integration import captcha_solver_vnc
    VNC_AVAILABLE = True
except ImportError:
    VNC_AVAILABLE = False
    captcha_solver_vnc = None

logger = logging.getLogger("BrowserManager")

class BrowserPool:
    """Manages a pool of browser instances for concurrent captcha solving"""
    
    def __init__(self, max_browsers: int = 4, browser_type: str = "camoufox", 
                 headless: bool = True, use_vnc: bool = False):
        self.max_browsers = max_browsers
        self.browser_type = browser_type.lower()
        self.headless = headless and not use_vnc  # Force non-headless if VNC is enabled
        self.use_vnc = use_vnc and VNC_AVAILABLE
        
        self.playwright: Optional[Playwright] = None
        self.browsers: List[Dict[str, Any]] = []
        self.available_browsers: asyncio.Queue = asyncio.Queue()
        self.browser_counter = 0
        
        if self.use_vnc:
            logger.info("🖥️ VNC integration enabled - browsers will run in non-headless mode")
        
        logger.info(f"🌐 Browser pool initialized: {max_browsers} {browser_type} browsers, headless={self.headless}")
    
    async def initialize(self):
        """Initialize the browser pool"""
        try:
            self.playwright = await async_playwright().start()
            
            # Create initial browsers
            for i in range(self.max_browsers):
                browser_info = await self._create_browser(f"browser_{i}")
                if browser_info:
                    self.browsers.append(browser_info)
                    await self.available_browsers.put(browser_info)
            
            logger.info(f"✅ Browser pool initialized with {len(self.browsers)} browsers")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize browser pool: {e}")
            raise
    
    async def _create_browser(self, browser_id: str) -> Optional[Dict[str, Any]]:
        """Create a single browser instance"""
        try:
            # VNC session setup
            vnc_session_info = None
            if self.use_vnc and captcha_solver_vnc:
                vnc_session_info = await captcha_solver_vnc.create_solver_session(
                    solver_id=browser_id,
                    task_type="browser"
                )
            
            # Browser launch arguments
            launch_args = self._get_browser_args()
            
            # Launch browser based on type
            if self.browser_type == "camoufox":
                browser = await self._launch_camoufox(launch_args)
            elif self.browser_type == "chromium":
                browser = await self.playwright.chromium.launch(
                    headless=self.headless,
                    args=launch_args
                )
            elif self.browser_type == "chrome":
                browser = await self.playwright.chromium.launch(
                    headless=self.headless,
                    channel="chrome",
                    args=launch_args
                )
            elif self.browser_type == "edge":
                browser = await self.playwright.chromium.launch(
                    headless=self.headless,
                    channel="msedge",
                    args=launch_args
                )
            else:
                logger.warning(f"⚠️ Unknown browser type {self.browser_type}, using chromium")
                browser = await self.playwright.chromium.launch(
                    headless=self.headless,
                    args=launch_args
                )
            
            browser_info = {
                'id': browser_id,
                'browser': browser,
                'vnc_session': vnc_session_info,
                'in_use': False,
                'created_at': asyncio.get_event_loop().time()
            }
            
            logger.info(f"✅ Created browser {browser_id} ({self.browser_type})")
            if vnc_session_info:
                vnc_url = vnc_session_info.get('vnc_urls', {}).get('vnc_direct', 'N/A')
                logger.info(f"🖥️ VNC access: {vnc_url}")
            
            return browser_info
            
        except Exception as e:
            logger.error(f"❌ Failed to create browser {browser_id}: {e}")
            return None
    
    async def _launch_camoufox(self, args: List[str]) -> Browser:
        """Launch Camoufox browser with anti-detection"""
        try:
            # Try to use camoufox if available
            camoufox_path = self._find_camoufox_executable()
            if camoufox_path:
                return await self.playwright.firefox.launch(
                    headless=self.headless,
                    executable_path=camoufox_path,
                    args=args + [
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox'
                    ]
                )
            else:
                logger.warning("⚠️ Camoufox not found, using Firefox")
                return await self.playwright.firefox.launch(
                    headless=self.headless,
                    args=args
                )
        except Exception as e:
            logger.warning(f"⚠️ Failed to launch Camoufox: {e}, falling back to Firefox")
            return await self.playwright.firefox.launch(
                headless=self.headless,
                args=args
            )
    
    def _find_camoufox_executable(self) -> Optional[str]:
        """Find Camoufox executable path"""
        possible_paths = [
            '/root/.cache/camoufox/camoufox',  # Default Camoufox installation path
            os.path.expanduser('~/.cache/camoufox/camoufox'),  # User cache path
            '/usr/bin/camoufox',
            '/usr/local/bin/camoufox',
            '/opt/camoufox/camoufox',
            os.path.expanduser('~/.local/bin/camoufox'),
            './camoufox'
        ]
        
        for path in possible_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        
        return None
    
    def _get_browser_args(self) -> List[str]:
        """Get browser launch arguments with anti-detection"""
        base_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-features=TranslateUI',
            '--disable-ipc-flooding-protection',
            '--enable-features=NetworkService',
            '--disable-background-networking',
            '--disable-sync',
            '--metrics-recording-only',
            '--disable-default-apps',
            '--no-first-run',
            '--mute-audio',
            '--hide-scrollbars',
            '--disable-component-update',
            '--disable-domain-reliability'
        ]
        
        # Add window size for non-headless mode
        if not self.headless:
            base_args.extend([
                '--window-size=1280,720',
                '--window-position=0,0'
            ])
        
        return base_args
    
    async def get_browser(self) -> Optional[Dict[str, Any]]:
        """Get an available browser from the pool"""
        try:
            # Wait for available browser (with timeout)
            browser_info = await asyncio.wait_for(
                self.available_browsers.get(), 
                timeout=30.0
            )
            
            browser_info['in_use'] = True
            logger.debug(f"🔄 Browser {browser_info['id']} acquired")
            return browser_info
            
        except asyncio.TimeoutError:
            logger.error("❌ Timeout waiting for available browser")
            return None
        except Exception as e:
            logger.error(f"❌ Error getting browser: {e}")
            return None
    
    async def return_browser(self, browser_info: Dict[str, Any]):
        """Return a browser to the pool"""
        try:
            browser_info['in_use'] = False
            await self.available_browsers.put(browser_info)
            logger.debug(f"🔄 Browser {browser_info['id']} returned to pool")
            
        except Exception as e:
            logger.error(f"❌ Error returning browser: {e}")
    
    async def create_context(self, browser_info: Dict[str, Any]) -> Optional[BrowserContext]:
        """Create a new browser context with anti-detection"""
        try:
            browser = browser_info['browser']
            
            # Random user agent
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ]
            
            context = await browser.new_context(
                user_agent=random.choice(user_agents),
                viewport={'width': 1280, 'height': 720},
                locale='en-US',
                timezone_id='America/New_York',
                permissions=['geolocation'],
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            )
            
            # Add anti-detection scripts
            await context.add_init_script("""
                // Remove webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                
                // Mock permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            return context
            
        except Exception as e:
            logger.error(f"❌ Error creating browser context: {e}")
            return None
    
    async def close_browser(self, browser_info: Dict[str, Any]):
        """Close a specific browser"""
        try:
            browser = browser_info['browser']
            await browser.close()
            
            # Clean up VNC session if exists
            if browser_info.get('vnc_session') and captcha_solver_vnc:
                session_id = f"solver_{browser_info['id']}_browser"
                await captcha_solver_vnc.cleanup_session(session_id)
            
            logger.info(f"🔒 Browser {browser_info['id']} closed")
            
        except Exception as e:
            logger.error(f"❌ Error closing browser: {e}")
    
    async def close_all(self):
        """Close all browsers and cleanup"""
        try:
            # Close all browsers
            for browser_info in self.browsers:
                await self.close_browser(browser_info)
            
            # Stop playwright
            if self.playwright:
                await self.playwright.stop()
            
            # Clean up VNC sessions
            if captcha_solver_vnc:
                await captcha_solver_vnc.cleanup_all_sessions()
            
            logger.info("🔒 All browsers closed and cleaned up")
            
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get status of the browser pool"""
        in_use = sum(1 for b in self.browsers if b['in_use'])
        available = len(self.browsers) - in_use
        
        return {
            'total_browsers': len(self.browsers),
            'in_use': in_use,
            'available': available,
            'browser_type': self.browser_type,
            'headless': self.headless,
            'vnc_enabled': self.use_vnc,
            'browsers': [
                {
                    'id': b['id'],
                    'in_use': b['in_use'],
                    'created_at': b['created_at'],
                    'has_vnc': bool(b.get('vnc_session'))
                }
                for b in self.browsers
            ]
        }

class BrowserManager:
    """Main browser manager for captcha solver"""
    
    def __init__(self, max_browsers: int = 4, browser_type: str = "camoufox", 
                 headless: bool = True, debug: bool = False):
        self.debug = debug
        self.use_vnc = os.getenv('USE_VNC', 'false').lower() == 'true'
        
        # Override headless if VNC is enabled
        if self.use_vnc:
            headless = False
            logger.info("🖥️ VNC enabled - forcing non-headless mode")
        
        self.browser_pool = BrowserPool(
            max_browsers=max_browsers,
            browser_type=browser_type,
            headless=headless,
            use_vnc=self.use_vnc
        )
    
    async def initialize(self):
        """Initialize the browser manager"""
        await self.browser_pool.initialize()
        logger.info("✅ Browser manager initialized")
    
    async def get_browser_session(self) -> Optional[Dict[str, Any]]:
        """Get a browser session for captcha solving"""
        browser_info = await self.browser_pool.get_browser()
        if not browser_info:
            return None
        
        context = await self.browser_pool.create_context(browser_info)
        if not context:
            await self.browser_pool.return_browser(browser_info)
            return None
        
        page = await context.new_page()
        
        return {
            'browser_info': browser_info,
            'context': context,
            'page': page,
            'vnc_session': browser_info.get('vnc_session')
        }
    
    async def return_browser_session(self, session: Dict[str, Any]):
        """Return a browser session to the pool"""
        try:
            # Close context and page
            context = session.get('context')
            if context:
                await context.close()
            
            # Return browser to pool
            browser_info = session.get('browser_info')
            if browser_info:
                await self.browser_pool.return_browser(browser_info)
            
        except Exception as e:
            logger.error(f"❌ Error returning browser session: {e}")
    
    async def close(self):
        """Close the browser manager"""
        await self.browser_pool.close_all()
        logger.info("🔒 Browser manager closed")
    
    def get_status(self) -> Dict[str, Any]:
        """Get browser manager status"""
        return {
            'pool_status': self.browser_pool.get_pool_status(),
            'vnc_enabled': self.use_vnc,
            'debug_mode': self.debug
        }