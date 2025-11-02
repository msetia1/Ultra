"""SSE stream parser for integration tests."""

import json
from typing import List, Dict, Any


async def parse_sse_stream(response) -> List[Dict[str, Any]]:
    """Parse Server-Sent Events from streaming response.

    Args:
        response: httpx Response object with streaming content

    Returns:
        List of parsed SSE events with 'type' and data fields
    """
    events = []
    buffer = ""

    async for chunk in response.aiter_text():
        buffer += chunk

        # Split by double newline (SSE event separator)
        while "\n\n" in buffer:
            event_str, buffer = buffer.split("\n\n", 1)

            # Parse data: prefix
            if event_str.startswith("data: "):
                data_json = event_str[6:]  # Remove "data: " prefix
                try:
                    event_data = json.loads(data_json)
                    events.append(event_data)
                except json.JSONDecodeError:
                    # Skip malformed events
                    pass

    return events


def extract_patches_from_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract proposed patches from SSE events.

    Args:
        events: List of parsed SSE events

    Returns:
        List of patch objects
    """
    patches = []

    for event in events:
        event_type = event.get("type")

        # patch_proposed events contain individual patches
        if event_type == "patch_proposed":
            patch = event.get("patch")
            if patch:
                patches.append(patch)

        # final event contains all patches
        elif event_type == "final":
            final_patches = event.get("patches", [])
            patches.extend(final_patches)

    return patches


def extract_final_message(events: List[Dict[str, Any]]) -> str:
    """Extract final agent message from SSE events.

    Args:
        events: List of parsed SSE events

    Returns:
        Final message string
    """
    for event in reversed(events):  # Check from end
        if event.get("type") == "final":
            return event.get("message", "")

    return ""


def verify_real_time_emission(events: List[Dict[str, Any]]) -> bool:
    """Verify that patches were emitted in real-time (before final event).

    This validates that the Agents SDK streaming is working correctly.

    Args:
        events: List of parsed SSE events

    Returns:
        True if patches came before final event
    """
    patch_indices = []
    final_index = None

    for i, event in enumerate(events):
        if event.get("type") == "patch_proposed":
            patch_indices.append(i)
        elif event.get("type") == "final":
            final_index = i

    # If we have both patches and final, patches should come first
    if patch_indices and final_index is not None:
        return all(idx < final_index for idx in patch_indices)

    # If only patches (no final yet), that's fine
    if patch_indices:
        return True

    # No patches at all
    return False
