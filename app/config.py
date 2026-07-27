from groundwork import BaseConfig


class AppConfig(BaseConfig):
    """App settings. Inherits app_env / log_level / OpenRouter keys from groundwork.BaseConfig
    and adds this app's runtime, data, and model-selection fields. All fields have safe
    defaults so the process starts; required values come from .env / the environment."""

    # Runtime
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    smoke_test_token: str = ""

    # Data
    database_url: str = "postgresql+psycopg://aignite:aignite@localhost:5432/parallax"
    redis_url: str = "redis://localhost:6379/0"

    # LLM runtime bounds. Reads LLM_TIMEOUT_SECONDS (already documented in .env.example);
    # without it the OpenAI client default is 600s, long enough to pin workers.
    llm_timeout_seconds: float = 60.0

    # Model selection — pinned from env, never hardcoded. Blank until populated.
    llm_model_reasoning: str = ""
    llm_model_extraction: str = ""
    llm_model_judge: str = ""
    embedding_model: str = ""


settings = AppConfig()
