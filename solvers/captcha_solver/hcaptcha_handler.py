#!/usr/bin/env python3
"""
hCaptcha Handler for Captcha Solver
Handles hCaptcha grid-based image selection challenges using AI models
"""

import time
import asyncio
import logging
import base64
import io
from typing import List, Dict, Any, Optional
from PIL import Image

logger = logging.getLogger("HCaptchaHandler")

class HCaptchaHandler:
    """Handles hCaptcha image selection challenges"""
    
    def __init__(self, api_server):
        self.api_server = api_server
        self.logger = logger
    
    async def solve_hcaptcha(self, task_id: str, images: List[str], instructions: str,
                            rows: int = 3, columns: int = 3) -> None:
        """
        Solve hCaptcha grid-based image selection challenge
        
        Args:
            task_id: Unique task identifier
            images: List of base64 encoded images
            instructions: Challenge instructions (e.g., "Click all the objects that fit inside the sample item")
            rows: Number of grid rows
            columns: Number of grid columns
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"🔄 Starting hCaptcha solving for task {task_id}")
            self.logger.info(f"📋 Instructions: {instructions}")
            self.logger.info(f"🖼️ Images: {len(images)}, Grid: {rows}x{columns}")
            
            # Validate input
            if not images or not instructions:
                raise ValueError("Images and instructions are required")
            
            expected_images = rows * columns
            if len(images) != expected_images:
                self.logger.warning(f"⚠️ Expected {expected_images} images for {rows}x{columns} grid, got {len(images)}")
            
            # Process and validate images
            processed_images = []
            for i, img_data in enumerate(images):
                try:
                    # Validate and process image
                    processed_img = self._process_image(img_data, i + 1)
                    if processed_img:
                        processed_images.append(processed_img)
                    else:
                        self.logger.warning(f"⚠️ Failed to process image {i + 1}")
                except Exception as e:
                    self.logger.error(f"❌ Error processing image {i + 1}: {e}")
                    continue
            
            if not processed_images:
                raise ValueError("No valid images to process")
            
            self.logger.info(f"✅ Processed {len(processed_images)} valid images")
            
            # Analyze images using AI models
            success, selected_tiles = await self.api_server.ai_model_manager.analyze_images(
                processed_images, instructions
            )
            
            if success:
                elapsed_time = time.time() - start_time
                
                if selected_tiles:
                    self.logger.success(f"✅ hCaptcha solved successfully in {elapsed_time:.2f}s")
                    self.logger.info(f"🎯 Selected tiles: {selected_tiles}")
                    
                    # Store successful result
                    self.api_server.results[task_id] = {
                        "status": "ready",
                        "tiles": selected_tiles,
                        "elapsed_time": elapsed_time
                    }
                else:
                    self.logger.info(f"✅ hCaptcha analyzed - no matching images found in {elapsed_time:.2f}s")
                    
                    # Store "no matching images" result
                    self.api_server.results[task_id] = {
                        "status": "ready",
                        "tiles": "No_matching_images",
                        "elapsed_time": elapsed_time
                    }
                
                self.api_server._save_results()
                
            else:
                # AI analysis failed
                self.logger.error("❌ AI model analysis failed")
                self.api_server.results[task_id] = {
                    "status": "error",
                    "error": "AI model analysis failed"
                }
                self.api_server._save_results()
                
        except Exception as e:
            self.logger.error(f"❌ hCaptcha solving failed for task {task_id}: {str(e)}")
            self.api_server.results[task_id] = {
                "status": "error",
                "error": str(e)
            }
            self.api_server._save_results()
    
    def _process_image(self, img_data: str, image_num: int) -> Optional[str]:
        """
        Process and validate image data
        
        Args:
            img_data: Base64 encoded image data
            image_num: Image number for logging
            
        Returns:
            Processed base64 image data or None if invalid
        """
        try:
            # Handle data URL format
            if img_data.startswith('data:'):
                # Extract base64 data after comma
                if ',' in img_data:
                    img_data = img_data.split(',', 1)[1]
                else:
                    self.logger.warning(f"⚠️ Invalid data URL format for image {image_num}")
                    return None
            
            # Decode base64 to validate
            try:
                img_bytes = base64.b64decode(img_data)
            except Exception as e:
                self.logger.error(f"❌ Invalid base64 data for image {image_num}: {e}")
                return None
            
            # Validate image size (max 600KB as per 2Captcha specs)
            if len(img_bytes) > 600 * 1024:
                self.logger.warning(f"⚠️ Image {image_num} too large: {len(img_bytes)} bytes")
                # Try to compress the image
                img_data = self._compress_image(img_bytes)
                if not img_data:
                    return None
            
            # Validate image format using PIL
            try:
                img = Image.open(io.BytesIO(img_bytes))
                
                # Check image dimensions (max 1000px on any side)
                width, height = img.size
                if width > 1000 or height > 1000:
                    self.logger.warning(f"⚠️ Image {image_num} too large: {width}x{height}")
                    # Resize image
                    img_data = self._resize_image(img, max_size=1000)
                    if not img_data:
                        return None
                
                # Ensure image is in supported format (JPEG, PNG, GIF)
                if img.format not in ['JPEG', 'PNG', 'GIF']:
                    self.logger.info(f"🔄 Converting image {image_num} from {img.format} to JPEG")
                    img_data = self._convert_to_jpeg(img)
                    if not img_data:
                        return None
                
                self.logger.debug(f"✅ Image {image_num} validated: {img.format} {width}x{height}")
                return img_data
                
            except Exception as e:
                self.logger.error(f"❌ Invalid image format for image {image_num}: {e}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error processing image {image_num}: {e}")
            return None
    
    def _compress_image(self, img_bytes: bytes, max_size: int = 600 * 1024) -> Optional[str]:
        """Compress image to reduce file size"""
        try:
            img = Image.open(io.BytesIO(img_bytes))
            
            # Try different quality levels
            for quality in [85, 70, 55, 40]:
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=quality, optimize=True)
                compressed_bytes = output.getvalue()
                
                if len(compressed_bytes) <= max_size:
                    self.logger.info(f"🗜️ Compressed image to {len(compressed_bytes)} bytes (quality: {quality})")
                    return base64.b64encode(compressed_bytes).decode('utf-8')
            
            self.logger.warning("⚠️ Could not compress image to acceptable size")
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error compressing image: {e}")
            return None
    
    def _resize_image(self, img: Image.Image, max_size: int = 1000) -> Optional[str]:
        """Resize image to fit within max dimensions"""
        try:
            width, height = img.size
            
            # Calculate new dimensions maintaining aspect ratio
            if width > height:
                new_width = max_size
                new_height = int((height * max_size) / width)
            else:
                new_height = max_size
                new_width = int((width * max_size) / height)
            
            # Resize image
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Save as JPEG
            output = io.BytesIO()
            resized_img.save(output, format='JPEG', quality=85, optimize=True)
            resized_bytes = output.getvalue()
            
            self.logger.info(f"📏 Resized image from {width}x{height} to {new_width}x{new_height}")
            return base64.b64encode(resized_bytes).decode('utf-8')
            
        except Exception as e:
            self.logger.error(f"❌ Error resizing image: {e}")
            return None
    
    def _convert_to_jpeg(self, img: Image.Image) -> Optional[str]:
        """Convert image to JPEG format"""
        try:
            # Convert to RGB if necessary (for PNG with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save as JPEG
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            jpeg_bytes = output.getvalue()
            
            return base64.b64encode(jpeg_bytes).decode('utf-8')
            
        except Exception as e:
            self.logger.error(f"❌ Error converting image to JPEG: {e}")
            return None