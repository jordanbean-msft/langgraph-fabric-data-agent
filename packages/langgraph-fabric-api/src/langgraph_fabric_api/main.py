"""API entrypoint."""

import uvicorn
from langgraph_fabric_core.core.logging import configure_logging

from langgraph_fabric_api.app import app
from langgraph_fabric_api.config import get_settings


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_level_override)
    uvicorn.run(app, host="0.0.0.0", port=settings.port)


if __name__ == "__main__":
    main()
