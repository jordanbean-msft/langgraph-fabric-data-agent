"""API entrypoint."""

import uvicorn

from langgraph_fabric_data_agent.api import app
from langgraph_fabric_data_agent.config import get_settings
from langgraph_fabric_data_agent.logging_setup import configure_logging


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    uvicorn.run(app, host="0.0.0.0", port=settings.port)


if __name__ == "__main__":
    main()
