from types import SimpleNamespace

import langgraph_fabric_m365.main as main_m365


def test_create_server_app_registers_messages_routes() -> None:
    agent_app = SimpleNamespace(adapter=object())
    settings = SimpleNamespace(
        microsoft_app_id="app-id",
        microsoft_tenant_id="tenant-id",
        microsoft_app_password="secret",
    )

    app = main_m365.create_server_app(agent_app, settings)

    routes = {(route.method, route.resource.canonical) for route in app.router.routes()}
    assert ("POST", "/api/messages") in routes
    assert ("GET", "/api/messages") in routes
    assert main_m365.AGENT_CONFIGURATION_KEY in app
    assert main_m365.AGENT_CONFIGURATION_STATE_KEY in app
    assert app[main_m365.AGENT_APP_KEY] is agent_app
    assert app[main_m365.ADAPTER_KEY] is agent_app.adapter
    assert app[main_m365.AGENT_APP_STATE_KEY] is agent_app
    assert app[main_m365.ADAPTER_STATE_KEY] is agent_app.adapter


def test_create_server_app_uses_jwt_authorization_middleware() -> None:
    agent_app = SimpleNamespace(adapter=object())
    settings = SimpleNamespace(
        microsoft_app_id="app-id",
        microsoft_tenant_id="tenant-id",
        microsoft_app_password="secret",
    )

    app = main_m365.create_server_app(agent_app, settings)

    assert main_m365.jwt_authorization_middleware in app.middlewares


def test_create_server_app_with_no_channel_factory() -> None:
    """When adapter lacks channel_service_client_factory, auth config uses settings."""
    from microsoft_agents.hosting.core.authorization import AgentAuthConfiguration

    agent_app = SimpleNamespace(adapter=SimpleNamespace())  # No factory method
    settings = SimpleNamespace(
        microsoft_app_id="app-id",
        microsoft_tenant_id="tenant-id",
        microsoft_app_password="secret",
    )

    app = main_m365.create_server_app(agent_app, settings)

    config = app[main_m365.AGENT_CONFIGURATION_KEY]
    assert isinstance(config, AgentAuthConfiguration)
    assert config.CLIENT_ID == "app-id"
    assert config.TENANT_ID == "tenant-id"
    assert config.CLIENT_SECRET == "secret"


def test_main_starts_server_on_configured_port(monkeypatch) -> None:
    settings = SimpleNamespace(
        log_level="INFO",
        log_level_override=None,
        port=8765,
        microsoft_app_id="app-id",
        microsoft_tenant_id="tenant-id",
        microsoft_app_password="secret",
    )
    agent_app = SimpleNamespace(adapter=object())

    monkeypatch.setattr(main_m365, "get_settings", lambda: settings)
    monkeypatch.setattr(main_m365, "configure_logging", lambda *_: None)

    async def _fake_build_m365_agent_app():
        return agent_app

    monkeypatch.setattr(main_m365, "_build_m365_agent_app", _fake_build_m365_agent_app)

    run_app_calls: list[tuple[object, str, int]] = []

    def _fake_run_app(app, host: str, port: int) -> None:
        run_app_calls.append((app, host, port))

    monkeypatch.setattr(main_m365, "run_app", _fake_run_app)

    main_m365.main()

    assert len(run_app_calls) == 1
    _, host, port = run_app_calls[0]
    assert host == "0.0.0.0"
    assert port == 8765


def test_resolve_agent_auth_configuration_uses_connection_manager() -> None:
    """When adapter has connection_manager, auth config uses it."""
    # Mock a connection manager with get_default_connection_configuration
    mock_connection_config = SimpleNamespace(CLIENT_ID="cm-app-id")
    mock_connection_manager = SimpleNamespace(
        get_default_connection_configuration=lambda: mock_connection_config
    )
    mock_channel_factory = SimpleNamespace(_connection_manager=mock_connection_manager)
    mock_adapter = SimpleNamespace(_channel_service_client_factory=mock_channel_factory)
    agent_app = SimpleNamespace(adapter=mock_adapter)

    settings = SimpleNamespace(
        microsoft_app_id="settings-app-id",
        microsoft_tenant_id="settings-tenant-id",
        microsoft_app_password="settings-secret",
    )

    app = main_m365.create_server_app(agent_app, settings)

    config = app[main_m365.AGENT_CONFIGURATION_KEY]
    # Should use connection manager config, not settings
    assert config is mock_connection_config


def test_health_check_endpoint_returns_200(monkeypatch) -> None:
    """GET /api/messages should return 200 status."""
    from aiohttp import web
    from aiohttp.test_utils import TestClient, TestServer

    agent_app = SimpleNamespace(adapter=object())
    settings = SimpleNamespace(
        microsoft_app_id="app-id",
        microsoft_tenant_id="tenant-id",
        microsoft_app_password="secret",
    )

    # Mock JWT middleware using new-style middleware
    @web.middleware
    async def noop_jwt_middleware(request, handler):
        return await handler(request)

    monkeypatch.setattr(main_m365, "jwt_authorization_middleware", noop_jwt_middleware)

    app = main_m365.create_server_app(agent_app, settings)

    # Create a test client and make a synchronous GET request
    import asyncio

    async def _test():
        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/api/messages")
            return resp.status

    status = asyncio.run(_test())
    assert status == 200


def test_entry_point_handler_calls_start_agent_process(monkeypatch) -> None:
    """POST /api/messages should call start_agent_process."""
    from aiohttp import web
    from aiohttp.test_utils import TestClient, TestServer

    start_agent_process_calls = []

    async def mock_start_agent_process(request, agent_app_arg, adapter_arg):
        start_agent_process_calls.append((agent_app_arg, adapter_arg))
        return None

    monkeypatch.setattr(main_m365, "start_agent_process", mock_start_agent_process)

    # Mock JWT middleware using new-style middleware
    @web.middleware
    async def noop_jwt_middleware(request, handler):
        return await handler(request)

    monkeypatch.setattr(main_m365, "jwt_authorization_middleware", noop_jwt_middleware)

    agent_app = SimpleNamespace(adapter=object())
    settings = SimpleNamespace(
        microsoft_app_id="app-id",
        microsoft_tenant_id="tenant-id",
        microsoft_app_password="secret",
    )

    app = main_m365.create_server_app(agent_app, settings)

    import asyncio

    async def _test():
        async with TestClient(TestServer(app)) as client:
            resp = await client.post("/api/messages")
            return resp.status

    status = asyncio.run(_test())
    # Should return 201 (from Response(status=201) when start_agent_process returns None)
    assert status == 201
    # Verify start_agent_process was called with the correct app and adapter
    assert len(start_agent_process_calls) == 1
    called_app, called_adapter = start_agent_process_calls[0]
    assert called_app is agent_app
    assert called_adapter is agent_app.adapter
