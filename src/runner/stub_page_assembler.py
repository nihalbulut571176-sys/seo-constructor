import json
from pathlib import Path
from typing import Any

from config import Settings
from src.tools.file_store import ensure_directory, save_json_artifact
from src.utils.logger import get_logger


class StubPageAssembler:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = get_logger(__name__, settings.log_level)

    def load_json(self, filepath: str) -> dict[str, Any]:
        with Path(filepath).open("r", encoding="utf-8") as file:
            return json.load(file)

    def load_section_stub(self, filepath: str) -> dict[str, Any]:
        return self.load_json(filepath)

    def get_section_output_path(self, page_slug: str, section_name: str) -> Path:
        return Path(self.settings.outputs_dir) / "sections" / page_slug / f"{section_name}.json"

    def get_page_notes(self, assembly_status: str) -> list[str]:
        notes_map = {
            "complete": ["All required section stubs assembled."],
            "partial": ["Some required section stubs are missing."],
            "missing": ["No section stubs found for this page."],
        }
        return notes_map.get(assembly_status, [])

    def build_section_entry(self, page_slug: str, section_name: str) -> tuple[dict[str, Any], bool]:
        filepath = self.get_section_output_path(page_slug, section_name)
        if filepath.exists():
            stub_data = self.load_section_stub(str(filepath))
            content_stub = stub_data.get("content_stub", {})
            return (
                {
                    "section_name": section_name,
                    "filepath": str(filepath.resolve()),
                    "status": "assembled",
                    "headline": content_stub.get("headline", ""),
                    "subheadline": content_stub.get("subheadline", ""),
                    "bullet_points": content_stub.get("bullet_points", []),
                    "cta_label": content_stub.get("cta_label", ""),
                },
                True,
            )

        return (
            {
                "section_name": section_name,
                "filepath": "",
                "status": "missing_stub",
                "headline": "",
                "subheadline": "",
                "bullet_points": [],
                "cta_label": "",
            },
            False,
        )

    def get_assembly_status(self, found_count: int, total_count: int) -> str:
        if total_count == 0 or found_count == 0:
            return "missing"
        if found_count == total_count:
            return "complete"
        return "partial"

    def run(self) -> dict[str, Any]:
        blueprints_path = Path(self.settings.artifacts_dir) / "page_blueprints.json"
        output_index_path = Path(self.settings.artifacts_dir) / "output_index.json"

        self.logger.info("Loading page blueprints from %s", blueprints_path)
        page_blueprints = self.load_json(str(blueprints_path))
        self.logger.info("Loading output index from %s", output_index_path)
        self.load_json(str(output_index_path))

        pages_dir = ensure_directory(str(Path(self.settings.outputs_dir) / "pages"))
        page_entries = []

        for page in page_blueprints.get("pages", []):
            page_slug = str(page.get("slug", ""))
            required_sections = page.get("required_sections", [])
            sections = []
            found_count = 0

            for section_name in required_sections:
                section_entry, found = self.build_section_entry(page_slug, section_name)
                sections.append(section_entry)
                if found:
                    found_count += 1

            assembly_status = self.get_assembly_status(found_count, len(required_sections))
            page_payload = {
                "page_slug": page_slug,
                "page_type": page.get("page_type", ""),
                "title_hint": page.get("title_hint", ""),
                "priority_tier": page.get("priority_tier", ""),
                "build_priority": page.get("build_priority", ""),
                "primary_goal": page.get("primary_goal", ""),
                "target_cluster_names": page.get("target_cluster_names", []),
                "target_keywords": page.get("target_keywords", []),
                "relevant_pain_groups": page.get("relevant_pain_groups", []),
                "seo_notes": page.get("seo_notes", []),
                "coverage_status": page.get("coverage_status", ""),
                "required_sections": required_sections,
                "sections": sections,
                "assembly_status": assembly_status,
                "notes": self.get_page_notes(assembly_status),
            }

            filepath = pages_dir / f"{page_slug}.json"
            with filepath.open("w", encoding="utf-8") as file:
                json.dump(page_payload, file, indent=2, ensure_ascii=False)

            page_entries.append(
                {
                    "page_slug": page_slug,
                    "page_type": page.get("page_type", ""),
                    "assembly_status": assembly_status,
                    "filepath": str(filepath.resolve()),
                }
            )

        page_output_index = {
            "project_name": page_blueprints.get("project_name", ""),
            "total_pages": len(page_entries),
            "complete_pages": sum(1 for page in page_entries if page["assembly_status"] == "complete"),
            "partial_pages": sum(1 for page in page_entries if page["assembly_status"] == "partial"),
            "missing_pages": sum(1 for page in page_entries if page["assembly_status"] == "missing"),
            "pages": page_entries,
        }
        artifact_path = save_json_artifact(page_output_index, "page_output_index.json")
        self.logger.info("Saved page output index to %s", artifact_path)
        return page_output_index
