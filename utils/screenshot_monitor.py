"""
Screenshot Monitor - Takes screenshots every 10 seconds during account checking ONLY
Restricted to account checking process with user-specific folders
"""
import asyncio
import logging
import time
from typing import Optional
from playwright.async_api import Page
from .dropbox_uploader import DropboxUploader

logger = logging.getLogger(__name__)

class ScreenshotMonitor:
    """
    Monitors account checking process and takes screenshots every 10 seconds
    RESTRICTED TO ACCOUNT CHECKING ONLY - No other processes allowed
    """
    
    def __init__(self, dropbox_uploader: DropboxUploader, user_id: str):
        self.dropbox_uploader = dropbox_uploader
        self.user_id = user_id  # User-specific folder identification
        self.monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.screenshot_count = 0
        
    async def start_monitoring(self, page: Page, email: str, process_name: str = "account_check"):
        """
        Start taking screenshots every 10 seconds - ACCOUNT CHECKING ONLY
        
        Args:
            page: Playwright page to screenshot
            email: Email being checked (for filename)
            process_name: Must be "account_check" - other processes not allowed
        """
        # RESTRICTION: Only allow account checking process
        if process_name != "account_check":
            logger.error(f"🚫 Screenshot monitoring DENIED for process '{process_name}' - Only 'account_check' allowed")
            return
            
        if self.monitoring:
            logger.warning("📸 Screenshot monitoring already running")
            return
            
        self.monitoring = True
        self.screenshot_count = 0
        logger.info(f"📸 {email} - Starting screenshot monitoring every 10 seconds for user {self.user_id}...")
        
        # Start the monitoring task
        self.monitor_task = asyncio.create_task(
            self._monitor_loop(page, email, process_name)
        )
        
    async def stop_monitoring(self, page: Page = None, email: str = ""):
        """Stop screenshot monitoring and take final screenshot after 10 seconds"""
        if not self.monitoring:
            return
            
        self.monitoring = False
        logger.info(f"📸 Stopping screenshot monitoring for user {self.user_id}...")
        
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        # Take final screenshot 10 seconds after account checking completes
        if page and email:
            try:
                logger.info(f"📸 {email} - Waiting 10 seconds before final screenshot...")
                await asyncio.sleep(10)
                
                timestamp = int(time.time())
                safe_email = email.replace('@', '_at_').replace('.', '_')
                filename = f"final_screenshot_{timestamp}_{safe_email}_user_{self.user_id}"
                
                screenshot_bytes = await page.screenshot(full_page=True)
                
                # Upload to user-specific folder
                dropbox_path = await self._upload_to_user_folder(screenshot_bytes, filename)
                
                logger.info(f"📸 {email} - Final screenshot taken for user {self.user_id}: {dropbox_path}")
                
            except Exception as e:
                logger.error(f"📸 {email} - Error taking final screenshot: {e}")
                
    async def _monitor_loop(self, page: Page, email: str, process_name: str):
        """
        Main monitoring loop that takes screenshots every 10 seconds
        """
        start_time = time.time()
        
        try:
            while self.monitoring:
                try:
                    self.screenshot_count += 1
                    elapsed_seconds = int(time.time() - start_time)
                    
                    # Create descriptive filename with user ID
                    timestamp = int(time.time())
                    safe_email = email.replace('@', '_at_').replace('.', '_')
                    filename = f"{process_name}_{timestamp}_{safe_email}_monitor_{self.screenshot_count:03d}_{elapsed_seconds}s_user_{self.user_id}"
                    
                    # Take screenshot
                    screenshot_bytes = await page.screenshot(full_page=True)
                    
                    # Upload to user-specific folder
                    dropbox_path = await self._upload_to_user_folder(screenshot_bytes, filename)
                    
                    logger.info(f"📸 {email} - Monitor screenshot #{self.screenshot_count} ({elapsed_seconds}s) for user {self.user_id}: {dropbox_path}")
                    
                except Exception as e:
                    logger.error(f"📸 {email} - Error taking monitor screenshot #{self.screenshot_count}: {e}")
                
                # Wait 10 seconds before next screenshot (changed from 5 seconds)
                try:
                    await asyncio.sleep(10)
                except asyncio.CancelledError:
                    break
                    
        except asyncio.CancelledError:
            logger.info(f"📸 {email} - Screenshot monitoring cancelled after {self.screenshot_count} screenshots")
        except Exception as e:
            logger.error(f"📸 {email} - Screenshot monitoring error: {e}")
        finally:
            logger.info(f"📸 {email} - Screenshot monitoring stopped. Total screenshots: {self.screenshot_count}")
    
    async def _upload_to_user_folder(self, screenshot_bytes: bytes, filename: str) -> Optional[str]:
        """Upload screenshot to user-specific folder in Dropbox"""
        try:
            from datetime import datetime
            date_folder = datetime.now().strftime("%Y-%m-%d")
            
            # Create user-specific path: /screenshots/user_ID/date/filename
            dropbox_path = DropboxUploader.build_dropbox_path("screenshots", f"user_{self.user_id}", date_folder, f"{filename}.png")
            
            # Use the existing upload_screenshot method but with custom path
            return await self.dropbox_uploader.upload_screenshot_to_path(screenshot_bytes, dropbox_path)
            
        except Exception as e:
            logger.error(f"Error uploading to user folder: {e}")
            return None