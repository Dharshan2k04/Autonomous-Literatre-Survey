"""Pluggable LLM service supporting OpenAI and Anthropic."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.config import get_settings
from app.core.exceptions import LLMServiceUnavailable
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class BaseLLMService(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> str:
        """Generate a completion from the LLM."""
        ...

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
    ) -> str:
        """Generate a structured (JSON) response."""
        ...


class OpenAILLMService(BaseLLMService):
    """OpenAI GPT-based LLM service."""

    def __init__(self):
        if not settings.has_openai:
            raise LLMServiceUnavailable("OpenAI")
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
    ) -> str:
        return await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            json_mode=True,
        )


class AnthropicLLMService(BaseLLMService):
    """Anthropic Claude-based LLM service."""

    def __init__(self):
        if not settings.has_anthropic:
            raise LLMServiceUnavailable("Anthropic")
        from langchain_anthropic import ChatAnthropic
        self.llm = ChatAnthropic(
            model=settings.ANTHROPIC_MODEL,
            api_key=settings.ANTHROPIC_API_KEY,
            temperature=0.7,
            max_tokens=4096,
        )
        self.model = settings.ANTHROPIC_MODEL

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        self.llm.temperature = temperature
        self.llm.max_tokens = max_tokens

        response = await self.llm.ainvoke(messages)
        return response.content or ""

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
    ) -> str:
        json_system = (system_prompt or "") + "\n\nRespond ONLY with valid JSON. No markdown, no explanation."
        return await self.generate(
            prompt=prompt,
            system_prompt=json_system,
            temperature=temperature,
        )


class MockLLMService(BaseLLMService):
    """Mock LLM for development when no API keys are configured."""

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> str:
        logger.warning("mock_llm_used", prompt_length=len(prompt))
        return "[Mock LLM Response] No LLM API key configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY."

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
    ) -> str:
        logger.warning("mock_llm_structured_used", prompt_length=len(prompt))
        return '{"error": "No LLM API key configured"}'


def get_llm_service() -> BaseLLMService:
    """Factory function that returns the configured LLM service."""
    provider = settings.LLM_PROVIDER.lower()

    if provider == "openai" and settings.has_openai:
        return OpenAILLMService()
    elif provider == "anthropic" and settings.has_anthropic:
        return AnthropicLLMService()
    elif settings.has_openai:
        return OpenAILLMService()
    elif settings.has_anthropic:
        return AnthropicLLMService()
    else:
        logger.warning("no_llm_configured", message="Using mock LLM service")
        return MockLLMService()
