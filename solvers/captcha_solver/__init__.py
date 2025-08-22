"""
Custom Captcha Solver - Unified solver for Turnstile and hCaptcha challenges
Replaces all existing solvers with a single, comprehensive solution.
"""

from .api_server import CaptchaSolverAPI
from .turnstile_handler import TurnstileHandler
from .hcaptcha_handler import HCaptchaHandler
from .ai_models import AIModelManager

__version__ = "1.0.0"
__all__ = ["CaptchaSolverAPI", "TurnstileHandler", "HCaptchaHandler", "AIModelManager"]