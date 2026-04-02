import json
from pathlib import Path
from typing import Any

from config import Settings
from src.tools.file_store import ensure_directory, save_json_artifact
from src.utils.logger import get_logger


class StubSiteAssembler:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = get_logger(__name__, settings.log_level)

    def load_json(self, filepath: str) -> dict[str, Any]:
        with Path(filepath).open("r", encoding="utf-8") as file:
            return json.load(file)

    def get_site_notes(self, complete_pages: int, partial_pages: int, missing_pages: int) -> list[str]:
        if missing_pages > 0:
            return ["Some pages are missing from the site snapshot."]
        if partial_pages > 0:
            return ["Some pages are only partially assembled."]
        if complete_pages > 0:
            return ["All page-level outputs assembled into site snapshot."]
        return []

    def run(self) -> dict[str, Any]:
        page_output_index_path = Path(self.settings.artifacts_dir) / "page_output_index.json"
        project_package_path = Path(self.settings.artifacts_dir) / "project_package.json"

        self.logger.info("Loading page output index from %s", page_output_index_path)
        page_output_index = self.load_json(str(page_output_index_path))
        self.logger.info("Loading project package from %s", project_package_path)
        project_package = self.load_json(str(project_package_path))

        pages = []
        page_order = []

        for page_entry in page_output_index.get("pages", []):
            filepath = str(page_entry.get("filepath", ""))
            if not filepath:
                continue

            page_data = self.load_json(filepath)
            page_order.append(page_data.get("page_slug", ""))
            pages.append(
                {
                    "page_slug": page_data.get("page_slug", ""),
                    "page_type": page_data.get("page_type", ""),
                    "title_hint": page_data.get("title_hint", ""),
                    "priority_tier": page_data.get("priority_tier", ""),
                    "build_priority": page_data.get("build_priority", ""),
                    "assembly_status": page_data.get("assembly_status", ""),
                    "required_sections": page_data.get("required_sections", []),
                    "sections": page_data.get("sections", []),
                    "seo_notes": page_data.get("seo_notes", []),
                    "target_keywords": page_data.get("target_keywords", []),
                    "relevant_pain_groups": page_data.get("relevant_pain_groups", []),
                }
            )

        complete_pages = sum(1 for page in pages if page["assembly_status"] == "complete")
        partial_pages = sum(1 for page in pages if page["assembly_status"] == "partial")
        missing_pages = sum(1 for page in pages if page["assembly_status"] == "missing")
        total_sections = sum(len(page.get("sections", [])) for page in pages)

        input_data = project_package.get("input_data", {})
        site_snapshot = {
            "project_name": project_package.get("project_name", ""),
            "city": input_data.get("city", ""),
            "niche": input_data.get("niche", ""),
            "site_type": input_data.get("site_type", ""),
            "language": input_data.get("language", ""),
            "total_pages": len(pages),
            "page_order": page_order,
            "pages": pages,
            "summary": {
                "complete_pages": complete_pages,
                "partial_pages": partial_pages,
                "missing_pages": missing_pages,
                "total_sections": total_sections,
            },
            "notes": self.get_site_notes(complete_pages, partial_pages, missing_pages),
        }

        site_dir = ensure_directory(str(Path(self.settings.outputs_dir) / "site"))
        site_snapshot_path = Path(site_dir) / "site_snapshot.json"
        with site_snapshot_path.open("w", encoding="utf-8") as file:
            json.dump(site_snapshot, file, indent=2, ensure_ascii=False)

        site_output_index = {
            "project_name": project_package.get("project_name", ""),
            "site_snapshot_filepath": str(site_snapshot_path.resolve()),
            "total_pages": len(pages),
            "complete_pages": complete_pages,
            "partial_pages": partial_pages,
            "missing_pages": missing_pages,
        }
        artifact_path = save_json_artifact(site_output_index, "site_output_index.json")
        self.logger.info("Saved site output index to %s", artifact_path)
        return {
            "site_snapshot": site_snapshot,
            "site_output_index": site_output_index,
        }
