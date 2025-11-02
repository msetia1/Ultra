"""OpenRouter model provider for Agents SDK.

Implements custom ModelProvider that routes all model calls through OpenRouter,
allowing use of models like Claude (anthropic/*) via the Agents SDK.

Pattern based on Plan Editor V2 implementation.
"""

import os
import logging
from openai import AsyncOpenAI
from agents import ModelProvider, OpenAIChatCompletionsModel, Model, set_tracing_disabled

# Disable tracing for calendar chat (hackathon project, no LangSmith setup)
set_tracing_disabled(True)

logger = logging.getLogger(__name__)

# OpenRouter client for Agents SDK
openrouter_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)


class OpenRouterModelProvider(ModelProvider):
    """Model provider that routes all models through OpenRouter.

    This allows the Agents SDK to use any model supported by OpenRouter,
    including anthropic/claude-*, google/gemini-*, etc.

    The provider accepts any model name and passes it directly to OpenRouter,
    which handles the routing to the appropriate provider.
    """

    def get_model(self, model_name: str | None) -> Model:
        """Get model instance for the given model name.

        Args:
            model_name: Full model name (e.g., "anthropic/claude-3.5-sonnet")

        Returns:
            OpenAIChatCompletionsModel configured with OpenRouter client
        """
        return OpenAIChatCompletionsModel(
            model=model_name,
            openai_client=openrouter_client,
        )

    def supports_model(self, model_name: str) -> bool:
        """Check if this provider supports the given model.

        Args:
            model_name: Model name to check

        Returns:
            True - OpenRouter handles all model routing
        """
        # Accept all model names - OpenRouter handles routing
        return True


# Singleton provider instance
OPENROUTER_PROVIDER = OpenRouterModelProvider()


def get_openrouter_async_client() -> AsyncOpenAI:
    """Get OpenRouter-configured async OpenAI client.

    This client is used for direct API calls (e.g., Morph API) that don't
    go through the Agents SDK.

    Returns:
        Async OpenAI client pointing at OpenRouter
    """
    return openrouter_client
