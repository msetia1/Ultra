"""OpenRouter client wrapper for calendar agents."""

import os
from typing import Optional
from openai import AsyncOpenAI


class OpenRouterClient:
    """Wrapper for OpenAI SDK configured to use OpenRouter."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenRouter client.

        Args:
            api_key: OpenRouter API key. If not provided, reads from OPENROUTER_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment")

        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )

    async def chat_completion(
        self,
        messages: list[dict],
        model: str = "anthropic/claude-3.5-sonnet",
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str | dict] = None,
        stream: bool = False,
        **kwargs,
    ):
        """Create a chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name in OpenRouter format (e.g., 'anthropic/claude-3.5-sonnet')
            tools: Optional list of tool/function definitions
            tool_choice: Optional tool choice strategy
            stream: Whether to stream the response
            **kwargs: Additional parameters for the API call

        Returns:
            Chat completion response or stream
        """
        params = {
            "model": model,
            "messages": messages,
            "stream": stream,
            **kwargs,
        }

        if tools:
            params["tools"] = tools
        if tool_choice:
            params["tool_choice"] = tool_choice

        return await self.client.chat.completions.create(**params)


# Singleton instance
_openrouter_client: Optional[OpenRouterClient] = None


def get_openrouter_client() -> OpenRouterClient:
    """Get or create singleton OpenRouter client."""
    global _openrouter_client
    if _openrouter_client is None:
        _openrouter_client = OpenRouterClient()
    return _openrouter_client
