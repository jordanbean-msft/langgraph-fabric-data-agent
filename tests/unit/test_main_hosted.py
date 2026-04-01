from types import SimpleNamespace

import langgraph_fabric_data_agent.main_hosted as main_hosted


def test_create_server_app_registers_messages_routes() -> None:
    agent_app = SimpleNamespace(adapter=object())
    settings = SimpleNamespace(
        microsoft_app_id="app-id",
        microsoft_tenant_id="tenant-id",
        microsoft_app_password="secret",
    )

    app = main_hosted.create_server_app(agent_app, settings)

    routes = {(route.method, route.resource.canonical) for route in app.router.routes()}
    assert ("POST", "/api/messages") in routes
    assert ("GET", "/api/messages") in routes
    assert "agent_configuration" in app
    assert app["agent_app"] is agent_app
    assert app["adapter"] is agent_app.adapter


def test_main_starts_server_on_configured_port(monkeypatch) -> None:
    settings = SimpleNamespace(log_level="INFO", log_level_override=None, port=8765)
    agent_app = SimpleNamespace(adapter=object())

    monkeypatch.setattr(main_hosted, "get_settings", lambda: settings)
    monkeypatch.setattr(main_hosted, "configure_logging", lambda *_: None)

    async def _fake_build_hosted_agent_app() -> SimpleNamespace:
        return agent_app

    monkeypatch.setattr(main_hosted, "_build_hosted_agent_app", _fake_build_hosted_agent_app)

    run_app_calls: list[tuple[object, str, int]] = []

    def _fake_create_server_app(_agent_app, _settings):
        return object()

    monkeypatch.setattr(main_hosted, "create_server_app", _fake_create_server_app)

    def _fake_run_app(app, host: str, port: int) -> None:
        run_app_calls.append((app, host, port))

    monkeypatch.setattr(main_hosted, "run_app", _fake_run_app)

    main_hosted.main()

    assert len(run_app_calls) == 1
    _, host, port = run_app_calls[0]
    assert host == "0.0.0.0"
    assert port == 8765
