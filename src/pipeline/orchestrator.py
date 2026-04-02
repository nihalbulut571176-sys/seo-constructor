import json
from pathlib import Path

from config import Settings
from src.pipeline.context import PipelineContext
from src.pipeline import steps
from src.tools.file_store import ensure_directories
from src.utils.logger import get_logger


class PipelineOrchestrator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = get_logger(__name__, settings.log_level)

    def load_project_input(self) -> dict:
        input_path = Path(self.settings.inputs_dir) / "project.json"
        self.logger.info("Loading project input from %s", input_path)

        with input_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def run(self) -> PipelineContext:
        self.logger.info("Pipeline started")
        ensure_directories()

        input_data = self.load_project_input()
        context = PipelineContext(input_data=input_data)

        context = steps.collect_competitors(context)
        context = steps.build_site_structure(context)
        context = steps.collect_semantics(context)
        context = steps.build_build_spec(context)
        context = steps.build_seo_priorities(context)
        context = steps.extract_pains(context)
        context = steps.build_gap_analysis(context)
        context = steps.build_page_blueprints(context)
        context = steps.build_execution_plan(context)
        context = steps.build_project_package(context)
        context = steps.build_page_task_queue(context)
        context = steps.build_section_briefs(context)
        context = steps.build_content_input_queue(context)
        context = steps.build_generation_batches(context)
        context = steps.build_generation_manifest(context)

        self.logger.info("Saved artifacts: %s", list(context.artifacts_index.values()))
        self.logger.info("Pipeline finished")
        return context
