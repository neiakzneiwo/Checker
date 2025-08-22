"""
Unified Captcha Solver API Server
Handles both Turnstile and hCaptcha challenges through a single API interface.
"""

import os
import sys
import time
import uuid
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from quart import Quart, request, jsonify
from camoufox.async_api import AsyncCamoufox

try:
    from patchright.async_api import async_playwright
    PATCHRIGHT_AVAILABLE = True
except ImportError:
    from playwright.async_api import async_playwright
    PATCHRIGHT_AVAILABLE = False

from turnstile_handler import TurnstileHandler
from hcaptcha_handler import HCaptchaHandler
from ai_models import AIModelManager
from browser_manager import BrowserManager
from vnc_integration import captcha_solver_vnc

COLORS = {
    'MAGENTA': '\033[35m',
    'BLUE': '\033[34m',
    'GREEN': '\033[32m',
    'YELLOW': '\033[33m',
    'RED': '\033[31m',
    'RESET': '\033[0m',
}

class CustomLogger(logging.Logger):
    @staticmethod
    def format_message(level, color, message):
        timestamp = time.strftime('%H:%M:%S')
        return f"[{timestamp}] [{COLORS.get(color)}{level}{COLORS.get('RESET')}] -> {message}"

    def debug(self, message, *args, **kwargs):
        super().debug(self.format_message('DEBUG', 'MAGENTA', message), *args, **kwargs)

    def info(self, message, *args, **kwargs):
        super().info(self.format_message('INFO', 'BLUE', message), *args, **kwargs)

    def success(self, message, *args, **kwargs):
        super().info(self.format_message('SUCCESS', 'GREEN', message), *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        super().warning(self.format_message('WARNING', 'YELLOW', message), *args, **kwargs)

    def error(self, message, *args, **kwargs):
        super().error(self.format_message('ERROR', 'RED', message), *args, **kwargs)

logging.setLoggerClass(CustomLogger)
logger = logging.getLogger("CaptchaSolverAPI")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)

class CaptchaSolverAPI:
    """Unified API server for handling both Turnstile and hCaptcha challenges"""
    
    def __init__(self, headless: bool = True, useragent: str = None, debug: bool = True, 
                 browser_type: str = "camoufox", thread: int = 2, proxy_support: bool = False):
        self.app = Quart(__name__)
        self.debug = debug
        self.results = self._load_results()
        self.browser_type = browser_type
        self.headless = headless
        self.useragent = useragent
        self.thread_count = thread
        self.proxy_support = proxy_support
        self.browser_pool = asyncio.Queue()
        self.browser_args = []
        
        if useragent:
            self.browser_args.append(f"--user-agent={useragent}")
        
        # Initialize advanced backend components
        self.browser_manager = BrowserManager(
            max_browsers=thread,
            browser_type=browser_type,
            headless=headless,
            debug=debug
        )
        self.ai_model_manager = AIModelManager()
        
        # Initialize handlers with advanced backend
        self.turnstile_handler = TurnstileHandler(self)
        self.hcaptcha_handler = HCaptchaHandler(self)
        
        self._setup_routes()

    @staticmethod
    def _load_results():
        """Load previous results from results.json."""
        try:
            if os.path.exists("captcha_results.json"):
                with open("captcha_results.json", "r") as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error loading results: {str(e)}. Starting with an empty results dictionary.")
        return {}

    def _save_results(self):
        """Save results to captcha_results.json."""
        try:
            with open("captcha_results.json", "w") as result_file:
                json.dump(self.results, result_file, indent=4)
        except IOError as e:
            logger.error(f"Error saving results to file: {str(e)}")

    def _setup_routes(self) -> None:
        """Set up the application routes."""
        self.app.before_serving(self._startup)
        
        # Turnstile endpoints
        self.app.route('/turnstile', methods=['GET'])(self.process_turnstile)
        self.app.route('/results', methods=['GET'])(self.get_turnstile_result)
        
        # hCaptcha endpoints  
        self.app.route('/hcaptcha', methods=['POST'])(self.process_hcaptcha)
        self.app.route('/resolved', methods=['GET'])(self.get_hcaptcha_result)
        
        # General endpoints
        self.app.route('/')(self.index)
        self.app.route('/health', methods=['GET'])(self.health_check)
        self.app.route('/status', methods=['GET'])(self.get_advanced_status)

    async def _startup(self) -> None:
        """Initialize the advanced backend components on startup."""
        logger.info("🚀 Starting Advanced Captcha Solver API initialization")
        try:
            # Initialize browser manager with advanced features
            await self.browser_manager.initialize()
            logger.success("✅ Advanced browser manager initialized")
            
            # Initialize AI models manager
            await self.ai_model_manager.initialize()
            logger.success("✅ AI models manager initialized")
            
            # Log VNC status
            if captcha_solver_vnc.is_vnc_enabled():
                logger.success("✅ VNC integration enabled for visual monitoring")
            else:
                logger.info("ℹ️ VNC integration disabled (set USE_VNC=true to enable)")
            
            logger.success("🎯 Advanced Captcha Solver API ready!")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Advanced Captcha Solver API: {str(e)}")
            raise

    async def get_browser_session(self):
        """Get a browser session from the advanced browser manager"""
        return await self.browser_manager.get_browser_session()
    
    async def return_browser_session(self, session):
        """Return a browser session to the advanced browser manager"""
        await self.browser_manager.return_browser_session(session)
    


    async def process_turnstile(self):
        """Handle the /turnstile endpoint requests."""
        url = request.args.get('url')
        sitekey = request.args.get('sitekey')
        action = request.args.get('action')
        cdata = request.args.get('cdata')
        pagedata = request.args.get('pagedata')

        logger.info(f"🔄 New Turnstile request received:")
        logger.info(f"   URL: {url}")
        logger.info(f"   Sitekey: {sitekey}")
        if action:
            logger.info(f"   Action: {action}")
        if cdata:
            logger.info(f"   CData: {cdata}")
        if pagedata:
            logger.info(f"   PageData: {pagedata[:50]}..." if len(pagedata) > 50 else f"   PageData: {pagedata}")

        if not url or not sitekey:
            logger.error("❌ Missing required parameters: url and sitekey are required")
            return jsonify({
                "status": "error",
                "error": "Both 'url' and 'sitekey' are required"
            }), 400

        task_id = str(uuid.uuid4())
        self.results[task_id] = {"status": "not_ready", "type": "turnstile"}

        logger.info(f"✅ Turnstile task created with ID: {task_id}")
        logger.info(f"🚀 Starting Turnstile solving task...")

        try:
            asyncio.create_task(self.turnstile_handler.solve_turnstile(
                task_id=task_id, url=url, sitekey=sitekey, 
                action=action, cdata=cdata, pagedata=pagedata
            ))
            
            logger.success(f"Turnstile task {task_id} queued successfully")
            return jsonify({"task_id": task_id}), 202
        except Exception as e:
            logger.error(f"❌ Unexpected error processing Turnstile request: {str(e)}")
            return jsonify({
                "status": "error",
                "error": str(e)
            }), 500

    async def process_hcaptcha(self):
        """Handle the /hcaptcha endpoint requests."""
        try:
            data = await request.get_json()
            
            if not data:
                return jsonify({
                    "status": "error",
                    "error": "JSON data required"
                }), 400
            
            images = data.get('images', [])
            instructions = data.get('instructions', '')
            rows = data.get('rows', 3)
            columns = data.get('columns', 3)
            
            logger.info(f"🔄 New hCaptcha request received:")
            logger.info(f"   Images count: {len(images)}")
            logger.info(f"   Instructions: {instructions}")
            logger.info(f"   Grid: {rows}x{columns}")
            
            if not images or not instructions:
                logger.error("❌ Missing required parameters: images and instructions are required")
                return jsonify({
                    "status": "error",
                    "error": "Both 'images' and 'instructions' are required"
                }), 400
            
            task_id = str(uuid.uuid4())
            self.results[task_id] = {"status": "not_ready", "type": "hcaptcha"}
            
            logger.info(f"✅ hCaptcha task created with ID: {task_id}")
            logger.info(f"🚀 Starting hCaptcha solving task...")
            
            asyncio.create_task(self.hcaptcha_handler.solve_hcaptcha(
                task_id=task_id, images=images, instructions=instructions,
                rows=rows, columns=columns
            ))
            
            logger.success(f"hCaptcha task {task_id} queued successfully")
            return jsonify({"task_id": task_id}), 202
            
        except Exception as e:
            logger.error(f"❌ Unexpected error processing hCaptcha request: {str(e)}")
            return jsonify({
                "status": "error",
                "error": str(e)
            }), 500

    async def get_turnstile_result(self):
        """Return Turnstile solved data via /results endpoint"""
        task_id = request.args.get('id')
        
        logger.info(f"📋 Turnstile result request for task: {task_id}")
        
        if not task_id or task_id not in self.results:
            logger.error(f"❌ Invalid task ID: {task_id}")
            return jsonify({"status": "error", "error": "Invalid task ID"}), 400
        
        result = self.results[task_id]
        
        if isinstance(result, dict):
            status = result.get("status", "error")
            if status == "not_ready":
                logger.info(f"⏳ Turnstile task {task_id}: Still processing...")
                return jsonify({"status": "not_ready"}), 202
            elif status == "error":
                logger.warning(f"❌ Turnstile task {task_id}: Failed")
                return jsonify({"status": "error", "error": result.get("error", "Unknown error")}), 500
            elif status == "ready":
                logger.success(f"✅ Turnstile task {task_id}: Solved in {result.get('elapsed_time', 'unknown')}s")
                return jsonify({
                    "status": "ready",
                    "solution": result.get("value"),
                    "elapsed_time": result.get("elapsed_time")
                }), 200
        
        return jsonify({"status": "error", "error": "Invalid result format"}), 500

    async def get_hcaptcha_result(self):
        """Return hCaptcha solved data via /resolved endpoint"""
        task_id = request.args.get('id')
        
        logger.info(f"📋 hCaptcha result request for task: {task_id}")
        
        if not task_id or task_id not in self.results:
            logger.error(f"❌ Invalid task ID: {task_id}")
            return jsonify({"status": "error", "error": "Invalid task ID"}), 400
        
        result = self.results[task_id]
        
        if isinstance(result, dict):
            status = result.get("status", "error")
            if status == "not_ready":
                logger.info(f"⏳ hCaptcha task {task_id}: Still processing...")
                return jsonify({"status": "not_ready"}), 202
            elif status == "error":
                logger.warning(f"❌ hCaptcha task {task_id}: Failed")
                return jsonify({"status": "error", "error": result.get("error", "Unknown error")}), 500
            elif status == "ready":
                logger.success(f"✅ hCaptcha task {task_id}: Solved")
                return jsonify({
                    "status": "ready",
                    "solution": result.get("tiles", "No_matching_images")
                }), 200
        
        return jsonify({"status": "error", "error": "Invalid result format"}), 500

    async def health_check(self):
        """Health check endpoint"""
        return jsonify({
            "status": "healthy",
            "version": "1.0.0",
            "browser_pool_size": self.browser_pool.qsize(),
            "active_tasks": len([r for r in self.results.values() if isinstance(r, dict) and r.get("status") == "not_ready"])
        }), 200

    @staticmethod
    async def index():
        """Serve the API documentation page."""
        return """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Captcha Solver API</title>
                <script src="https://cdn.tailwindcss.com"></script>
            </head>
            <body class="bg-gray-900 text-gray-200 min-h-screen flex items-center justify-center">
                <div class="bg-gray-800 p-8 rounded-lg shadow-md max-w-4xl w-full border border-blue-500">
                    <h1 class="text-3xl font-bold mb-6 text-center text-blue-500">Captcha Solver API</h1>
                    
                    <div class="grid md:grid-cols-2 gap-6">
                        <!-- Turnstile Section -->
                        <div class="bg-gray-700 p-6 rounded-lg border border-green-500">
                            <h2 class="text-xl font-bold mb-4 text-green-400">Turnstile Solver</h2>
                            <p class="mb-4 text-gray-300">Send GET request to <code class="bg-green-700 text-white px-2 py-1 rounded">/turnstile</code></p>
                            <ul class="list-disc pl-6 mb-4 text-gray-300 text-sm">
                                <li><strong>url</strong>: Target URL</li>
                                <li><strong>sitekey</strong>: Turnstile site key</li>
                                <li><strong>action</strong> (optional): Action parameter</li>
                                <li><strong>cdata</strong> (optional): CData parameter</li>
                                <li><strong>pagedata</strong> (optional): Page data parameter</li>
                            </ul>
                            <p class="text-sm text-gray-400">Check results at <code>/results?id=TASK_ID</code></p>
                        </div>
                        
                        <!-- hCaptcha Section -->
                        <div class="bg-gray-700 p-6 rounded-lg border border-purple-500">
                            <h2 class="text-xl font-bold mb-4 text-purple-400">hCaptcha Solver</h2>
                            <p class="mb-4 text-gray-300">Send POST request to <code class="bg-purple-700 text-white px-2 py-1 rounded">/hcaptcha</code></p>
                            <ul class="list-disc pl-6 mb-4 text-gray-300 text-sm">
                                <li><strong>images</strong>: Array of Base64 images</li>
                                <li><strong>instructions</strong>: Challenge instructions</li>
                                <li><strong>rows</strong>: Grid rows (default: 3)</li>
                                <li><strong>columns</strong>: Grid columns (default: 3)</li>
                            </ul>
                            <p class="text-sm text-gray-400">Check results at <code>/resolved?id=TASK_ID</code></p>
                        </div>
                    </div>
                    
                    <div class="mt-6 bg-blue-900 border-l-4 border-blue-600 p-4">
                        <p class="text-blue-200 font-semibold">Custom Captcha Solver v1.0.0</p>
                        <p class="text-blue-300 text-sm">Unified API for Turnstile and hCaptcha challenges</p>
                    </div>
                </div>
            </body>
            </html>
        """
    
    async def get_advanced_status(self):
        """Get comprehensive status of the advanced captcha solver system"""
        try:
            # Browser manager status
            browser_status = self.browser_manager.get_status()
            
            # AI models status
            ai_models_status = self.ai_model_manager.get_performance_stats()
            available_models = [model.value for model in self.ai_model_manager.get_available_models()]
            
            # VNC status
            vnc_status = {
                'enabled': captcha_solver_vnc.is_vnc_enabled(),
                'active_sessions': captcha_solver_vnc.get_active_sessions() if captcha_solver_vnc.is_vnc_enabled() else {}
            }
            
            # Task results status
            task_stats = {
                'total_tasks': len(self.results),
                'completed_tasks': len([r for r in self.results.values() if r.get('status') == 'ready']),
                'failed_tasks': len([r for r in self.results.values() if r.get('status') == 'error']),
                'pending_tasks': len([r for r in self.results.values() if r.get('status') == 'not_ready'])
            }
            
            status = {
                'system': {
                    'status': 'operational',
                    'version': '2.0.0-advanced',
                    'uptime': time.time() - getattr(self, '_start_time', time.time()),
                    'debug_mode': self.debug
                },
                'browser_manager': browser_status,
                'ai_models': {
                    'available_models': available_models,
                    'performance_stats': ai_models_status,
                    'total_models': len(available_models)
                },
                'vnc_integration': vnc_status,
                'task_statistics': task_stats,
                'features': {
                    'turnstile_solving': True,
                    'hcaptcha_solving': True,
                    'ai_powered_recognition': len(available_models) > 0,
                    'visual_monitoring': vnc_status['enabled'],
                    'anti_detection': True,
                    'concurrent_solving': browser_status['pool_status']['total_browsers'] > 1
                }
            }
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Error getting advanced status: {e}")
            return {
                'system': {
                    'status': 'error',
                    'error': str(e)
                }
            }, 500

def create_app(headless: bool = True, useragent: str = None, debug: bool = True, 
               browser_type: str = "camoufox", thread: int = 2, proxy_support: bool = False) -> Quart:
    """Create and configure the Captcha Solver API application"""
    server = CaptchaSolverAPI(
        headless=headless, 
        useragent=useragent, 
        debug=debug, 
        browser_type=browser_type, 
        thread=thread, 
        proxy_support=proxy_support
    )
    return server.app