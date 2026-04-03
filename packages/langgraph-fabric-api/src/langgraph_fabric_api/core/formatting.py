"""Streaming response formatting utilities for SSE and NDJSON."""

import json


def format_sse_event(event: str, data: str) -> bytes:
    """Format an SSE event, prefixing each payload line with `data:`.

    Args:
        event: The event type name.
        data: The event payload data.

    Returns:
        Formatted SSE event as bytes.
    """
    # split("\n") preserves trailing newlines as a trailing empty string,
    # unlike splitlines() which silently drops them.
    data_lines = data.split("\n") if data else [""]
    lines = [f"event: {event}"]
    lines.extend(f"data: {line}" for line in data_lines)
    lines.append("")
    return "\n".join(lines).encode("utf-8")


def format_ndjson_event(event: str, data: str) -> bytes:
    """Format a stream event as a single NDJSON object.

    Args:
        event: The event type name.
        data: The event payload data.

    Returns:
        Formatted NDJSON event as bytes.
    """
    payload = {"event": event, "data": data}
    return (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
