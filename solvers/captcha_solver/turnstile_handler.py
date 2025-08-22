#!/usr/bin/env python3
"""
Turnstile Handler for Captcha Solver
Handles Cloudflare Turnstile challenges
"""

import time
import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("TurnstileHandler")

class TurnstileHandler:
    """Handles Turnstile captcha solving"""
    
    def __init__(self, api_server):
        self.api_server = api_server
        self.logger = logger
    
    async def solve_turnstile(self, task_id: str, url: str, sitekey: str, 
                             action: Optional[str] = None, cdata: Optional[str] = None, 
                             pagedata: Optional[str] = None) -> None:
        """
        Solve Turnstile captcha challenge
        
        Args:
            task_id: Unique task identifier
            url: Target URL
            sitekey: Turnstile site key
            action: Optional action parameter
            cdata: Optional cdata parameter
            pagedata: Optional pagedata parameter
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"🔄 Starting Turnstile solving for task {task_id}")
            
            # Get browser session from pool
            session = await self.api_server.get_browser_session()
            if not session:
                raise Exception("No browser session available")
            
            try:
                # Extract page from session
                page = session['page']
                
                # Navigate to target URL
                self.logger.info(f"🌐 Navigating to: {url}")
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                
                # Wait for Turnstile widget to load
                await asyncio.sleep(2)
                
                # Look for Turnstile iframe
                turnstile_iframe = None
                try:
                    # Try to find Turnstile iframe
                    iframes = await page.query_selector_all('iframe')
                    for iframe in iframes:
                        src = await iframe.get_attribute('src')
                        if src and 'challenges.cloudflare.com' in src:
                            turnstile_iframe = iframe
                            break
                    
                    if not turnstile_iframe:
                        # Look for Turnstile div container
                        turnstile_div = await page.query_selector('[data-sitekey]')
                        if turnstile_div:
                            self.logger.info("📍 Found Turnstile container, waiting for challenge...")
                            await asyncio.sleep(3)
                            
                            # Re-check for iframe after waiting
                            iframes = await page.query_selector_all('iframe')
                            for iframe in iframes:
                                src = await iframe.get_attribute('src')
                                if src and 'challenges.cloudflare.com' in src:
                                    turnstile_iframe = iframe
                                    break
                    
                    if turnstile_iframe:
                        self.logger.info("✅ Found Turnstile iframe, attempting to solve...")
                        
                        # Switch to iframe context
                        iframe_content = await turnstile_iframe.content_frame()
                        if iframe_content:
                            # Look for checkbox or challenge elements
                            checkbox = await iframe_content.query_selector('input[type="checkbox"]')
                            if checkbox:
                                self.logger.info("🎯 Clicking Turnstile checkbox...")
                                await checkbox.click()
                                await asyncio.sleep(2)
                            
                            # Wait for potential challenge completion
                            await asyncio.sleep(5)
                            
                            # Check if challenge is completed by looking for success indicators
                            success_indicators = [
                                'input[name="cf-turnstile-response"]',
                                '[data-cf-turnstile-response]',
                                '.cf-turnstile-success'
                            ]
                            
                            turnstile_response = None
                            for selector in success_indicators:
                                try:
                                    element = await page.query_selector(selector)
                                    if element:
                                        value = await element.get_attribute('value') or await element.inner_text()
                                        if value and len(value) > 10:  # Valid response should be longer
                                            turnstile_response = value
                                            break
                                except:
                                    continue
                            
                            if turnstile_response:
                                elapsed_time = time.time() - start_time
                                self.logger.success(f"✅ Turnstile solved successfully in {elapsed_time:.2f}s")
                                
                                # Store successful result
                                self.api_server.results[task_id] = {
                                    "status": "ready",
                                    "value": turnstile_response,
                                    "elapsed_time": elapsed_time
                                }
                                self.api_server._save_results()
                                return
                    
                    # If we get here, solving failed
                    self.logger.warning("⚠️ Could not solve Turnstile challenge automatically")
                    
                    # Store error result
                    self.api_server.results[task_id] = {
                        "status": "error",
                        "error": "Could not solve Turnstile challenge automatically"
                    }
                    
                except Exception as iframe_error:
                    self.logger.error(f"❌ Error processing Turnstile iframe: {iframe_error}")
                    self.api_server.results[task_id] = {
                        "status": "error",
                        "error": f"Iframe processing error: {str(iframe_error)}"
                    }
                
                finally:
                    # Page cleanup is handled by session cleanup
                    pass
                    
            finally:
                # Return browser session to pool
                await self.api_server.return_browser_session(session)
                
        except Exception as e:
            self.logger.error(f"❌ Turnstile solving failed for task {task_id}: {str(e)}")
            self.api_server.results[task_id] = {
                "status": "error",
                "error": str(e)
            }
            self.api_server._save_results()