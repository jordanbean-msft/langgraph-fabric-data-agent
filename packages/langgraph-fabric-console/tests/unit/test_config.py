from langgraph_fabric_console import config as config_module


def test_env_file_points_to_package_local_dotenv() -> None:
    expected = config_module.Path(config_module.__file__).parents[2] / ".env"
    env_file = config_module.ConsoleSettings.model_config.get("env_file")
    assert env_file == str(expected)


def test_get_settings_returns_cached_instance(monkeypatch) -> None:
    config_module.get_settings.cache_clear()
    created: list[object] = []

    def fake_console_settings() -> object:
        instance = object()
        created.append(instance)
        return instance

    monkeypatch.setattr(config_module, "ConsoleSettings", fake_console_settings)

    first = config_module.get_settings()
    second = config_module.get_settings()

    assert first is second
    assert len(created) == 1

    config_module.get_settings.cache_clear()
