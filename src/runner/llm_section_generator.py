import json
from pathlib import Path
from typing import Any
from urllib import error, request

from config import Settings
from src.tools.file_store import ensure_directory, save_json_artifact
from src.utils.logger import get_logger


class LLMSectionGenerator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = get_logger(__name__, settings.log_level)

    def load_json(self, filepath: str) -> dict[str, Any]:
        with Path(filepath).open("r", encoding="utf-8") as file:
            return json.load(file)

    def save_artifacts(
        self,
        generated_output_index: dict[str, Any],
        generation_log: dict[str, Any],
    ) -> dict[str, Any]:
        generated_index_path = save_json_artifact(
            generated_output_index,
            "generated_output_index.json",
        )
        generation_log_path = save_json_artifact(
            generation_log,
            "llm_generation_log.json",
        )
        self.logger.info("Saved generated output index to %s", generated_index_path)
        self.logger.info("Saved llm generation log to %s", generation_log_path)
        return {
            "generated_output_index": generated_output_index,
            "llm_generation_log": generation_log,
        }

    def is_generation_enabled(self) -> bool:
        return bool(self.settings.enable_llm_generation and self.settings.openai_api_key)

    def build_item_index(self, content_input_queue: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {
            str(item.get("item_id", "")): item
            for item in content_input_queue.get("items", [])
        }

    def get_items_for_batch(
        self,
        batch: dict[str, Any],
        content_items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        priority = str(batch.get("priority", ""))
        page_type = str(batch.get("page_type", ""))
        return [
            item
            for item in content_items
            if item.get("ready") is True
            and str(item.get("priority", "")) == priority
            and str(item.get("page_type", "")) == page_type
        ]

    def select_target_items(
        self,
        generation_manifest: dict[str, Any],
        content_input_queue: dict[str, Any],
    ) -> tuple[str, list[dict[str, Any]]]:
        content_items = content_input_queue.get("items", [])
        batches = generation_manifest.get("batches", [])
        batch_index = {
            str(batch.get("batch_id", "")): batch
            for batch in batches
        }

        target_batch_id = self.settings.llm_target_batch
        target_batch = batch_index.get(target_batch_id)
        max_items = max(1, self.settings.llm_max_items)

        if target_batch:
            selected_items = self.get_items_for_batch(target_batch, content_items)
            return target_batch_id, selected_items[:max_items]

        fallback_phase = next(
            (
                phase
                for phase in generation_manifest.get("phases", [])
                if phase.get("phase_name") == "phase_1_foundation_high"
            ),
            {},
        )

        fallback_items: list[dict[str, Any]] = []
        for batch_id in fallback_phase.get("batch_ids", []):
            batch = batch_index.get(str(batch_id))
            if not batch or batch.get("ready") is not True:
                continue
            fallback_items.extend(self.get_items_for_batch(batch, content_items))

        fallback_limit = min(3, max_items)
        return "phase_1_foundation_high:fallback", fallback_items[:fallback_limit]

    def build_response_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "headline": {"type": "string"},
                "subheadline": {"type": "string"},
                "body_paragraphs": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "bullet_points": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "cta_label": {"type": "string"},
            },
            "required": [
                "headline",
                "subheadline",
                "body_paragraphs",
                "bullet_points",
                "cta_label",
            ],
            "additionalProperties": False,
        }

    def build_prompt(
        self,
        item: dict[str, Any],
        project_language: str,
    ) -> list[dict[str, str]]:
        payload = item.get("content_payload", {})
        system_prompt = (
            "You write safe website section copy. "
            "Return only valid JSON that matches the requested schema. "
            "Do not invent facts, testimonials, guarantees, licenses, pricing, "
            "or unverifiable claims. Keep tone neutral, helpful, and concise. "
            "Do not overstuff keywords."
        )
        user_prompt = json.dumps(
            {
                "task": "Generate one website section content object.",
                "language": project_language,
                "page_slug": item.get("page_slug", ""),
                "page_type": item.get("page_type", ""),
                "section_name": item.get("section_name", ""),
                "primary_goal": payload.get("primary_goal", ""),
                "target_keywords": payload.get("target_keywords", []),
                "pain_points": payload.get("pain_points", []),
                "desired_outcomes": payload.get("desired_outcomes", []),
                "seo_notes": payload.get("seo_notes", []),
                "content_requirements": payload.get("content_requirements", []),
                "section_focus": payload.get("section_focus", ""),
                "cta_intent": payload.get("cta_intent", ""),
                "rules": [
                    "Write in the project language.",
                    "Keep the content safe and generic.",
                    "Do not fabricate company-specific facts.",
                    "CTA must align with cta_intent.",
                    "Return strict JSON only.",
                ],
                "output_format": {
                    "headline": "string",
                    "subheadline": "string",
                    "body_paragraphs": ["string"],
                    "bullet_points": ["string"],
                    "cta_label": "string",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def extract_message_content(self, response_data: dict[str, Any]) -> str:
        choices = response_data.get("choices", [])
        if not choices:
            return ""

        message = choices[0].get("message", {})
        content = message.get("content", "")

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    text_value = item.get("text")
                    if text_value:
                        text_parts.append(str(text_value))
            return "".join(text_parts)

        return ""

    def request_generation(self, item: dict[str, Any], project_language: str) -> dict[str, Any]:
        payload = {
            "model": self.settings.openai_model,
            "messages": self.build_prompt(item, project_language),
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "section_content",
                    "strict": True,
                    "schema": self.build_response_schema(),
                },
            },
        }

        http_request = request.Request(
            url="https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with request.urlopen(http_request, timeout=90) as response:
            response_data = json.load(response)

        response_text = self.extract_message_content(response_data)
        return json.loads(response_text)

    def validate_generated_content(self, data: dict[str, Any]) -> bool:
        required_string_fields = ["headline", "subheadline", "cta_label"]
        required_list_fields = ["body_paragraphs", "bullet_points"]

        if not isinstance(data, dict):
            return False

        for field in required_string_fields:
            if not isinstance(data.get(field), str):
                return False

        for field in required_list_fields:
            value = data.get(field)
            if not isinstance(value, list):
                return False
            if not all(isinstance(item, str) for item in value):
                return False

        return True

    def write_generated_section(
        self,
        item: dict[str, Any],
        generated_content: dict[str, Any],
    ) -> str:
        page_slug = str(item.get("page_slug", ""))
        section_name = str(item.get("section_name", ""))

        base_dir = ensure_directory(str(Path(self.settings.outputs_dir) / "generated_sections"))
        page_dir = ensure_directory(str(base_dir / page_slug))
        output_path = page_dir / f"{section_name}.json"

        output_payload = {
            "item_id": item.get("item_id", ""),
            "page_slug": page_slug,
            "page_type": item.get("page_type", ""),
            "section_name": section_name,
            "priority": item.get("priority", ""),
            "generation_mode": "llm_section_generation",
            "status": "generated",
            "model": self.settings.openai_model,
            "generated_content": generated_content,
            "source_payload": item.get("content_payload", {}),
        }

        with output_path.open("w", encoding="utf-8") as file:
            json.dump(output_payload, file, indent=2, ensure_ascii=False)

        return str(output_path.resolve())

    def build_disabled_result(
        self,
        project_name: str,
        reason: str,
    ) -> dict[str, Any]:
        generated_output_index = {
            "project_name": project_name,
            "generation_enabled": False,
            "target_batch": self.settings.llm_target_batch,
            "processed_items": 0,
            "generated_files": 0,
            "failed_items": 0,
            "outputs": [],
        }
        generation_log = {
            "project_name": project_name,
            "run_mode": "disabled",
            "target_batch": self.settings.llm_target_batch,
            "items": [],
            "summary": {
                "processed_items": 0,
                "generated_items": 0,
                "failed_items": 0,
                "skipped_items": 0,
            },
            "message": reason,
        }
        return self.save_artifacts(generated_output_index, generation_log)

    def run(self) -> dict[str, Any]:
        project_package_path = Path(self.settings.artifacts_dir) / "project_package.json"
        project_name = ""
        if project_package_path.exists():
            project_name = self.load_json(str(project_package_path)).get("project_name", "")

        if not self.settings.enable_llm_generation:
            self.logger.info("LLM generation is disabled by configuration.")
            return self.build_disabled_result(project_name, "LLM generation disabled by configuration.")

        if not self.settings.openai_api_key:
            self.logger.info("LLM generation skipped because OPENAI_API_KEY is missing.")
            return self.build_disabled_result(project_name, "OPENAI_API_KEY is not configured.")

        generation_manifest_path = Path(self.settings.artifacts_dir) / "generation_manifest.json"
        content_input_queue_path = Path(self.settings.artifacts_dir) / "content_input_queue.json"
        project_package_path = Path(self.settings.artifacts_dir) / "project_package.json"

        generation_manifest = self.load_json(str(generation_manifest_path))
        content_input_queue = self.load_json(str(content_input_queue_path))
        project_package = self.load_json(str(project_package_path))

        target_batch, selected_items = self.select_target_items(
            generation_manifest,
            content_input_queue,
        )

        project_name = project_package.get("project_name", "")
        project_language = str(project_package.get("input_data", {}).get("language", "en"))
        log_items: list[dict[str, Any]] = []
        outputs: list[dict[str, Any]] = []

        processed_items = 0
        generated_items = 0
        failed_items = 0
        skipped_items = 0

        if not selected_items:
            generation_log = {
                "project_name": project_name,
                "run_mode": "live",
                "target_batch": target_batch,
                "items": [],
                "summary": {
                    "processed_items": 0,
                    "generated_items": 0,
                    "failed_items": 0,
                    "skipped_items": 0,
                },
                "message": "No ready items matched the configured batch selection.",
            }
            generated_output_index = {
                "project_name": project_name,
                "generation_enabled": True,
                "target_batch": target_batch,
                "processed_items": 0,
                "generated_files": 0,
                "failed_items": 0,
                "outputs": [],
            }
            return self.save_artifacts(generated_output_index, generation_log)

        for item in selected_items:
            item_id = str(item.get("item_id", ""))
            page_slug = str(item.get("page_slug", ""))
            section_name = str(item.get("section_name", ""))

            if item.get("ready") is not True:
                skipped_items += 1
                log_items.append(
                    {
                        "item_id": item_id,
                        "page_slug": page_slug,
                        "section_name": section_name,
                        "status": "skipped",
                        "message": "Item skipped because it is not ready.",
                    }
                )
                continue

            processed_items += 1
            try:
                generated_content = self.request_generation(item, project_language)
                if not self.validate_generated_content(generated_content):
                    failed_items += 1
                    log_items.append(
                        {
                            "item_id": item_id,
                            "page_slug": page_slug,
                            "section_name": section_name,
                            "status": "failed_generation",
                            "message": "Model response was invalid or incomplete JSON.",
                        }
                    )
                    continue

                filepath = self.write_generated_section(item, generated_content)
                generated_items += 1
                outputs.append(
                    {
                        "item_id": item_id,
                        "page_slug": page_slug,
                        "section_name": section_name,
                        "filepath": filepath,
                        "status": "generated",
                    }
                )
                log_items.append(
                    {
                        "item_id": item_id,
                        "page_slug": page_slug,
                        "section_name": section_name,
                        "status": "generated",
                        "message": "Generated section content and wrote output file.",
                    }
                )
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                failed_items += 1
                log_items.append(
                    {
                        "item_id": item_id,
                        "page_slug": page_slug,
                        "section_name": section_name,
                        "status": "failed_generation",
                        "message": f"Failed to parse model output: {exc}",
                    }
                )
            except error.HTTPError as exc:
                failed_items += 1
                response_body = exc.read().decode("utf-8", errors="ignore")
                log_items.append(
                    {
                        "item_id": item_id,
                        "page_slug": page_slug,
                        "section_name": section_name,
                        "status": "failed_generation",
                        "message": f"OpenAI API request failed with status {exc.code}: {response_body}",
                    }
                )
            except Exception as exc:
                failed_items += 1
                log_items.append(
                    {
                        "item_id": item_id,
                        "page_slug": page_slug,
                        "section_name": section_name,
                        "status": "failed_generation",
                        "message": f"Unexpected generation failure: {exc}",
                    }
                )

        generated_output_index = {
            "project_name": project_name,
            "generation_enabled": True,
            "target_batch": target_batch,
            "processed_items": processed_items,
            "generated_files": generated_items,
            "failed_items": failed_items,
            "outputs": outputs,
        }
        generation_log = {
            "project_name": project_name,
            "run_mode": "live",
            "target_batch": target_batch,
            "items": log_items,
            "summary": {
                "processed_items": processed_items,
                "generated_items": generated_items,
                "failed_items": failed_items,
                "skipped_items": skipped_items,
            },
        }
        return self.save_artifacts(generated_output_index, generation_log)
