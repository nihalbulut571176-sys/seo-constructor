import json
from pathlib import Path
from typing import Any

from config import Settings
from src.tools.file_store import save_json_artifact
from src.utils.logger import get_logger


class GenerationConsumerRunner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = get_logger(__name__, settings.log_level)

    def load_json(self, filepath: str) -> dict[str, Any]:
        with Path(filepath).open("r", encoding="utf-8") as file:
            return json.load(file)

    def build_item_index(self, items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {str(item.get("item_id", "")): item for item in items}

    def process_batch(
        self,
        batch: dict[str, Any],
        content_items: list[dict[str, Any]],
        item_index: dict[str, dict[str, Any]],
    ) -> tuple[dict[str, Any], int, int]:
        batch_ready = bool(batch.get("ready", False))
        matching_items = [
            item
            for item in content_items
            if item.get("priority") == batch.get("priority")
            and item.get("page_type") == batch.get("page_type")
        ]

        if not batch_ready:
            return (
                {
                    "batch_id": batch.get("batch_id", ""),
                    "status": "skipped",
                    "items": [
                        {
                            "item_id": item.get("item_id", ""),
                            "page_slug": item.get("page_slug", ""),
                            "section_name": item.get("section_name", ""),
                            "status": "skipped",
                            "message": "Batch skipped because it is not ready.",
                        }
                        for item in matching_items
                    ],
                },
                0,
                len(matching_items),
            )

        batch_items = []
        completed_items = 0
        skipped_items = 0

        for item in matching_items:
            item_id = str(item.get("item_id", ""))
            indexed_item = item_index.get(item_id)
            item_ready = bool(indexed_item and indexed_item.get("ready", False))

            if item_ready:
                status = "completed"
                message = "Dry-run completed for section item."
                completed_items += 1
            else:
                status = "skipped"
                message = "Item skipped because it is not ready."
                skipped_items += 1

            batch_items.append(
                {
                    "item_id": item_id,
                    "page_slug": item.get("page_slug", ""),
                    "section_name": item.get("section_name", ""),
                    "status": status,
                    "message": message,
                }
            )

        batch_status = "completed" if batch_ready else "skipped"
        return (
            {
                "batch_id": batch.get("batch_id", ""),
                "status": batch_status,
                "items": batch_items,
            },
            completed_items,
            skipped_items,
        )

    def process_phase(
        self,
        phase: dict[str, Any],
        batches_by_id: dict[str, dict[str, Any]],
        content_items: list[dict[str, Any]],
        item_index: dict[str, dict[str, Any]],
    ) -> tuple[dict[str, Any], int, int, int]:
        phase_batches = []
        completed_items = 0
        skipped_items = 0
        total_batches = 0

        for batch_id in phase.get("batch_ids", []):
            batch = batches_by_id.get(batch_id)
            if not batch:
                continue

            batch_entry, batch_completed, batch_skipped = self.process_batch(
                batch=batch,
                content_items=content_items,
                item_index=item_index,
            )
            phase_batches.append(batch_entry)
            completed_items += batch_completed
            skipped_items += batch_skipped
            total_batches += 1

        phase_status = "completed"
        if phase_batches and all(batch["status"] == "skipped" for batch in phase_batches):
            phase_status = "skipped"

        return (
            {
                "phase_name": phase.get("phase_name", ""),
                "status": phase_status,
                "batches": phase_batches,
            },
            total_batches,
            completed_items,
            skipped_items,
        )

    def run(self) -> dict[str, Any]:
        manifest_path = Path(self.settings.artifacts_dir) / "generation_manifest.json"
        content_queue_path = Path(self.settings.artifacts_dir) / "content_input_queue.json"

        self.logger.info("Loading generation manifest from %s", manifest_path)
        manifest = self.load_json(str(manifest_path))
        self.logger.info("Loading content input queue from %s", content_queue_path)
        content_queue = self.load_json(str(content_queue_path))

        content_items = content_queue.get("items", [])
        item_index = self.build_item_index(content_items)
        batches_by_id = {
            str(batch.get("batch_id", "")): batch
            for batch in manifest.get("batches", [])
        }

        phases = []
        total_batches = 0
        completed_items = 0
        skipped_items = 0

        for phase in manifest.get("phases", []):
            phase_entry, phase_batches, phase_completed, phase_skipped = self.process_phase(
                phase=phase,
                batches_by_id=batches_by_id,
                content_items=content_items,
                item_index=item_index,
            )
            phases.append(phase_entry)
            total_batches += phase_batches
            completed_items += phase_completed
            skipped_items += phase_skipped

        execution_log = {
            "project_name": manifest.get("project_name", ""),
            "consumer_name": manifest.get("consumer_name", ""),
            "run_mode": "dry_run",
            "phases": phases,
            "summary": {
                "total_phases": len(phases),
                "total_batches": total_batches,
                "total_items": completed_items + skipped_items,
                "completed_items": completed_items,
                "skipped_items": skipped_items,
            },
        }

        artifact_path = save_json_artifact(execution_log, "execution_log.json")
        self.logger.info("Saved execution log to %s", artifact_path)
        return execution_log
