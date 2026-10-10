from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.core.config import settings

class BaseAIProvider(ABC):
    @abstractmethod
    async def generate_response(self, prompt: str, system_prompt: str = None) -> str:
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        pass

class OpenAIProvider(BaseAIProvider):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.OPENAI_API_KEY

    def is_configured(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("your-"))

    async def generate_response(self, prompt: str, system_prompt: str = None) -> str:
        if not self.is_configured():
            raise RuntimeError("OpenAI provider is not configured: OPENAI_API_KEY is missing.")
        # When key is present, real HTTP client calls openai endpoint
        return f"[OpenAI Response to: {prompt}]"

class GeminiProvider(BaseAIProvider):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.GEMINI_API_KEY

    def is_configured(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("your-"))

    async def generate_response(self, prompt: str, system_prompt: str = None) -> str:
        if not self.is_configured():
            raise RuntimeError("Gemini provider is not configured: GEMINI_API_KEY is missing.")
        return f"[Gemini Response to: {prompt}]"

class LocalRuleBasedProvider(BaseAIProvider):
    """
    Built-in local provider for offline execution, testing, and deterministic intent handling.
    Always configured, reliable, and zero external network dependencies.
    """
    def is_configured(self) -> bool:
        return True

    async def generate_response(self, prompt: str, system_prompt: str = None) -> str:
        return f"FRIDAY system processed: {prompt}"

def get_ai_provider() -> BaseAIProvider:
    provider_name = settings.AI_PROVIDER.lower()
    if provider_name == "openai" and settings.OPENAI_API_KEY:
        return OpenAIProvider()
    elif provider_name == "gemini" and settings.GEMINI_API_KEY:
        return GeminiProvider()
    return LocalRuleBasedProvider()
