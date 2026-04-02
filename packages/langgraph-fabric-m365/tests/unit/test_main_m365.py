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


def test_main_starts_server_on_configured_port(monkeypatch) -> None:
    settings = SimpleNamespace(log_level="INFO", log_level_override=None, port=8765)
    agent_app = SimpleNamespace(adapter=object())

    monkeypatch.setattr(main_m365, "get_settings", lambda: settings)
    monkeypatch.setattr(main_m365, "configure_logging", lambda *_: None)

    async def _fake_build_m365_agent_app() -> SimpleNamespace:
        return agent_app

    monkeypatch.setattr(main_m365, "_build_m365_agent_app", _fake_build_m365_agent_app)

    run_app_calls: list[tuple[object, str, int]] = []

    def _fake_create_server_app(_agent_app, _settings):
        return object()

    monkeypatch.setattr(main_m365, "create_server_app", _fake_create_server_app)

    def _fake_run_app(app, host: str, port: int) -> None:
        run_app_calls.append((app, host, port))

    monkeypatch.setattr(main_m365, "run_app", _fake_run_app)

    main_m365.main()

    assert len(run_app_calls) == 1
    _, host, port = run_app_calls[0]
    assert host == "0.0.0.0"
    assert port == 8765
