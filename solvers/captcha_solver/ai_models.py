#!/usr/bin/env python3
"""
Advanced AI Models Manager for hCaptcha Solving
Professional-grade backend core inspired by hcaptcha-challenger
Integrates with multiple AI models for superior image recognition
"""

import os
import base64
import asyncio
import logging
import json
import re
import io
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union, Literal
from dataclasses import dataclass
from enum import Enum
import aiohttp
from PIL import Image
import time

logger = logging.getLogger("AIModelManager")

class ChallengeType(str, Enum):
    """Challenge types for hCaptcha"""
    IMAGE_LABEL_BINARY = "image_label_binary"
    IMAGE_LABEL_SINGLE_SELECT = "image_label_single_select"
    IMAGE_LABEL_MULTI_SELECT = "image_label_multi_select"
    IMAGE_DRAG_SINGLE = "image_drag_single"
    IMAGE_DRAG_MULTI = "image_drag_multi"

class ModelType(str, Enum):
    """Supported AI model types"""
    GEMINI_1_5_FLASH = "gemini-1.5-flash"
    GEMINI_1_5_PRO = "gemini-1.5-pro"
    GEMINI_2_0_FLASH = "gemini-2.0-flash-exp"
    TOGETHER_LLAMA_VISION = "meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo"
    OPENAI_GPT4O_MINI = "gpt-4o-mini"
    OPENAI_GPT4O = "gpt-4o"

@dataclass
class ImageBinaryChallenge:
    """Response model for binary image challenges"""
    challenge_prompt: str
    coordinates: List[Dict[str, List[int]]]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImageBinaryChallenge':
        return cls(
            challenge_prompt=data.get('challenge_prompt', ''),
            coordinates=data.get('coordinates', [])
        )

@dataclass
class ModelConfig:
    """Configuration for AI models"""
    name: str
    endpoint: str
    model_id: str
    max_images: int
    max_tokens: int
    temperature: float
    thinking_budget: Optional[int] = None
    supports_structured_output: bool = False
    supports_thinking: bool = False

class AdvancedPromptEngine:
    """Advanced prompt engineering for hCaptcha challenges"""
    
    SYSTEM_INSTRUCTIONS = {
        ChallengeType.IMAGE_LABEL_BINARY: """
You are an expert hCaptcha solver specializing in grid-based image selection challenges.

TASK: Analyze the provided grid of images and identify which tiles match the given instruction.

GRID SYSTEM:
- Images are arranged in a grid (typically 3x3 = 9 images)
- Use coordinate system [row, col] where [0,0] is top-left
- For 3x3 grid: [0,0] [0,1] [0,2]
                 [1,0] [1,1] [1,2]  
                 [2,0] [2,1] [2,2]

OUTPUT FORMAT:
Return a JSON object with this exact structure:
```json
{
  "challenge_prompt": "the instruction text",
  "coordinates": [
    {"box_2d": [row, col]},
    {"box_2d": [row, col]}
  ]
}
```

ANALYSIS APPROACH:
1. Carefully examine each image in the grid
2. Understand the instruction context and requirements
3. Apply strict matching criteria - only select images that clearly match
4. Consider edge cases and ambiguous images carefully
5. If no images match, return empty coordinates array

QUALITY STANDARDS:
- Precision over recall - better to miss a match than include a false positive
- Consider lighting, angles, partial objects, and image quality
- Account for common hCaptcha tricks and edge cases
""",
        
        ChallengeType.IMAGE_LABEL_MULTI_SELECT: """
You are an expert hCaptcha solver for multi-selection image challenges.

TASK: Identify ALL images that match the given criteria from the provided grid.

GRID SYSTEM: Same coordinate system as binary challenges.

SPECIAL CONSIDERATIONS:
- This is a multi-select challenge - multiple correct answers expected
- Be thorough but maintain accuracy standards
- Consider variations and edge cases of the target object/concept

OUTPUT: Same JSON format as binary challenges.
""",
        
        ChallengeType.IMAGE_LABEL_SINGLE_SELECT: """
You are an expert hCaptcha solver for single-selection challenges.

TASK: Identify the ONE image that best matches the given criteria.

SPECIAL CONSIDERATIONS:
- Only one correct answer expected
- Choose the most obvious/clear match if multiple candidates exist
- Consider the specific wording of the instruction

OUTPUT: Same JSON format with single coordinate.
"""
    }
    
    USER_PROMPTS = {
        "grid_analysis": """
Analyze this grid of images and solve the challenge.

Grid dimensions: {rows}x{columns} ({total_images} total images)
Challenge instruction: "{instruction}"

Apply the coordinate system and return the solution in the specified JSON format.
""",
        
        "context_enhanced": """
Challenge Context: {instruction}

Additional Context:
- Image quality: Analyze for clarity, lighting, and visibility
- Object detection: Look for complete vs partial objects
- Contextual clues: Consider background, setting, and related objects
- Edge cases: Account for reflections, shadows, and unusual angles

Provide your analysis and solution.
""",
        
        "verification": """
Before finalizing your answer, verify:
1. Each selected coordinate corresponds to an image that clearly matches the instruction
2. No obvious matches were missed
3. No false positives were included
4. The coordinate format is correct [row, col] starting from [0,0]

Final answer:
"""
    }

class AIModelManager:
    """Advanced AI Models Manager with professional-grade backend core"""
    
    def __init__(self):
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.together_api_key = os.getenv('TOGETHER_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        # Advanced model configurations
        self.models = {
            ModelType.GEMINI_1_5_FLASH: ModelConfig(
                name="Gemini 1.5 Flash",
                endpoint="https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
                model_id="gemini-1.5-flash",
                max_images=16,
                max_tokens=8192,
                temperature=0.1,
                supports_structured_output=True,
                supports_thinking=False
            ),
            ModelType.GEMINI_1_5_PRO: ModelConfig(
                name="Gemini 1.5 Pro",
                endpoint="https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent",
                model_id="gemini-1.5-pro",
                max_images=16,
                max_tokens=8192,
                temperature=0.1,
                thinking_budget=1024,
                supports_structured_output=True,
                supports_thinking=True
            ),
            ModelType.GEMINI_2_0_FLASH: ModelConfig(
                name="Gemini 2.0 Flash",
                endpoint="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent",
                model_id="gemini-2.0-flash-exp",
                max_images=16,
                max_tokens=8192,
                temperature=0.1,
                thinking_budget=2048,
                supports_structured_output=True,
                supports_thinking=True
            ),
            ModelType.TOGETHER_LLAMA_VISION: ModelConfig(
                name="Llama 3.2 Vision",
                endpoint="https://api.together.xyz/v1/chat/completions",
                model_id="meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo",
                max_images=8,
                max_tokens=4096,
                temperature=0.1,
                supports_structured_output=False,
                supports_thinking=False
            ),
            ModelType.OPENAI_GPT4O_MINI: ModelConfig(
                name="GPT-4o Mini",
                endpoint="https://api.openai.com/v1/chat/completions",
                model_id="gpt-4o-mini",
                max_images=10,
                max_tokens=4096,
                temperature=0.1,
                supports_structured_output=True,
                supports_thinking=False
            ),
            ModelType.OPENAI_GPT4O: ModelConfig(
                name="GPT-4o",
                endpoint="https://api.openai.com/v1/chat/completions",
                model_id="gpt-4o",
                max_images=10,
                max_tokens=4096,
                temperature=0.1,
                supports_structured_output=True,
                supports_thinking=False
            )
        }
        
        self.prompt_engine = AdvancedPromptEngine()
        self.session = None
        self.cache = {}
        self.performance_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_response_time': 0.0,
            'model_usage': {}
        }
        
    async def initialize(self):
        """Initialize the AI model manager with advanced setup"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=120),
            connector=aiohttp.TCPConnector(limit=10, limit_per_host=5)
        )
        
        # Check available models
        available_models = []
        if self.gemini_api_key:
            available_models.extend([ModelType.GEMINI_1_5_FLASH, ModelType.GEMINI_1_5_PRO, ModelType.GEMINI_2_0_FLASH])
        if self.together_api_key:
            available_models.append(ModelType.TOGETHER_LLAMA_VISION)
        if self.openai_api_key:
            available_models.extend([ModelType.OPENAI_GPT4O_MINI, ModelType.OPENAI_GPT4O])
        
        if available_models:
            model_names = [self.models[model].name for model in available_models]
            logger.info(f"✅ AI Models available: {', '.join(model_names)}")
            
            # Initialize performance tracking
            for model in available_models:
                self.performance_stats['model_usage'][model.value] = {
                    'requests': 0,
                    'successes': 0,
                    'failures': 0,
                    'avg_response_time': 0.0
                }
        else:
            logger.warning("⚠️ No AI model API keys configured. Set GEMINI_API_KEY, TOGETHER_API_KEY, or OPENAI_API_KEY")
    
    def get_available_models(self) -> List[ModelType]:
        """Get list of available models based on API keys"""
        available = []
        if self.gemini_api_key:
            available.extend([ModelType.GEMINI_1_5_FLASH, ModelType.GEMINI_1_5_PRO, ModelType.GEMINI_2_0_FLASH])
        if self.together_api_key:
            available.append(ModelType.TOGETHER_LLAMA_VISION)
        if self.openai_api_key:
            available.extend([ModelType.OPENAI_GPT4O_MINI, ModelType.OPENAI_GPT4O])
        return available
    
    def _determine_challenge_type(self, instruction: str) -> ChallengeType:
        """Determine challenge type from instruction"""
        instruction_lower = instruction.lower()
        
        # Multi-select indicators
        multi_indicators = ['all', 'every', 'each', 'multiple']
        if any(indicator in instruction_lower for indicator in multi_indicators):
            return ChallengeType.IMAGE_LABEL_MULTI_SELECT
        
        # Single select indicators  
        single_indicators = ['the', 'one', 'single', 'which']
        if any(indicator in instruction_lower for indicator in single_indicators):
            return ChallengeType.IMAGE_LABEL_SINGLE_SELECT
        
        # Default to binary
        return ChallengeType.IMAGE_LABEL_BINARY
    
    def _create_image_grid(self, images: List[str], rows: int, columns: int) -> str:
        """Create a visual representation of the image grid for debugging"""
        grid_repr = f"Image Grid ({rows}x{columns}):\n"
        for row in range(rows):
            row_repr = ""
            for col in range(columns):
                idx = row * columns + col
                if idx < len(images):
                    row_repr += f"[{row},{col}] "
                else:
                    row_repr += "[ - ] "
            grid_repr += row_repr + "\n"
        return grid_repr
    
    def _optimize_images_for_model(self, images: List[str], model_config: ModelConfig) -> List[str]:
        """Optimize images for specific model constraints"""
        if len(images) <= model_config.max_images:
            return images
        
        logger.warning(f"Too many images ({len(images)}) for {model_config.name}, limiting to {model_config.max_images}")
        return images[:model_config.max_images]
    
    def _extract_json_from_response(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from AI model response with multiple fallback strategies"""
        if not text:
            return None
        
        # Strategy 1: Look for JSON code blocks
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        matches = re.findall(json_pattern, text, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        # Strategy 2: Look for JSON objects in text
        json_pattern = r'\{[^{}]*"challenge_prompt"[^{}]*"coordinates"[^{}]*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        # Strategy 3: Try to parse the entire response as JSON
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        
        # Strategy 4: Extract coordinates with regex
        coord_pattern = r'\[(\d+),\s*(\d+)\]'
        coordinates = re.findall(coord_pattern, text)
        
        if coordinates:
            return {
                "challenge_prompt": "extracted from text",
                "coordinates": [{"box_2d": [int(row), int(col)]} for row, col in coordinates]
            }
        
        logger.warning(f"Failed to extract JSON from response: {text[:200]}...")
        return None
    
    def _convert_coordinates_to_tiles(self, coordinates: List[Dict[str, List[int]]], columns: int) -> List[int]:
        """Convert coordinate format to tile numbers (1-based)"""
        tiles = []
        for coord in coordinates:
            if 'box_2d' in coord:
                row, col = coord['box_2d']
                tile_num = row * columns + col + 1  # Convert to 1-based indexing
                tiles.append(tile_num)
        return sorted(tiles)
    
    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()
    
    async def _call_gemini_advanced(self, model_type: ModelType, images: List[str], 
                                   instruction: str, challenge_type: ChallengeType) -> Optional[ImageBinaryChallenge]:
        """Advanced Gemini API call with structured output and thinking support"""
        try:
            model_config = self.models[model_type]
            start_time = time.time()
            
            # Prepare the request payload
            contents = []
            
            # Add system instruction
            system_instruction = self.prompt_engine.SYSTEM_INSTRUCTIONS[challenge_type]
            
            # Add images
            parts = []
            for img_b64 in images:
                if img_b64.startswith('data:'):
                    img_b64 = img_b64.split(',', 1)[1]
                
                parts.append({
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": img_b64
                    }
                })
            
            # Add user prompt
            user_prompt = self.prompt_engine.USER_PROMPTS["grid_analysis"].format(
                rows=3, columns=3, total_images=len(images), instruction=instruction
            )
            parts.append({"text": user_prompt})
            
            contents.append({
                "role": "user",
                "parts": parts
            })
            
            # Prepare generation config
            generation_config = {
                "temperature": model_config.temperature,
                "maxOutputTokens": model_config.max_tokens,
                "responseMimeType": "application/json" if model_config.supports_structured_output else "text/plain"
            }
            
            # Add thinking config for supported models
            if model_config.supports_thinking and model_config.thinking_budget:
                generation_config["thinkingConfig"] = {
                    "includeThoughts": False,
                    "thinkingBudget": model_config.thinking_budget
                }
            
            payload = {
                "contents": contents,
                "generationConfig": generation_config,
                "systemInstruction": {"parts": [{"text": system_instruction}]}
            }
            
            # Make API call
            headers = {
                'Content-Type': 'application/json'
            }
            
            url = f"{model_config.endpoint}?key={self.gemini_api_key}"
            
            async with self.session.post(url, json=payload, headers=headers) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    
                    if 'candidates' in data and data['candidates']:
                        content = data['candidates'][0].get('content', {})
                        if 'parts' in content and content['parts']:
                            text = content['parts'][0].get('text', '')
                            
                            # Extract structured response
                            json_data = self._extract_json_from_response(text)
                            if json_data:
                                self._update_performance_stats(model_type.value, True, response_time)
                                return ImageBinaryChallenge.from_dict(json_data)
                
                error_text = await response.text()
                logger.error(f"❌ {model_config.name} API error {response.status}: {error_text}")
                self._update_performance_stats(model_type.value, False, response_time)
                
        except Exception as e:
            logger.error(f"❌ {model_config.name} API call failed: {e}")
            self._update_performance_stats(model_type.value, False, 0)
        
        return None
    
    async def _call_openai_advanced(self, model_type: ModelType, images: List[str], 
                                   instruction: str, challenge_type: ChallengeType) -> Optional[ImageBinaryChallenge]:
        """Advanced OpenAI API call with structured output"""
        try:
            model_config = self.models[model_type]
            start_time = time.time()
            
            # Prepare messages
            system_instruction = self.prompt_engine.SYSTEM_INSTRUCTIONS[challenge_type]
            user_prompt = self.prompt_engine.USER_PROMPTS["grid_analysis"].format(
                rows=3, columns=3, total_images=len(images), instruction=instruction
            )
            
            messages = [
                {"role": "system", "content": system_instruction},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt}
                    ]
                }
            ]
            
            # Add images
            for img_b64 in images:
                if not img_b64.startswith('data:'):
                    img_b64 = f"data:image/jpeg;base64,{img_b64}"
                
                messages[1]["content"].append({
                    "type": "image_url",
                    "image_url": {"url": img_b64}
                })
            
            # Prepare payload
            payload = {
                "model": model_config.model_id,
                "messages": messages,
                "temperature": model_config.temperature,
                "max_tokens": model_config.max_tokens
            }
            
            # Add structured output for supported models
            if model_config.supports_structured_output:
                payload["response_format"] = {
                    "type": "json_object"
                }
            
            headers = {
                'Authorization': f'Bearer {self.openai_api_key}',
                'Content-Type': 'application/json'
            }
            
            async with self.session.post(model_config.endpoint, json=payload, headers=headers) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    
                    if 'choices' in data and data['choices']:
                        content = data['choices'][0].get('message', {}).get('content', '')
                        
                        json_data = self._extract_json_from_response(content)
                        if json_data:
                            self._update_performance_stats(model_type.value, True, response_time)
                            return ImageBinaryChallenge.from_dict(json_data)
                
                error_text = await response.text()
                logger.error(f"❌ {model_config.name} API error {response.status}: {error_text}")
                self._update_performance_stats(model_type.value, False, response_time)
                
        except Exception as e:
            logger.error(f"❌ {model_config.name} API call failed: {e}")
            self._update_performance_stats(model_type.value, False, 0)
        
        return None
    
    async def _call_together_advanced(self, model_type: ModelType, images: List[str], 
                                     instruction: str, challenge_type: ChallengeType) -> Optional[ImageBinaryChallenge]:
        """Advanced Together AI API call"""
        try:
            model_config = self.models[model_type]
            start_time = time.time()
            
            # Prepare messages
            system_instruction = self.prompt_engine.SYSTEM_INSTRUCTIONS[challenge_type]
            user_prompt = self.prompt_engine.USER_PROMPTS["grid_analysis"].format(
                rows=3, columns=3, total_images=len(images), instruction=instruction
            )
            
            messages = [
                {"role": "system", "content": system_instruction},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt}
                    ]
                }
            ]
            
            # Add images
            for img_b64 in images:
                if not img_b64.startswith('data:'):
                    img_b64 = f"data:image/jpeg;base64,{img_b64}"
                
                messages[1]["content"].append({
                    "type": "image_url",
                    "image_url": {"url": img_b64}
                })
            
            payload = {
                "model": model_config.model_id,
                "messages": messages,
                "temperature": model_config.temperature,
                "max_tokens": model_config.max_tokens
            }
            
            headers = {
                'Authorization': f'Bearer {self.together_api_key}',
                'Content-Type': 'application/json'
            }
            
            async with self.session.post(model_config.endpoint, json=payload, headers=headers) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    
                    if 'choices' in data and data['choices']:
                        content = data['choices'][0].get('message', {}).get('content', '')
                        
                        json_data = self._extract_json_from_response(content)
                        if json_data:
                            self._update_performance_stats(model_type.value, True, response_time)
                            return ImageBinaryChallenge.from_dict(json_data)
                
                error_text = await response.text()
                logger.error(f"❌ {model_config.name} API error {response.status}: {error_text}")
                self._update_performance_stats(model_type.value, False, response_time)
                
        except Exception as e:
            logger.error(f"❌ {model_config.name} API call failed: {e}")
            self._update_performance_stats(model_type.value, False, 0)
        
        return None
    
    def _update_performance_stats(self, model_name: str, success: bool, response_time: float):
        """Update performance statistics"""
        self.performance_stats['total_requests'] += 1
        
        if success:
            self.performance_stats['successful_requests'] += 1
        else:
            self.performance_stats['failed_requests'] += 1
        
        # Update average response time
        total_time = self.performance_stats['average_response_time'] * (self.performance_stats['total_requests'] - 1)
        self.performance_stats['average_response_time'] = (total_time + response_time) / self.performance_stats['total_requests']
        
        # Update model-specific stats
        if model_name in self.performance_stats['model_usage']:
            stats = self.performance_stats['model_usage'][model_name]
            stats['requests'] += 1
            
            if success:
                stats['successes'] += 1
            else:
                stats['failures'] += 1
            
            # Update model average response time
            if stats['requests'] > 1:
                total_model_time = stats['avg_response_time'] * (stats['requests'] - 1)
                stats['avg_response_time'] = (total_model_time + response_time) / stats['requests']
            else:
                stats['avg_response_time'] = response_time
    
    async def analyze_images(self, images: List[str], instruction: str, 
                           rows: int = 3, columns: int = 3) -> Tuple[bool, List[int]]:
        """
        Advanced image analysis using multiple AI models with intelligent fallback
        
        Args:
            images: List of base64 encoded images
            instruction: hCaptcha instruction text
            rows: Number of grid rows
            columns: Number of grid columns
            
        Returns:
            Tuple of (success, tile_numbers)
        """
        if not images or not instruction:
            return False, []
        
        logger.info(f"🤖 Advanced analysis: {len(images)} images, instruction: '{instruction}'")
        logger.debug(self._create_image_grid(images, rows, columns))
        
        # Determine challenge type
        challenge_type = self._determine_challenge_type(instruction)
        logger.info(f"🎯 Challenge type detected: {challenge_type.value}")
        
        # Get available models in priority order
        available_models = self.get_available_models()
        if not available_models:
            logger.error("❌ No AI models available")
            return False, []
        
        # Model priority order (best to worst)
        model_priority = [
            ModelType.GEMINI_2_0_FLASH,      # Best: Latest with thinking
            ModelType.GEMINI_1_5_PRO,        # Good: Pro with thinking
            ModelType.OPENAI_GPT4O,          # Good: OpenAI flagship
            ModelType.GEMINI_1_5_FLASH,      # Fast: Good balance
            ModelType.OPENAI_GPT4O_MINI,     # Fast: Cheaper OpenAI
            ModelType.TOGETHER_LLAMA_VISION  # Fallback: Free alternative
        ]
        
        # Filter available models by priority
        models_to_try = [model for model in model_priority if model in available_models]
        
        logger.info(f"🔄 Trying {len(models_to_try)} models in priority order")
        
        for model_type in models_to_try:
            model_config = self.models[model_type]
            logger.info(f"🤖 Attempting with {model_config.name}...")
            
            try:
                # Optimize images for model constraints
                optimized_images = self._optimize_images_for_model(images, model_config)
                
                # Call appropriate model API
                result = None
                if model_type.value.startswith('gemini'):
                    result = await self._call_gemini_advanced(model_type, optimized_images, instruction, challenge_type)
                elif model_type.value.startswith('gpt'):
                    result = await self._call_openai_advanced(model_type, optimized_images, instruction, challenge_type)
                elif model_type.value.startswith('meta-llama'):
                    result = await self._call_together_advanced(model_type, optimized_images, instruction, challenge_type)
                
                if result and result.coordinates:
                    # Convert coordinates to tile numbers
                    tiles = self._convert_coordinates_to_tiles(result.coordinates, columns)
                    
                    if tiles:
                        logger.success(f"✅ {model_config.name} solved: tiles {tiles}")
                        return True, tiles
                    else:
                        logger.info(f"🚫 {model_config.name}: No matching images found")
                        return True, []  # Valid response, just no matches
                
                logger.warning(f"⚠️ {model_config.name} returned no valid result")
                
            except Exception as e:
                logger.error(f"❌ {model_config.name} failed: {e}")
                continue
        
        logger.error("❌ All AI models failed to analyze images")
        return False, []
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return self.performance_stats.copy()
    
    def reset_performance_stats(self):
        """Reset performance statistics"""
        self.performance_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_response_time': 0.0,
            'model_usage': {}
        }
        
        # Reinitialize model stats
        for model in self.get_available_models():
            self.performance_stats['model_usage'][model.value] = {
                'requests': 0,
                'successes': 0,
                'failures': 0,
                'avg_response_time': 0.0
            }
    
    def __del__(self):
        """Cleanup on destruction"""
        if self.session and not self.session.closed:
            try:
                asyncio.create_task(self.session.close())
            except:
                pass