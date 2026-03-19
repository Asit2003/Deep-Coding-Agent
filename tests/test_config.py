from config import AgentConfig


def test_agent_config_forces_openai_provider(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_MODEL_PROVIDER", "gemini")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5-mini")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("AGENT_TEMPERATURE", "0.25")

    config = AgentConfig()

    assert config.provider == "openai"
    assert config.api_key == "openai-key"
    assert config.model_name == "gpt-5-mini"
    assert config.base_url == "https://api.openai.com/v1"
    assert config.temperature == 0.25


def test_agent_config_uses_openai_provider_from_env(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_MODEL_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5-mini")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    config = AgentConfig()

    assert config.provider == "openai"
    assert config.api_key == "openai-key"
    assert config.model_name == "gpt-5-mini"
    assert config.base_url == "https://api.openai.com/v1"
