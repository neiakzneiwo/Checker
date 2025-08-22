#!/usr/bin/env python3
"""
Captcha Solver Startup Script
Starts the unified captcha solver API server
"""

import os
import sys
import asyncio
import argparse
from hypercorn.config import Config
from hypercorn.asyncio import serve

# Add the solver directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_server import CaptchaSolverAPI

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Start Captcha Solver API Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--headless', action='store_true', help='Run browsers in headless mode')
    parser.add_argument('--browser', default='camoufox', choices=['camoufox', 'chromium', 'chrome', 'msedge'], 
                       help='Browser type to use')
    parser.add_argument('--threads', type=int, default=2, help='Number of browser threads')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--useragent', help='Custom user agent string')
    parser.add_argument('--proxy-support', action='store_true', help='Enable proxy support')
    
    args = parser.parse_args()
    
    print(f"""
🚀 Starting Captcha Solver API Server
=====================================
Host: {args.host}
Port: {args.port}
Browser: {args.browser}
Headless: {args.headless}
Threads: {args.threads}
Debug: {args.debug}
Proxy Support: {args.proxy_support}
=====================================
    """)
    
    # Create API server instance
    api_server = CaptchaSolverAPI(
        headless=args.headless,
        useragent=args.useragent,
        debug=args.debug,
        browser_type=args.browser,
        thread=args.threads,
        proxy_support=args.proxy_support
    )
    
    # Configure Hypercorn
    config = Config()
    config.bind = [f"{args.host}:{args.port}"]
    config.use_reloader = args.debug
    config.accesslog = "-" if args.debug else None
    config.errorlog = "-"
    
    print(f"🌐 API Server will be available at: http://{args.host}:{args.port}")
    print(f"📚 API Documentation: http://{args.host}:{args.port}/")
    print(f"🔄 Health Check: http://{args.host}:{args.port}/health")
    print()
    print("Endpoints:")
    print(f"  • Turnstile: GET  http://{args.host}:{args.port}/turnstile")
    print(f"  • Results:   GET  http://{args.host}:{args.port}/results?id=TASK_ID")
    print(f"  • hCaptcha:  POST http://{args.host}:{args.port}/hcaptcha")
    print(f"  • Resolved:  GET  http://{args.host}:{args.port}/resolved?id=TASK_ID")
    print()
    print("🔑 Environment Variables (optional):")
    print("  • GEMINI_API_KEY - For Gemini AI model")
    print("  • TOGETHER_API_KEY - For Together AI model")
    print("  • OPENAI_API_KEY - For OpenAI model")
    print()
    print("Starting server...")
    
    try:
        # Run the server
        asyncio.run(serve(api_server.app, config))
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()