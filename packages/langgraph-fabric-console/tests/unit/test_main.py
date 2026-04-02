import runpy
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

from langgraph_fabric_console import main as main_module


def test_main_wires_dependencies_and_runs_console() -> None:
    settings = SimpleNamespace(log_level="INFO", log_level_override="")
    token_provider = object()
    client = object()
    model = object()
    orchestrator = object()
    run_console_coro = object()
    run_console_mock = Mock(return_value=run_console_coro)

    with patch("langgraph_fabric_console.main.get_settings", return_value=settings) as get_settings:
        with patch("langgraph_fabric_console.main.configure_logging") as configure_logging:
            with patch(
                "langgraph_fabric_console.main.FabricTokenProvider",
                return_value=token_provider,
            ) as fabric_token_provider:
                with patch(
                    "langgraph_fabric_console.main.FabricMcpClient",
                    return_value=client,
                ) as fabric_client:
                    with patch(
                        "langgraph_fabric_console.main.create_chat_model",
                        return_value=model,
                    ) as create_chat_model:
                        with patch(
                            "langgraph_fabric_console.main.AgentOrchestrator",
                            return_value=orchestrator,
                        ) as agent_orchestrator:
                            with patch(
                                "langgraph_fabric_console.main.run_console",
                                new=run_console_mock,
                            ) as run_console:
                                with patch(
                                    "langgraph_fabric_console.main.asyncio.run"
                                ) as asyncio_run:
                                    main_module.main()

    get_settings.assert_called_once_with()
    configure_logging.assert_called_once_with("INFO", "")
    fabric_token_provider.assert_called_once_with(settings)
    fabric_client.assert_called_once_with(settings, token_provider)
    create_chat_model.assert_called_once_with(settings)
    agent_orchestrator.assert_called_once_with(model, client)
    run_console.assert_called_once_with(orchestrator)
    asyncio_run.assert_called_once_with(run_console_coro)


def test_module_script_entrypoint_invokes_main_path() -> None:
    settings = SimpleNamespace(log_level="INFO", log_level_override="")
    token_provider = object()
    client = object()
    model = object()
    orchestrator = object()
    run_console_coro = object()
    run_console_mock = Mock(return_value=run_console_coro)

    with patch(
        "langgraph_fabric_console.config.get_settings", return_value=settings
    ) as get_settings:
        with patch("langgraph_fabric_core.core.logging.configure_logging") as configure_logging:
            with patch(
                "langgraph_fabric_core.fabric.auth.FabricTokenProvider",
                return_value=token_provider,
            ) as fabric_token_provider:
                with patch(
                    "langgraph_fabric_core.fabric.mcp_client.FabricMcpClient",
                    return_value=client,
                ) as fabric_client:
                    with patch(
                        "langgraph_fabric_core.llm.factory.create_chat_model",
                        return_value=model,
                    ) as create_chat_model:
                        with patch(
                            "langgraph_fabric_core.graph.orchestrator.AgentOrchestrator",
                            return_value=orchestrator,
                        ) as agent_orchestrator:
                            with patch(
                                "langgraph_fabric_console.console.run_console", new=run_console_mock
                            ) as run_console:
                                with patch("asyncio.run") as asyncio_run:
                                    sys.modules.pop("langgraph_fabric_console.main", None)
                                    runpy.run_module(
                                        "langgraph_fabric_console.main", run_name="__main__"
                                    )

    get_settings.assert_called_once_with()
    configure_logging.assert_called_once_with("INFO", "")
    fabric_token_provider.assert_called_once_with(settings)
    fabric_client.assert_called_once_with(settings, token_provider)
    create_chat_model.assert_called_once_with(settings)
    agent_orchestrator.assert_called_once_with(model, client)
    run_console.assert_called_once_with(orchestrator)
    asyncio_run.assert_called_once_with(run_console_coro)
