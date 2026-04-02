from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


def parse_bool_env(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def parse_int_env(value: str | None, default: int) -> int:
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass
class Settings:
    app_env: str = os.getenv("APP_ENV", "local")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    inputs_dir: str = os.getenv("INPUTS_DIR", "inputs")
    artifacts_dir: str = os.getenv("ARTIFACTS_DIR", "artifacts")
    logs_dir: str = os.getenv("LOGS_DIR", "logs")
    outputs_dir: str = os.getenv("OUTPUTS_DIR", "outputs")
    enable_codex_generation: bool = parse_bool_env(os.getenv("ENABLE_CODEX_GENERATION"), False)
    codex_executable: str = os.getenv("CODEX_EXECUTABLE", "codex").strip() or "codex"
    codex_target_batch: str = os.getenv("CODEX_TARGET_BATCH", "high__home").strip() or "high__home"
    codex_max_items: int = parse_int_env(os.getenv("CODEX_MAX_ITEMS"), 5)
    enable_llm_generation: bool = parse_bool_env(os.getenv("ENABLE_LLM_GENERATION"), False)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "").strip()
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    llm_target_batch: str = os.getenv("LLM_TARGET_BATCH", "high__home").strip() or "high__home"
    llm_max_items: int = parse_int_env(os.getenv("LLM_MAX_ITEMS"), 5)


def get_settings() -> Settings:
    return Settings()
