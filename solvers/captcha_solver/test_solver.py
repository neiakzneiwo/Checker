#!/usr/bin/env python3
"""
Test Script for Captcha Solver
Tests both Turnstile and hCaptcha solving capabilities
"""

import asyncio
import aiohttp
import json
import base64
import time
from typing import Dict, Any

class CaptchaSolverTester:
    """Test client for the captcha solver API"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_health(self) -> bool:
        """Test the health endpoint"""
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Health check passed: {data}")
                    return True
                else:
                    print(f"❌ Health check failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    async def test_turnstile(self) -> bool:
        """Test Turnstile solving"""
        print("\n🔄 Testing Turnstile solver...")
        
        try:
            # Submit Turnstile task
            params = {
                'url': 'https://demo.turnstile.workers.dev/',
                'sitekey': '0x4AAAAAAADnPIDROlWd_wc'  # Demo sitekey
            }
            
            async with self.session.get(f"{self.base_url}/turnstile", params=params) as response:
                if response.status == 202:
                    data = await response.json()
                    task_id = data.get('task_id')
                    print(f"✅ Turnstile task submitted: {task_id}")
                    
                    # Poll for results
                    return await self._poll_turnstile_results(task_id)
                else:
                    error_data = await response.text()
                    print(f"❌ Turnstile submission failed: {response.status} - {error_data}")
                    return False
                    
        except Exception as e:
            print(f"❌ Turnstile test error: {e}")
            return False
    
    async def _poll_turnstile_results(self, task_id: str, max_attempts: int = 30) -> bool:
        """Poll for Turnstile results"""
        for attempt in range(max_attempts):
            try:
                await asyncio.sleep(2)  # Wait 2 seconds between polls
                
                async with self.session.get(f"{self.base_url}/results", params={'id': task_id}) as response:
                    data = await response.json()
                    status = data.get('status')
                    
                    if status == 'ready':
                        solution = data.get('solution')
                        elapsed_time = data.get('elapsed_time')
                        print(f"✅ Turnstile solved in {elapsed_time:.2f}s")
                        print(f"🎯 Solution: {solution[:50]}..." if solution else "No solution")
                        return True
                    elif status == 'error':
                        error = data.get('error')
                        print(f"❌ Turnstile solving failed: {error}")
                        return False
                    elif status == 'not_ready':
                        print(f"⏳ Attempt {attempt + 1}/{max_attempts}: Still processing...")
                        continue
                    else:
                        print(f"❓ Unknown status: {status}")
                        
            except Exception as e:
                print(f"❌ Error polling results: {e}")
                
        print(f"⏰ Turnstile solving timed out after {max_attempts} attempts")
        return False
    
    async def test_hcaptcha(self) -> bool:
        """Test hCaptcha solving with sample data"""
        print("\n🔄 Testing hCaptcha solver...")
        
        try:
            # Create sample images (blank squares for testing)
            sample_images = []
            for i in range(9):  # 3x3 grid
                # Create a simple test image (100x100 white square)
                from PIL import Image
                import io
                
                img = Image.new('RGB', (100, 100), color='white')
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG')
                img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                sample_images.append(img_b64)
            
            # Submit hCaptcha task
            payload = {
                'images': sample_images,
                'instructions': 'Click all the objects that fit inside the sample item',
                'rows': 3,
                'columns': 3
            }
            
            async with self.session.post(f"{self.base_url}/hcaptcha", json=payload) as response:
                if response.status == 202:
                    data = await response.json()
                    task_id = data.get('task_id')
                    print(f"✅ hCaptcha task submitted: {task_id}")
                    
                    # Poll for results
                    return await self._poll_hcaptcha_results(task_id)
                else:
                    error_data = await response.text()
                    print(f"❌ hCaptcha submission failed: {response.status} - {error_data}")
                    return False
                    
        except Exception as e:
            print(f"❌ hCaptcha test error: {e}")
            return False
    
    async def _poll_hcaptcha_results(self, task_id: str, max_attempts: int = 15) -> bool:
        """Poll for hCaptcha results"""
        for attempt in range(max_attempts):
            try:
                await asyncio.sleep(2)  # Wait 2 seconds between polls
                
                async with self.session.get(f"{self.base_url}/resolved", params={'id': task_id}) as response:
                    data = await response.json()
                    status = data.get('status')
                    
                    if status == 'ready':
                        solution = data.get('solution')
                        print(f"✅ hCaptcha solved!")
                        print(f"🎯 Solution: {solution}")
                        return True
                    elif status == 'error':
                        error = data.get('error')
                        print(f"❌ hCaptcha solving failed: {error}")
                        return False
                    elif status == 'not_ready':
                        print(f"⏳ Attempt {attempt + 1}/{max_attempts}: Still processing...")
                        continue
                    else:
                        print(f"❓ Unknown status: {status}")
                        
            except Exception as e:
                print(f"❌ Error polling results: {e}")
                
        print(f"⏰ hCaptcha solving timed out after {max_attempts} attempts")
        return False
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests"""
        print("🧪 Starting Captcha Solver Tests")
        print("=" * 50)
        
        results = {}
        
        # Test health
        results['health'] = await self.test_health()
        
        # Test Turnstile (only if health passes)
        if results['health']:
            results['turnstile'] = await self.test_turnstile()
        else:
            results['turnstile'] = False
            print("⏭️ Skipping Turnstile test due to health check failure")
        
        # Test hCaptcha (only if health passes)
        if results['health']:
            results['hcaptcha'] = await self.test_hcaptcha()
        else:
            results['hcaptcha'] = False
            print("⏭️ Skipping hCaptcha test due to health check failure")
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 Test Results Summary:")
        for test_name, passed in results.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"  {test_name.capitalize()}: {status}")
        
        total_tests = len(results)
        passed_tests = sum(results.values())
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        return results

async def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Captcha Solver API')
    parser.add_argument('--url', default='http://localhost:5000', help='API server URL')
    parser.add_argument('--test', choices=['health', 'turnstile', 'hcaptcha', 'all'], 
                       default='all', help='Which test to run')
    
    args = parser.parse_args()
    
    async with CaptchaSolverTester(args.url) as tester:
        if args.test == 'health':
            await tester.test_health()
        elif args.test == 'turnstile':
            await tester.test_turnstile()
        elif args.test == 'hcaptcha':
            await tester.test_hcaptcha()
        else:
            await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())