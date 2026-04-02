import json
from pathlib import Path
from typing import Any

from config import Settings
from src.tools.file_store import ensure_directory, save_json_artifact
from src.utils.logger import get_logger


class StubOutputWriter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = get_logger(__name__, settings.log_level)

    def load_json(self, filepath: str) -> dict[str, Any]:
        with Path(filepath).open("r", encoding="utf-8") as file:
            return json.load(file)

    def get_cta_label(self, cta_intent: str) -> str:
        labels = {
            "contact_now": "Contact Us",
            "explore_services": "View Services",
            "reduce_friction": "Learn More",
            "build_trust": "Why Choose Us",
            "confirm_local_fit": "Check Availability",
        }
        return labels.get(cta_intent, "Get Started")

    def humanize_value(self, value: str) -> str:
        return value.replace("-", " ").replace("_", " ").strip().title()

    def build_stub_payload(self, item: dict[str, Any]) -> dict[str, Any]:
        content_payload = item.get("content_payload", {})
        section_name = str(item.get("section_name", ""))
        page_slug = str(item.get("page_slug", ""))

        return {
            "item_id": item.get("item_id", ""),
            "page_slug": page_slug,
            "page_type": item.get("page_type", ""),
            "section_name": section_name,
            "priority": item.get("priority", ""),
            "generation_mode": item.get("generation_mode", ""),
            "status": "stub_created",
            "content_stub": {
                "headline": f"{self.humanize_value(section_name)} for {self.humanize_value(page_slug)}",
                "subheadline": "Stub content placeholder for future generation.",
                "bullet_points": content_payload.get("content_requirements", []),
                "cta_label": self.get_cta_label(str(content_payload.get("cta_intent", ""))),
                "notes": [
                    "This is a stub output file.",
                    "Replace with generated content in the next stage.",
                ],
            },
            "source_payload": content_payload,
        }

    def write_section_stub(self, item: dict[str, Any]) -> str:
        page_slug = str(item.get("page_slug", ""))
        section_name = str(item.get("section_name", ""))

        outputs_dir = ensure_directory(self.settings.outputs_dir)
        sections_dir = ensure_directory(str(outputs_dir / "sections"))
        page_dir = ensure_directory(str(sections_dir / page_slug))
        filepath = page_dir / f"{section_name}.json"

        stub_payload = self.build_stub_payload(item)
        with filepath.open("w", encoding="utf-8") as file:
            json.dump(stub_payload, file, indent=2, ensure_ascii=False)

        return str(filepath.resolve())

    def run(self) -> dict[str, Any]:
        execution_log_path = Path(self.settings.artifacts_dir) / "execution_log.json"
        content_queue_path = Path(self.settings.artifacts_dir) / "content_input_queue.json"

        self.logger.info("Loading execution log from %s", execution_log_path)
        execution_log = self.load_json(str(execution_log_path))
        self.logger.info("Loading content input queue from %s", content_queue_path)
        content_queue = self.load_json(str(content_queue_path))

        item_index = {
            str(item.get("item_id", "")): item
            for item in content_queue.get("items", [])
        }

        outputs = []
        for phase in execution_log.get("phases", []):
            for batch in phase.get("batches", []):
                for item_entry in batch.get("items", []):
                    if item_entry.get("status") != "completed":
                        continue

                    item_id = str(item_entry.get("item_id", ""))
                    item = item_index.get(item_id)
                    if not item:
                        continue

                    filepath = self.write_section_stub(item)
                    outputs.append(
                        {
                            "item_id": item_id,
                            "page_slug": item.get("page_slug", ""),
                            "section_name": item.get("section_name", ""),
                            "filepath": filepath,
                        }
                    )

        output_index = {
            "project_name": execution_log.get("project_name", ""),
            "total_output_files": len(outputs),
            "outputs": outputs,
        }
        artifact_path = save_json_artifact(output_index, "output_index.json")
        self.logger.info("Saved output index to %s", artifact_path)
        return output_index
