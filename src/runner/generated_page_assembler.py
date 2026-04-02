import json
from pathlib import Path
from typing import Any

from config import Settings
from src.tools.file_store import ensure_directory, save_json_artifact
from src.utils.logger import get_logger


class GeneratedPageAssembler:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = get_logger(__name__, settings.log_level)

    def load_json(self, filepath: str) -> dict[str, Any]:
        with Path(filepath).open("r", encoding="utf-8") as file:
            return json.load(file)

    def maybe_load_json(self, filepath: Path) -> dict[str, Any]:
        if filepath.exists():
            return self.load_json(str(filepath))
        return {}

    def get_generated_section_path(self, page_slug: str, section_name: str) -> Path:
        return Path(self.settings.outputs_dir) / "generated_sections" / page_slug / f"{section_name}.json"

    def get_stub_section_path(self, page_slug: str, section_name: str) -> Path:
        return Path(self.settings.outputs_dir) / "sections" / page_slug / f"{section_name}.json"

    def build_generated_entry(self, filepath: Path, section_name: str) -> dict[str, Any]:
        generated_data = self.load_json(str(filepath))
        generated_content = generated_data.get("generated_content", {})
        return {
            "section_name": section_name,
            "source_type": "generated",
            "filepath": str(filepath.resolve()),
            "status": "assembled_generated",
            "headline": generated_content.get("headline", ""),
            "subheadline": generated_content.get("subheadline", ""),
            "body_paragraphs": generated_content.get("body_paragraphs", []),
            "bullet_points": generated_content.get("bullet_points", []),
            "cta_label": generated_content.get("cta_label", ""),
        }

    def build_stub_entry(self, filepath: Path, section_name: str) -> dict[str, Any]:
        stub_data = self.load_json(str(filepath))
        content_stub = stub_data.get("content_stub", {})
        return {
            "section_name": section_name,
            "source_type": "stub",
            "filepath": str(filepath.resolve()),
            "status": "assembled_stub",
            "headline": content_stub.get("headline", ""),
            "subheadline": content_stub.get("subheadline", ""),
            "body_paragraphs": [],
            "bullet_points": content_stub.get("bullet_points", []),
            "cta_label": content_stub.get("cta_label", ""),
        }

    def build_missing_entry(self, section_name: str) -> dict[str, Any]:
        return {
            "section_name": section_name,
            "source_type": "missing",
            "filepath": "",
            "status": "missing_section",
            "headline": "",
            "subheadline": "",
            "body_paragraphs": [],
            "bullet_points": [],
            "cta_label": "",
        }

    def build_section_entry(self, page_slug: str, section_name: str) -> dict[str, Any]:
        generated_path = self.get_generated_section_path(page_slug, section_name)
        if generated_path.exists():
            return self.build_generated_entry(generated_path, section_name)

        stub_path = self.get_stub_section_path(page_slug, section_name)
        if stub_path.exists():
            return self.build_stub_entry(stub_path, section_name)

        return self.build_missing_entry(section_name)

    def get_assembly_status(self, sections: list[dict[str, Any]]) -> str:
        if not sections:
            return "missing"

        generated_count = sum(1 for section in sections if section["source_type"] == "generated")
        stub_count = sum(1 for section in sections if section["source_type"] == "stub")
        missing_count = sum(1 for section in sections if section["source_type"] == "missing")

        if generated_count == len(sections):
            return "generated_complete"
        if missing_count == 0 and generated_count > 0 and stub_count > 0:
            return "mixed_fallback"
        if missing_count == 0 and stub_count == len(sections):
            return "stub_only"
        if missing_count < len(sections):
            return "partial"
        return "missing"

    def get_page_notes(self, assembly_status: str) -> list[str]:
        notes_map = {
            "generated_complete": ["All required sections assembled from generated outputs."],
            "mixed_fallback": [
                "Generated outputs used where available; remaining sections assembled from stub outputs."
            ],
            "stub_only": ["No generated outputs found; page assembled fully from stub outputs."],
            "partial": ["Some required sections are missing."],
            "missing": ["No section outputs found for this page."],
        }
        return notes_map.get(assembly_status, [])

    def run(self) -> dict[str, Any]:
        blueprints_path = Path(self.settings.artifacts_dir) / "page_blueprints.json"
        output_index_path = Path(self.settings.artifacts_dir) / "output_index.json"
        generated_output_index_path = Path(self.settings.artifacts_dir) / "generated_output_index.json"

        self.logger.info("Loading page blueprints from %s", blueprints_path)
        page_blueprints = self.load_json(str(blueprints_path))
        self.logger.info("Loading stub output index from %s", output_index_path)
        self.load_json(str(output_index_path))
        if generated_output_index_path.exists():
            self.logger.info("Loading generated output index from %s", generated_output_index_path)
            self.load_json(str(generated_output_index_path))

        pages_dir = ensure_directory(str(Path(self.settings.outputs_dir) / "generated_pages"))
        page_entries = []

        for page in page_blueprints.get("pages", []):
            page_slug = str(page.get("slug", ""))
            required_sections = [str(section) for section in page.get("required_sections", [])]
            sections = [
                self.build_section_entry(page_slug, section_name)
                for section_name in required_sections
            ]

            assembly_status = self.get_assembly_status(sections)
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

        generated_page_output_index = {
            "project_name": page_blueprints.get("project_name", ""),
            "total_pages": len(page_entries),
            "generated_complete_pages": sum(
                1 for page in page_entries if page["assembly_status"] == "generated_complete"
            ),
            "mixed_fallback_pages": sum(
                1 for page in page_entries if page["assembly_status"] == "mixed_fallback"
            ),
            "stub_only_pages": sum(
                1 for page in page_entries if page["assembly_status"] == "stub_only"
            ),
            "partial_pages": sum(1 for page in page_entries if page["assembly_status"] == "partial"),
            "missing_pages": sum(1 for page in page_entries if page["assembly_status"] == "missing"),
            "pages": page_entries,
        }
        artifact_path = save_json_artifact(
            generated_page_output_index,
            "generated_page_output_index.json",
        )
        self.logger.info("Saved generated page output index to %s", artifact_path)
        return generated_page_output_index
