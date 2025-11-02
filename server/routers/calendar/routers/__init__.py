"""Calendar routers package."""

from .chat_router import router as chat_router
from .accept_router import router as accept_router
from .generation_router import router as generation_router

__all__ = [
    "chat_router",
    "accept_router",
    "generation_router",
]
