"""OpenRouter provider configuration for Agents SDK."""

import os
import logging
from typing import Optional
from openai import OpenAI, AsyncOpenAI

logger = logging.getLogger(__name__)

# Global OpenRouter client instances
_openrouter_sync_client: Optional[OpenAI] = None
_openrouter_async_client: Optional[AsyncOpenAI] = None
_initialized = False


def initialize_openrouter_for_agents():
    """Initialize OpenRouter as the default OpenAI client for Agents SDK.

    This configures the Agents SDK to route all model calls through OpenRouter
    instead of directly to OpenAI. This allows using models like Claude through
    the Agents SDK.

    Must be called before running any agents.
    """
    global _openrouter_sync_client, _openrouter_async_client, _initialized

    if _initialized:
        logger.debug("[OPENROUTER_PROVIDER] Already initialized")
        return

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY not found in environment. "
            "Set this to use Agents SDK with OpenRouter."
        )

    # Create OpenAI clients configured to use OpenRouter
    _openrouter_sync_client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    _openrouter_async_client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    # Set as default clients for Agents SDK
    from agents import set_default_openai_client

    set_default_openai_client(_openrouter_sync_client, _openrouter_async_client)

    _initialized = True
    logger.info("[OPENROUTER_PROVIDER] Initialized OpenRouter for Agents SDK")


def get_openrouter_sync_client() -> OpenAI:
    """Get OpenRouter-configured sync OpenAI client.

    Returns:
        Sync OpenAI client pointing at OpenRouter
    """
    if not _initialized:
        initialize_openrouter_for_agents()
    return _openrouter_sync_client


def get_openrouter_async_client() -> AsyncOpenAI:
    """Get OpenRouter-configured async OpenAI client.

    Returns:
        Async OpenAI client pointing at OpenRouter
    """
    if not _initialized:
        initialize_openrouter_for_agents()
    return _openrouter_async_client


# Initialize automatically on import for convenience
try:
    initialize_openrouter_for_agents()
except Exception as e:
    logger.warning(
        f"[OPENROUTER_PROVIDER] Could not auto-initialize: {e}. "
        "Call initialize_openrouter_for_agents() explicitly if needed."
    )
