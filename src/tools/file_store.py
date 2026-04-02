import json
from pathlib import Path
from typing import Any

from config import get_settings
from src.pipeline.context import PipelineContext


def ensure_directory(path: str) -> Path:
    """Ensure that a directory exists and return its path."""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def ensure_directories() -> None:
    """Ensure that project runtime directories exist."""
    settings = get_settings()
    ensure_directory(settings.inputs_dir)
    ensure_directory(settings.artifacts_dir)
    ensure_directory(settings.logs_dir)
    ensure_directory(settings.outputs_dir)


def save_json_artifact(data: Any, filename: str) -> str:
    """Save JSON data into the artifacts directory and return its path."""
    settings = get_settings()
    artifacts_dir = ensure_directory(settings.artifacts_dir)
    filepath = artifacts_dir / filename

    with filepath.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    return str(filepath.resolve())


def load_json_artifact(filename: str) -> Any:
    """Load JSON data from the artifacts directory."""
    settings = get_settings()
    filepath = Path(settings.artifacts_dir) / filename

    with filepath.open("r", encoding="utf-8") as file:
        return json.load(file)


def register_artifact(context: PipelineContext, key: str, filepath: str) -> PipelineContext:
    """Register an artifact path in the pipeline context."""
    context.artifacts_index[key] = filepath
    return context
