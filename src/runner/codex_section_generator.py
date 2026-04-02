import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from config import Settings
from src.tools.file_store import ensure_directory, save_json_artifact
from src.utils.logger import get_logger


class CodexSectionGenerator:
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
        generation_debug: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        generated_index_path = save_json_artifact(
            generated_output_index,
            "generated_output_index.json",
        )
        generation_log_path = save_json_artifact(
            generation_log,
            "codex_generation_log.json",
        )
        debug_path = ""
        if generation_debug is not None:
            debug_path = save_json_artifact(
                generation_debug,
                "codex_generation_debug.json",
            )
        self.logger.info("Saved generated output index to %s", generated_index_path)
        self.logger.info("Saved codex generation log to %s", generation_log_path)
        if debug_path:
            self.logger.info("Saved codex generation debug to %s", debug_path)
        return {
            "generated_output_index": generated_output_index,
            "codex_generation_log": generation_log,
            "codex_generation_debug": generation_debug or {},
        }

    def build_result(
        self,
        project_name: str,
        run_mode: str,
        target_batch: str,
        message: str,
        outputs: list[dict[str, Any]] | None = None,
        processed_items: int = 0,
        generated_items: int = 0,
        failed_items: int = 0,
        skipped_items: int = 0,
        item_logs: list[dict[str, Any]] | None = None,
        debug_items: list[dict[str, Any]] | None = None,
        generation_enabled: bool = False,
    ) -> dict[str, Any]:
        generated_output_index = {
            "project_name": project_name,
            "generation_enabled": generation_enabled,
            "generator_type": "codex_exec",
            "target_batch": target_batch,
            "processed_items": processed_items,
            "generated_files": generated_items,
            "failed_items": failed_items,
            "outputs": outputs or [],
        }
        generation_log = {
            "project_name": project_name,
            "run_mode": run_mode,
            "target_batch": target_batch,
            "items": item_logs or [],
            "summary": {
                "processed_items": processed_items,
                "generated_items": generated_items,
                "failed_items": failed_items,
                "skipped_items": skipped_items,
            },
            "message": message,
        }
        generation_debug = {
            "project_name": project_name,
            "items": debug_items or [],
        }
        return self.save_artifacts(generated_output_index, generation_log, generation_debug)

    def resolve_executable(self) -> str | None:
        return shutil.which(self.settings.codex_executable)

    def is_cli_available(self, executable_path: str) -> bool:
        try:
            result = subprocess.run(
                [executable_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                cwd=self.settings.outputs_dir,
            )
        except (FileNotFoundError, PermissionError, OSError, subprocess.TimeoutExpired):
            return False

        return result.returncode == 0

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

    def has_generated_output(self, item: dict[str, Any]) -> bool:
        output_path = self.get_generated_section_output_path(item)
        if not output_path.exists():
            return False

        if self.is_generated_output_usable(item, output_path):
            return True

        self.remove_generated_section_if_exists(item)
        return False

    def get_pending_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [item for item in items if not self.has_generated_output(item)]

    def build_page_order_index(self, execution_plan: dict[str, Any]) -> dict[str, int]:
        page_order: dict[str, int] = {}
        for step in execution_plan.get("build_sequence", []):
            page_slug = str(step.get("page_slug", ""))
            step_number = int(step.get("step_number", 0))
            if page_slug:
                page_order[page_slug] = step_number
        return page_order

    def select_target_items(
        self,
        generation_manifest: dict[str, Any],
        content_input_queue: dict[str, Any],
        execution_plan: dict[str, Any],
    ) -> tuple[str, list[dict[str, Any]]]:
        content_items = content_input_queue.get("items", [])
        batches = generation_manifest.get("batches", [])
        batch_index = {
            str(batch.get("batch_id", "")): batch
            for batch in batches
        }
        page_order_index = self.build_page_order_index(execution_plan)

        target_batch_id = self.settings.codex_target_batch
        target_batch = batch_index.get(target_batch_id)
        max_items = max(1, self.settings.codex_max_items)

        if target_batch:
            selected_items = self.get_pending_items(self.get_items_for_batch(target_batch, content_items))
            if selected_items:
                return target_batch_id, selected_items[:max_items]

        for phase in generation_manifest.get("phases", []):
            phase_name = str(phase.get("phase_name", ""))
            phase_items: list[dict[str, Any]] = []
            for batch_id in phase.get("batch_ids", []):
                batch = batch_index.get(str(batch_id))
                if not batch or batch.get("ready") is not True:
                    continue
                phase_items.extend(self.get_pending_items(self.get_items_for_batch(batch, content_items)))

            sorted_phase_items = sorted(
                phase_items,
                key=lambda item: (
                    page_order_index.get(str(item.get("page_slug", "")), 10_000),
                    str(item.get("page_slug", "")),
                    str(item.get("section_name", "")),
                ),
            )

            if not sorted_phase_items:
                continue

            next_page_slug = str(sorted_phase_items[0].get("page_slug", ""))
            next_page_items = [
                item for item in sorted_phase_items if str(item.get("page_slug", "")) == next_page_slug
            ]
            return f"{phase_name}:{next_page_slug}", next_page_items[:max_items]

        return "generation_manifest:fallback", []

    def get_cta_examples_for_intent(self, cta_intent: str) -> list[str]:
        examples_map = {
            "contact_now": [
                "Contact Us",
                "Request Service",
                "Call Now",
                "Book Service",
                "Schedule Service",
            ],
            "explore_services": [
                "View Services",
                "Explore Services",
                "See Services",
                "Browse Services",
                "Our Services",
            ],
            "learn_more": [
                "Learn More",
                "Read More",
                "How It Works",
            ],
            "build_trust": [
                "Why Choose Us",
                "See Why",
                "About Our Team",
            ],
            "confirm_local_fit": [
                "Check Availability",
                "Check Service Area",
                "See If We Serve Your Area",
            ],
            "reduce_friction": [
                "Get Answers",
                "See FAQ",
                "Read FAQ",
            ],
        }
        return examples_map.get(cta_intent, [])

    def get_section_prompt_guidance(self, section_name: str) -> str:
        guidance_map = {
            "hero": (
                "This is a local service hero section. "
                "Lead with local service relevance and a direct conversion CTA."
            ),
            "services_overview": (
                "This is a services overview section, not a hero and not a contact block. "
                "It should summarize available plumbing services and use a service-discovery CTA. "
                "Do not use contact, call, request, book, or schedule CTAs here."
            ),
            "service_description": (
                "This section should explain service scope for a local plumbing service page. "
                "Describe what kinds of jobs are handled, who the service is for, and why it is locally relevant. "
                "Use a service-discovery CTA, not a contact-first CTA."
            ),
            "benefits": (
                "This section should explain practical service benefits and trust-building value. "
                "Focus on outcomes, reassurance, workmanship, response, and pricing clarity. "
                "Do not turn it into a hero or direct booking block."
            ),
            "local_relevance": (
                "This section should prove that the business serves the specific local area. "
                "Mention the neighborhood or area naturally, explain local coverage relevance, "
                "and use a local-fit CTA such as availability or coverage confirmation. "
                "Mention the exact area name in visible copy, write 3 to 5 short natural-language bullets, "
                "and never output JSON-like strings, field names, or meta instructions."
            ),
            "service_summary": (
                "This section should summarize the main plumbing services offered in the specific local area. "
                "Combine service wording with local coverage wording, and use a local-fit CTA rather than a direct contact CTA."
            ),
            "trust_signals": (
                "This section should emphasize trust, reliability, professionalism, and local credibility."
            ),
            "faq_preview": (
                "This section should preview common questions and reduce hesitation with FAQ-style wording. "
                "Use natural-language FAQ teaser copy only. "
                "Do not serialize JSON, do not output question-answer objects, "
                "and do not leave body paragraphs or the CTA empty. "
                "Write exactly 2 short body paragraphs and 4 to 6 plain-language FAQ teaser bullets. "
                "Make the bullets read like natural customer questions, not answers or JSON fields."
            ),
            "contact_cta": (
                "This is a conversion CTA section. "
                "Use direct contact-oriented wording and a clear action CTA."
            ),
        }
        return guidance_map.get(section_name, "")

    def try_repair_generated_content(
        self,
        item: dict[str, Any],
        generated_content: dict[str, Any],
        quality_result: dict[str, Any],
    ) -> tuple[dict[str, Any], bool, str]:
        section_name = str(item.get("section_name", ""))
        reasons = quality_result.get("reasons", [])

        if section_name == "services_overview" and reasons == ["cta_intent_mismatch"]:
            repaired_content = dict(generated_content)
            repaired_content["cta_label"] = "View Services"
            return repaired_content, True, "services_overview_cta_normalized"

        if section_name == "service_description" and reasons == ["cta_intent_mismatch"]:
            repaired_content = dict(generated_content)
            repaired_content["cta_label"] = "View Services"
            return repaired_content, True, "service_description_cta_normalized"

        if section_name == "benefits" and reasons == ["cta_intent_mismatch"]:
            repaired_content = dict(generated_content)
            repaired_content["cta_label"] = "Learn More"
            return repaired_content, True, "benefits_cta_normalized"

        if section_name in {"local_relevance", "service_summary"} and reasons == ["cta_intent_mismatch"]:
            repaired_content = dict(generated_content)
            repaired_content["cta_label"] = "Check Availability"
            return repaired_content, True, f"{section_name}_cta_normalized"

        if section_name == "faq_preview":
            repaired_content = self.repair_empty_faq_preview(item, generated_content)
            if repaired_content is not None:
                return repaired_content, True, "faq_preview_empty_output_repaired"

        if section_name == "contact_cta":
            repaired_content = self.repair_contact_cta_embedded_json(generated_content)
            if repaired_content is not None:
                return repaired_content, True, "contact_cta_embedded_json_repaired"

        if section_name == "local_relevance":
            repaired_content = self.repair_local_relevance_embedded_json(generated_content)
            if repaired_content is not None:
                return repaired_content, True, "local_relevance_embedded_json_repaired"

        return generated_content, False, ""

    def repair_empty_faq_preview(
        self,
        item: dict[str, Any],
        generated_content: dict[str, Any],
    ) -> dict[str, Any] | None:
        section_name = str(item.get("section_name", ""))
        if section_name != "faq_preview":
            return None

        headline = str(generated_content.get("headline", "")).strip()
        subheadline = str(generated_content.get("subheadline", "")).strip()
        body_paragraphs = [str(value).strip() for value in generated_content.get("body_paragraphs", [])]
        bullet_points = [str(value).strip() for value in generated_content.get("bullet_points", [])]
        cta_label = str(generated_content.get("cta_label", "")).strip()

        has_any_content = any(
            [
                headline,
                subheadline,
                cta_label,
                any(body_paragraphs),
                any(bullet_points),
            ]
        )
        if has_any_content:
            return None

        project_package_path = Path(self.settings.artifacts_dir) / "project_package.json"
        city = "the service area"
        niche = "local services"
        if project_package_path.exists():
            project_package = self.load_json(str(project_package_path))
            input_data = project_package.get("input_data", {})
            city = str(input_data.get("city", city))
            niche = str(input_data.get("niche", niche))

        payload = item.get("content_payload", {})
        primary_goal = str(payload.get("primary_goal", "")).strip()
        target_keywords = [str(value).strip() for value in payload.get("target_keywords", []) if str(value).strip()]
        primary_keyword = target_keywords[0] if target_keywords else f"{niche} in {city}"

        repaired_content = {
            "headline": f"{city} {niche.title()} FAQ",
            "subheadline": f"Quick answers about {primary_keyword.lower()}, scheduling, and service expectations in {city}.",
            "body_paragraphs": [
                f"People comparing {niche} in {city} often want clearer answers before they book. This FAQ preview helps reduce hesitation around scheduling, pricing, and what kinds of plumbing jobs are typically handled.",
                f"It supports service discovery by surfacing common questions early, so visitors can understand their options and decide whether the service is the right fit for their property and plumbing issue.",
            ],
            "bullet_points": [
                f"How quickly can I schedule {niche} in {city}?",
                f"What kinds of plumbing services are usually included?",
                "Do you provide estimates before work begins?",
                f"Can you help with urgent or same-day plumbing issues in {city}?",
                f"Do you serve my area within {city}?",
            ],
            "cta_label": "View All FAQs",
        }

        if not self.validate_generated_content(repaired_content):
            return None

        return repaired_content

    def build_prompt(
        self,
        item: dict[str, Any],
        project_language: str,
        is_retry: bool = False,
    ) -> str:
        payload = item.get("content_payload", {})
        niche = str(payload.get("target_keywords", [""])[0]).replace(str(item.get("page_slug", "")), "").strip()
        project_package_path = Path(self.settings.artifacts_dir) / "project_package.json"
        city = ""
        niche_value = ""
        if project_package_path.exists():
            project_package = self.load_json(str(project_package_path))
            input_data = project_package.get("input_data", {})
            city = str(input_data.get("city", ""))
            niche_value = str(input_data.get("niche", ""))

        prompt_data = {
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
        }
        cta_intent = str(payload.get("cta_intent", ""))
        cta_examples = self.get_cta_examples_for_intent(cta_intent)
        section_guidance = self.get_section_prompt_guidance(str(item.get("section_name", "")))
        retry_line = ""
        if is_retry:
            retry_line = (
                "Retry: the previous result did not match the expected section behavior or CTA intent. "
                "Be more concrete, local, and aligned to the section purpose.\n"
            )
        faq_shape_line = ""
        if str(item.get("section_name", "")) == "faq_preview":
            faq_shape_line = (
                "Output shape reminder for this FAQ preview: use 2 short body paragraphs, 4 to 6 FAQ-style bullet points, "
                "mention Austin or local plumbing relevance, and use a reduce-friction CTA such as View All FAQs or See FAQ.\n"
            )
        return (
            f"Return only one JSON object for a {item.get('section_name', '')} section "
            f"of a local {niche_value or 'service'} page in {city or 'the target city'}.\n"
            "Keep it neutral and safe.\n"
            "Do not invent facts.\n"
            "Use the provided context.\n"
            "Required fields: headline, subheadline, body_paragraphs, bullet_points, cta_label.\n"
            "No extra fields.\n"
            f"Language: {project_language}\n"
            f"Section guidance: {section_guidance}\n"
            f"CTA intent: {cta_intent}.\n"
            f"Preferred CTA examples: {', '.join(cta_examples) if cta_examples else 'Match the intent exactly'}.\n"
            f"{faq_shape_line}"
            f"{retry_line}"
            "Context:\n"
            f"{json.dumps(prompt_data, ensure_ascii=False, indent=2)}"
        )

    def build_output_schema(self) -> dict[str, Any]:
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

    def validate_generated_content(self, data: dict[str, Any]) -> bool:
        required_string_fields = ["headline", "subheadline", "cta_label"]
        required_list_fields = ["body_paragraphs", "bullet_points"]
        allowed_fields = set(required_string_fields + required_list_fields)

        if not isinstance(data, dict):
            return False

        if set(data.keys()) != allowed_fields:
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

    def normalize_text(self, value: str) -> str:
        normalized = value.lower()
        for char in [",", ".", "!", "?", ":", ";", "(", ")", "\"", "'", "\n", "\r", "/", "\\", "-"]:
            normalized = normalized.replace(char, " ")
        return " ".join(normalized.split())

    def contains_any_term(self, haystack: str, terms: list[str]) -> bool:
        normalized_haystack = self.normalize_text(haystack)
        for term in terms:
            normalized_term = self.normalize_text(str(term))
            if normalized_term and normalized_term in normalized_haystack:
                return True
        return False

    def normalize_cta_label(self, label: str) -> str:
        return self.normalize_text(label.strip())

    def contains_any_phrase(self, text: str, phrases: list[str]) -> bool:
        normalized_text = self.normalize_cta_label(text)
        for phrase in phrases:
            normalized_phrase = self.normalize_cta_label(phrase)
            if normalized_phrase and normalized_phrase in normalized_text:
                return True
        return False

    def matches_cta_intent(self, cta_label: str, cta_intent: str) -> bool:
        normalized_label = self.normalize_cta_label(cta_label)
        if not normalized_label:
            return False

        allowed_map = {
            "contact_now": [
                "contact",
                "contact us",
                "call",
                "call now",
                "call for service",
                "request service",
                "request help",
                "get help",
                "book service",
                "book now",
                "schedule service",
                "schedule plumbing service",
                "schedule now",
                "speak to a plumber",
                "talk to us",
            ],
            "explore_services": [
                "view services",
                "explore services",
                "our services",
                "see services",
                "browse services",
                "service options",
                "learn about services",
            ],
            "learn_more": [
                "learn more",
                "learn how",
                "see how it works",
                "how it works",
                "get started",
                "read more",
                "explore more",
            ],
            "build_trust": [
                "why choose us",
                "why us",
                "see why",
                "our approach",
                "our reputation",
                "about our team",
                "trust our team",
            ],
            "confirm_local_fit": [
                "check availability",
                "check service area",
                "confirm availability",
                "see if we serve your area",
                "service area",
                "check coverage",
            ],
            "reduce_friction": [
                "get answers",
                "see faq",
                "common questions",
                "ask a question",
                "learn more",
                "read faq",
                "view all faqs",
                "view faqs",
            ],
        }
        return self.contains_any_phrase(normalized_label, allowed_map.get(cta_intent, []))

    def is_cta_critical_section(self, section_name: str) -> bool:
        return section_name in {"hero", "services_overview", "contact_cta"}

    def detect_generic_copy(
        self,
        combined_text: str,
        has_context_relevance: bool,
    ) -> bool:
        generic_terms = [
            "feature",
            "product",
            "platform",
            "modern teams",
            "workflow",
            "dashboard",
            "automate",
            "automation",
            "software",
            "business",
            "productivity",
        ]
        return self.contains_any_term(combined_text, generic_terms) and not has_context_relevance

    def should_hard_fail_quality(
        self,
        section_name: str,
        reasons: list[str],
    ) -> bool:
        if self.is_cta_critical_section(section_name) and "cta_intent_mismatch" in reasons:
            return True

        return section_name == "contact_cta" and "contact_cta_empty_body" in reasons

    def is_json_like_string(self, value: str) -> bool:
        normalized = value.strip()
        return (
            normalized.startswith("{")
            and normalized.endswith("}")
        ) or (
            normalized.startswith("[")
            and normalized.endswith("]")
        )

    def has_non_empty_list_items(self, values: list[str]) -> bool:
        return any(str(value).strip() for value in values)

    def faq_preview_checks(
        self,
        body_paragraphs: list[str],
        bullet_points: list[str],
        cta_label: str,
    ) -> list[str]:
        failures: list[str] = []
        non_empty_bullets = [value for value in bullet_points if str(value).strip()]

        if not self.has_non_empty_list_items(body_paragraphs):
            failures.append("faq_preview_empty_body")
        if len(non_empty_bullets) < 3:
            failures.append("faq_preview_insufficient_bullets")
        if any(self.is_json_like_string(value) for value in non_empty_bullets):
            failures.append("faq_preview_json_blob_bullets")
        if any(not str(value).strip() for value in bullet_points):
            failures.append("faq_preview_empty_bullets")
        if not cta_label.strip():
            failures.append("faq_preview_empty_cta")

        return failures

    def service_description_checks(
        self,
        combined_text: str,
        body_paragraphs: list[str],
        bullet_points: list[str],
    ) -> list[str]:
        failures: list[str] = []
        scope_terms = [
            "repair",
            "repairs",
            "installation",
            "install",
            "drain",
            "leak",
            "pipe",
            "water heater",
            "toilet",
            "faucet",
            "plumbing",
        ]
        non_empty_bullets = [value for value in bullet_points if str(value).strip()]

        if not self.contains_any_term(combined_text, scope_terms):
            failures.append("service_description_missing_scope")
        if not self.has_non_empty_list_items(body_paragraphs):
            failures.append("service_description_empty_body")
        if len(non_empty_bullets) < 4:
            failures.append("service_description_insufficient_bullets")

        return failures

    def benefits_checks(
        self,
        combined_text: str,
        body_paragraphs: list[str],
        bullet_points: list[str],
    ) -> list[str]:
        failures: list[str] = []
        value_terms = [
            "upfront",
            "clear pricing",
            "reliable",
            "trusted",
            "licensed",
            "experienced",
            "same day",
            "durable",
            "quality",
            "clean",
            "communication",
            "dependable",
        ]
        non_empty_bullets = [value for value in bullet_points if str(value).strip()]

        if not self.contains_any_term(combined_text, value_terms):
            failures.append("benefits_missing_value_proof")
        if not self.has_non_empty_list_items(body_paragraphs):
            failures.append("benefits_empty_body")
        if len(non_empty_bullets) < 4:
            failures.append("benefits_insufficient_bullets")

        return failures

    def get_slug_terms(self, page_slug: str) -> list[str]:
        return [term for term in page_slug.replace("-", " ").split() if term]

    def local_relevance_checks(
        self,
        item: dict[str, Any],
        combined_text: str,
        body_paragraphs: list[str],
        bullet_points: list[str],
    ) -> list[str]:
        failures: list[str] = []
        local_terms = self.get_slug_terms(str(item.get("page_slug", "")))
        coverage_terms = [
            "local",
            "area",
            "neighborhood",
            "serve",
            "serving",
            "coverage",
            "available",
            "availability",
            "downtown",
            "north",
            "south",
            "austin",
        ]
        non_empty_bullets = [value for value in bullet_points if str(value).strip()]

        if not self.contains_any_term(combined_text, local_terms + coverage_terms):
            failures.append("local_relevance_missing_area_context")
        if not self.has_non_empty_list_items(body_paragraphs):
            failures.append("local_relevance_empty_body")
        if len(non_empty_bullets) < 3:
            failures.append("local_relevance_insufficient_bullets")
        if any(self.is_json_like_string(value) for value in body_paragraphs + non_empty_bullets):
            failures.append("local_relevance_json_like_copy")
        if self.contains_any_term(
            combined_text,
            ["json", "section id", "section type", "body paragraphs", "bullet points", "field"],
        ):
            failures.append("local_relevance_meta_copy")

        return failures

    def repair_local_relevance_embedded_json(
        self,
        generated_content: dict[str, Any],
    ) -> dict[str, Any] | None:
        body_paragraphs = [str(value) for value in generated_content.get("body_paragraphs", [])]
        if len(body_paragraphs) != 1 or not self.is_json_like_string(body_paragraphs[0]):
            return None

        try:
            embedded_payload = json.loads(body_paragraphs[0])
        except json.JSONDecodeError:
            return None

        if not isinstance(embedded_payload, dict):
            return None

        content_block = embedded_payload.get("content", {})
        bullet_points: list[str] = []
        repaired_body: list[str] = []

        if isinstance(content_block, dict):
            points = content_block.get("points", [])
            if isinstance(points, list):
                for point in points:
                    if not isinstance(point, dict):
                        continue
                    title = str(point.get("title", "")).strip()
                    text = str(point.get("text", "")).strip()
                    if title and text:
                        bullet_points.append(f"{title}: {text}")
                    elif title:
                        bullet_points.append(title)
                    elif text:
                        bullet_points.append(text)

            intro = str(content_block.get("intro", "")).strip()
            closing = str(content_block.get("closing", "")).strip()
            repaired_body.extend([paragraph for paragraph in [intro, closing] if paragraph])

        highlights = embedded_payload.get("highlights", [])
        if isinstance(highlights, list):
            for highlight in highlights:
                highlight_text = str(highlight).strip()
                if highlight_text:
                    bullet_points.append(highlight_text)

        service_area_note = str(embedded_payload.get("service_area_note", "")).strip()
        closing = str(embedded_payload.get("closing", "")).strip()
        intro = str(embedded_payload.get("intro", "")).strip()
        repaired_body.extend(
            paragraph
            for paragraph in [intro, service_area_note, closing]
            if paragraph and paragraph not in repaired_body
        )

        headline = str(embedded_payload.get("headline", "")).strip() or str(embedded_payload.get("title", "")).strip()
        subheadline = (
            str(embedded_payload.get("subheadline", "")).strip()
            or service_area_note
            or str(embedded_payload.get("service", "")).strip()
        )

        repaired_content = {
            "headline": headline,
            "subheadline": subheadline,
            "body_paragraphs": repaired_body,
            "bullet_points": bullet_points,
            "cta_label": "Check Service Area",
        }

        if not self.validate_generated_content(repaired_content):
            return None

        return repaired_content

    def service_summary_checks(
        self,
        item: dict[str, Any],
        combined_text: str,
        body_paragraphs: list[str],
        bullet_points: list[str],
    ) -> list[str]:
        failures: list[str] = []
        local_terms = self.get_slug_terms(str(item.get("page_slug", ""))) + ["austin"]
        service_terms = [
            "service",
            "services",
            "plumbing",
            "repair",
            "installation",
            "drain",
            "leak",
            "water heater",
            "pipe",
        ]
        non_empty_bullets = [value for value in bullet_points if str(value).strip()]

        if not self.contains_any_term(combined_text, local_terms):
            failures.append("service_summary_missing_local_context")
        if not self.contains_any_term(combined_text, service_terms):
            failures.append("service_summary_missing_service_scope")
        if not self.has_non_empty_list_items(body_paragraphs):
            failures.append("service_summary_empty_body")
        if len(non_empty_bullets) < 3:
            failures.append("service_summary_insufficient_bullets")

        return failures

    def contact_cta_checks(
        self,
        body_paragraphs: list[str],
        bullet_points: list[str],
        cta_label: str,
    ) -> list[str]:
        failures: list[str] = []
        non_empty_bullets = [value for value in bullet_points if str(value).strip()]

        if not self.has_non_empty_list_items(body_paragraphs):
            failures.append("contact_cta_empty_body")
        if any(self.is_json_like_string(value) for value in body_paragraphs):
            failures.append("contact_cta_json_like_body")
        if not cta_label.strip():
            failures.append("contact_cta_empty_cta")
        if len(non_empty_bullets) == 0:
            failures.append("contact_cta_missing_support_points")

        return failures

    def repair_contact_cta_embedded_json(
        self,
        generated_content: dict[str, Any],
    ) -> dict[str, Any] | None:
        body_paragraphs = [str(value) for value in generated_content.get("body_paragraphs", [])]
        if len(body_paragraphs) != 1 or not self.is_json_like_string(body_paragraphs[0]):
            return None

        try:
            embedded_payload = json.loads(body_paragraphs[0])
        except json.JSONDecodeError:
            return None

        if not isinstance(embedded_payload, dict):
            return None

        headline = str(embedded_payload.get("headline", "")).strip()
        subheadline = str(embedded_payload.get("subheadline", "")).strip()
        body = (
            str(embedded_payload.get("body", "")).strip()
            or str(embedded_payload.get("description", "")).strip()
            or str(embedded_payload.get("intro", "")).strip()
        )
        trust_points = embedded_payload.get("trust_points", [])
        primary_cta = embedded_payload.get("primary_cta", {})

        bullet_points: list[str] = []
        if isinstance(trust_points, list):
            bullet_points = [str(point).strip() for point in trust_points if str(point).strip()]

        cta_label = ""
        if isinstance(primary_cta, dict):
            cta_label = str(primary_cta.get("label", "")).strip()

        repaired_content = {
            "headline": headline,
            "subheadline": subheadline,
            "body_paragraphs": [body] if body else [],
            "bullet_points": bullet_points,
            "cta_label": cta_label,
        }

        if not self.validate_generated_content(repaired_content):
            return None

        return repaired_content

    def section_semantic_checks(
        self,
        section_name: str,
        combined_text: str,
    ) -> list[str]:
        checks = {
            "hero": ["local", "service", "austin", "plumbing"],
            "services_overview": ["service", "services", "repair", "installation", "plumbing"],
            "trust_signals": ["trust", "reliable", "dependable", "confidence", "professional"],
            "faq_preview": ["faq", "question", "questions", "answer", "answers", "concern"],
            "contact_cta": ["contact", "call", "request", "book", "help"],
        }
        required_terms = checks.get(section_name, [])
        failures = []
        if required_terms and not self.contains_any_term(combined_text, required_terms):
            failures.append(f"section_semantic_mismatch:{section_name}")
        return failures

    def quality_check_generated_content(
        self,
        item: dict[str, Any],
        generated_content: dict[str, Any],
    ) -> dict[str, Any]:
        payload = item.get("content_payload", {})
        headline = str(generated_content.get("headline", ""))
        subheadline = str(generated_content.get("subheadline", ""))
        body_paragraphs = [str(value) for value in generated_content.get("body_paragraphs", [])]
        bullet_points = [str(value) for value in generated_content.get("bullet_points", [])]
        cta_label = str(generated_content.get("cta_label", ""))
        section_name = str(item.get("section_name", ""))
        cta_intent = str(payload.get("cta_intent", ""))
        normalized_cta_label = self.normalize_cta_label(cta_label)
        cta_intent_match = self.matches_cta_intent(cta_label, cta_intent)

        combined_text = " ".join([headline, subheadline, *body_paragraphs])
        target_keywords = [str(value) for value in payload.get("target_keywords", [])]
        niche_terms = []
        city_terms = []

        project_package_path = Path(self.settings.artifacts_dir) / "project_package.json"
        if project_package_path.exists():
            project_package = self.load_json(str(project_package_path))
            input_data = project_package.get("input_data", {})
            niche_terms = [str(input_data.get("niche", ""))]
            city_terms = [str(input_data.get("city", ""))]

        score = 100
        reasons: list[str] = []
        has_context_relevance = self.contains_any_term(
            combined_text,
            target_keywords + niche_terms + city_terms,
        )

        if not headline.strip():
            score -= 25
            reasons.append("empty_headline")
        if not subheadline.strip():
            score -= 20
            reasons.append("empty_subheadline")

        if not has_context_relevance:
            score -= 20
            reasons.append("missing_city_or_niche_relevance")

        if not cta_intent_match:
            score -= 30
            reasons.append("cta_intent_mismatch")

        if self.detect_generic_copy(combined_text, has_context_relevance):
            score -= 20
            reasons.append("generic_sounding_copy")

        semantic_failures = self.section_semantic_checks(section_name, combined_text)
        for failure in semantic_failures:
            score -= 20
            reasons.append(failure)

        if section_name == "faq_preview":
            faq_failures = self.faq_preview_checks(body_paragraphs, bullet_points, cta_label)
            for failure in faq_failures:
                score -= 25
                reasons.append(failure)

        if section_name == "service_description":
            description_failures = self.service_description_checks(
                combined_text,
                body_paragraphs,
                bullet_points,
            )
            for failure in description_failures:
                score -= 20
                reasons.append(failure)

        if section_name == "benefits":
            benefits_failures = self.benefits_checks(
                combined_text,
                body_paragraphs,
                bullet_points,
            )
            for failure in benefits_failures:
                score -= 20
                reasons.append(failure)

        if section_name == "local_relevance":
            local_failures = self.local_relevance_checks(
                item,
                combined_text,
                body_paragraphs,
                bullet_points,
            )
            for failure in local_failures:
                score -= 20
                reasons.append(failure)

        if section_name == "service_summary":
            summary_failures = self.service_summary_checks(
                item,
                combined_text,
                body_paragraphs,
                bullet_points,
            )
            for failure in summary_failures:
                score -= 20
                reasons.append(failure)

        if section_name == "contact_cta":
            contact_failures = self.contact_cta_checks(
                body_paragraphs,
                bullet_points,
                cta_label,
            )
            for failure in contact_failures:
                score -= 20
                reasons.append(failure)

        hard_fail = self.should_hard_fail_quality(section_name, reasons)
        return {
            "passed": (score >= 70) and not hard_fail,
            "reasons": reasons,
            "score": max(score, 0),
            "normalized_cta_label": normalized_cta_label,
            "expected_cta_intent": cta_intent,
            "cta_intent_match": cta_intent_match,
        }

    def is_generated_output_usable(
        self,
        item: dict[str, Any],
        output_path: Path,
    ) -> bool:
        try:
            with output_path.open("r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError):
            return False

        generated_content = payload.get("generated_content")
        if not isinstance(generated_content, dict):
            return False

        if not self.validate_generated_content(generated_content):
            return False

        quality_result = self.quality_check_generated_content(item, generated_content)
        return bool(quality_result.get("passed"))

    def sanitize_preview(self, value: str, limit: int) -> str:
        return value[:limit]

    def run_codex_exec(
        self,
        executable_path: str,
        prompt: str,
        schema_path: str,
        output_path: str,
    ) -> tuple[str, str, int]:
        command_args = [
            executable_path,
            "exec",
            "--sandbox",
            "workspace-write",
            "--output-schema",
            schema_path,
            "-o",
            output_path,
            prompt,
        ]
        result = subprocess.run(
            command_args,
            shell=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
            cwd=str(Path.cwd()),
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode

    def read_generated_output_file(self, output_path: str) -> dict[str, Any] | None:
        output_file = Path(output_path)
        if not output_file.exists():
            return None

        try:
            with output_file.open("r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            return None

    def get_debug_paths(self, item_id: str) -> tuple[Path, Path]:
        debug_dir = ensure_directory(str(Path(self.settings.artifacts_dir) / "codex_debug"))
        safe_item_id = item_id.replace("/", "_").replace("\\", "_")
        schema_path = debug_dir / f"{safe_item_id}__schema.json"
        output_path = debug_dir / f"{safe_item_id}__output.json"
        return schema_path, output_path

    def get_failed_debug_file_paths(self, item_id: str) -> dict[str, Path]:
        debug_dir = ensure_directory(str(Path(self.settings.artifacts_dir) / "codex_debug"))
        safe_item_id = item_id.replace("/", "_").replace("\\", "_")
        return {
            "prompt_path": debug_dir / f"{safe_item_id}__prompt.txt",
            "stdout_path": debug_dir / f"{safe_item_id}__stdout.txt",
            "stderr_path": debug_dir / f"{safe_item_id}__stderr.txt",
            "command_path": debug_dir / f"{safe_item_id}__command.json",
        }

    def save_debug_files(
        self,
        item_id: str,
        prompt: str,
        stdout: str,
        stderr: str,
        command_args: list[str],
        return_code: int | None,
        schema_path: Path,
        output_path: Path,
    ) -> dict[str, str]:
        paths = self.get_failed_debug_file_paths(item_id)
        paths["prompt_path"].write_text(prompt, encoding="utf-8")
        paths["stdout_path"].write_text(stdout, encoding="utf-8")
        paths["stderr_path"].write_text(stderr, encoding="utf-8")
        command_payload = {
            "item_id": item_id,
            "command_args": command_args,
            "command_string": subprocess.list2cmdline(command_args),
            "cwd": str(Path.cwd()),
            "return_code": return_code,
            "schema_path": str(schema_path.resolve()),
            "output_path": str(output_path.resolve()),
        }
        with paths["command_path"].open("w", encoding="utf-8") as file:
            json.dump(command_payload, file, indent=2, ensure_ascii=False)
        return {key: str(path.resolve()) for key, path in paths.items()}

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
            "generation_mode": "codex_section_generation",
            "status": "generated",
            "model": "codex_exec_local",
            "generated_content": generated_content,
            "source_payload": item.get("content_payload", {}),
        }

        with output_path.open("w", encoding="utf-8") as file:
            json.dump(output_payload, file, indent=2, ensure_ascii=False)

        return str(output_path.resolve())

    def get_generated_section_output_path(self, item: dict[str, Any]) -> Path:
        page_slug = str(item.get("page_slug", ""))
        section_name = str(item.get("section_name", ""))
        return (
            Path(self.settings.outputs_dir)
            / "generated_sections"
            / page_slug
            / f"{section_name}.json"
        )

    def remove_generated_section_if_exists(self, item: dict[str, Any]) -> None:
        output_path = self.get_generated_section_output_path(item)
        if output_path.exists():
            output_path.unlink()

    def run(self) -> dict[str, Any]:
        project_package_path = Path(self.settings.artifacts_dir) / "project_package.json"
        project_package = self.load_json(str(project_package_path)) if project_package_path.exists() else {}
        project_name = str(project_package.get("project_name", ""))

        if not self.settings.enable_codex_generation:
            self.logger.info("Codex generation is disabled by configuration.")
            return self.build_result(
                project_name=project_name,
                run_mode="disabled",
                target_batch=self.settings.codex_target_batch,
                message="Codex generation disabled by configuration.",
            )

        executable_path = self.resolve_executable()
        if not executable_path or not self.is_cli_available(executable_path):
            self.logger.info("Codex CLI is not available on this machine.")
            return self.build_result(
                project_name=project_name,
                run_mode="unavailable",
                target_batch=self.settings.codex_target_batch,
                message="Codex CLI is not available on this machine.",
            )

        generation_manifest_path = Path(self.settings.artifacts_dir) / "generation_manifest.json"
        content_input_queue_path = Path(self.settings.artifacts_dir) / "content_input_queue.json"
        execution_plan_path = Path(self.settings.artifacts_dir) / "execution_plan.json"

        generation_manifest = self.load_json(str(generation_manifest_path))
        content_input_queue = self.load_json(str(content_input_queue_path))
        execution_plan = self.load_json(str(execution_plan_path))

        target_batch, selected_items = self.select_target_items(
            generation_manifest,
            content_input_queue,
            execution_plan,
        )

        project_language = str(project_package.get("input_data", {}).get("language", "en"))
        outputs: list[dict[str, Any]] = []
        item_logs: list[dict[str, Any]] = []
        debug_items: list[dict[str, Any]] = []
        processed_items = 0
        generated_items = 0
        failed_items = 0
        skipped_items = 0

        if not selected_items:
            return self.build_result(
                project_name=project_name,
                run_mode="codex_exec",
                target_batch=target_batch,
                message="No ready items matched the configured batch selection.",
                debug_items=debug_items,
                generation_enabled=True,
            )

        for item in selected_items:
            item_id = str(item.get("item_id", ""))
            page_slug = str(item.get("page_slug", ""))
            section_name = str(item.get("section_name", ""))

            if item.get("ready") is not True:
                skipped_items += 1
                item_logs.append(
                    {
                        "item_id": item_id,
                        "page_slug": page_slug,
                        "section_name": section_name,
                        "status": "skipped",
                        "message": "not_ready",
                    }
                )
                continue

            processed_items += 1
            prompt = self.build_prompt(item, project_language)
            schema_path, output_path = self.get_debug_paths(item_id)
            command_args = [
                executable_path,
                "exec",
                "--sandbox",
                "workspace-write",
                "--output-schema",
                str(schema_path),
                "-o",
                str(output_path),
                prompt,
            ]
            debug_entry: dict[str, Any] = {
                "item_id": item_id,
                "schema_path": str(schema_path.resolve()),
                "output_path": str(output_path.resolve()),
                "command_args": command_args,
                "return_code": None,
                "stdout_preview": "",
                "stderr_preview": "",
                "output_file_exists": False,
                "output_file_size": 0,
                "output_file_preview": "",
                "validation_passed": False,
                "quality_check_passed": False,
                "quality_score": 0,
                "quality_reasons": [],
                "attempts_used": 0,
                "retry_triggered": False,
                "failure_reason": "",
                "prompt_path": "",
                "stdout_path": "",
                "stderr_path": "",
                "command_path": "",
                "normalized_cta_label": "",
                "expected_cta_intent": "",
                "cta_intent_match": False,
                "repair_applied": False,
                "repair_note": "",
            }
            try:
                final_generated_content: dict[str, Any] | None = None
                final_failure_reason = ""
                stdout = ""
                stderr = ""
                for attempt_number in range(1, 3):
                    current_prompt = self.build_prompt(
                        item,
                        project_language,
                        is_retry=(attempt_number == 2),
                    )
                    prompt = current_prompt
                    debug_entry["attempts_used"] = attempt_number
                    debug_entry["retry_triggered"] = attempt_number == 2

                    with schema_path.open("w", encoding="utf-8") as file:
                        json.dump(self.build_output_schema(), file, indent=2, ensure_ascii=False)

                    if output_path.exists():
                        output_path.unlink()

                    stdout, stderr, returncode = self.run_codex_exec(
                        executable_path,
                        current_prompt,
                        str(schema_path),
                        str(output_path),
                    )
                    debug_entry["return_code"] = returncode
                    debug_entry["stdout_preview"] = self.sanitize_preview(stdout, 300)
                    debug_entry["stderr_preview"] = self.sanitize_preview(stderr, 500)

                    if stderr:
                        self.logger.warning("Codex stderr for %s: %s", item_id, debug_entry["stderr_preview"])

                    output_exists = output_path.exists()
                    debug_entry["output_file_exists"] = output_exists
                    debug_entry["output_file_size"] = 0
                    debug_entry["output_file_preview"] = ""
                    if output_exists:
                        output_text = output_path.read_text(encoding="utf-8")
                        debug_entry["output_file_size"] = output_path.stat().st_size
                        debug_entry["output_file_preview"] = self.sanitize_preview(output_text, 300)

                    if returncode != 0:
                        final_failure_reason = "subprocess_error"
                        break

                    generated_content = self.read_generated_output_file(str(output_path))
                    if generated_content is None:
                        final_failure_reason = "missing_output_file"
                        if output_exists:
                            final_failure_reason = "invalid_output_json"
                        break

                    validation_passed = self.validate_generated_content(generated_content)
                    debug_entry["validation_passed"] = validation_passed
                    if not validation_passed:
                        final_failure_reason = "schema_validation_failed"
                        break

                    quality_result = self.quality_check_generated_content(item, generated_content)
                    debug_entry["quality_check_passed"] = quality_result["passed"]
                    debug_entry["quality_score"] = quality_result["score"]
                    debug_entry["quality_reasons"] = quality_result["reasons"]
                    debug_entry["normalized_cta_label"] = quality_result["normalized_cta_label"]
                    debug_entry["expected_cta_intent"] = quality_result["expected_cta_intent"]
                    debug_entry["cta_intent_match"] = quality_result["cta_intent_match"]

                    if quality_result["passed"]:
                        final_generated_content = generated_content
                        final_failure_reason = ""
                        break

                    repaired_content, repair_applied, repair_note = self.try_repair_generated_content(
                        item,
                        generated_content,
                        quality_result,
                    )
                    if repair_applied:
                        repaired_quality = self.quality_check_generated_content(item, repaired_content)
                        debug_entry["repair_applied"] = True
                        debug_entry["repair_note"] = repair_note
                        debug_entry["quality_check_passed"] = repaired_quality["passed"]
                        debug_entry["quality_score"] = repaired_quality["score"]
                        debug_entry["quality_reasons"] = repaired_quality["reasons"]
                        debug_entry["normalized_cta_label"] = repaired_quality["normalized_cta_label"]
                        debug_entry["expected_cta_intent"] = repaired_quality["expected_cta_intent"]
                        debug_entry["cta_intent_match"] = repaired_quality["cta_intent_match"]
                        if repaired_quality["passed"]:
                            final_generated_content = repaired_content
                            final_failure_reason = ""
                            break

                    final_failure_reason = "quality_check_failed"
                    if attempt_number == 2:
                        break

                if final_generated_content is None:
                    debug_file_paths = self.save_debug_files(
                        item_id=item_id,
                        prompt=prompt,
                        stdout=stdout,
                        stderr=stderr,
                        command_args=command_args,
                        return_code=debug_entry["return_code"],
                        schema_path=schema_path,
                        output_path=output_path,
                    )
                    debug_entry.update(debug_file_paths)
                    self.remove_generated_section_if_exists(item)
                    failed_items += 1
                    debug_entry["failure_reason"] = final_failure_reason
                    item_logs.append(
                        {
                            "item_id": item_id,
                            "page_slug": page_slug,
                            "section_name": section_name,
                            "status": "failed",
                            "message": final_failure_reason,
                        }
                    )
                    debug_items.append(debug_entry)
                    continue

                try:
                    filepath = self.write_generated_section(item, final_generated_content)
                except OSError:
                    self.remove_generated_section_if_exists(item)
                    failed_items += 1
                    debug_entry["failure_reason"] = "write_failed"
                    item_logs.append(
                        {
                            "item_id": item_id,
                            "page_slug": page_slug,
                            "section_name": section_name,
                            "status": "failed",
                            "message": "write_failed",
                        }
                    )
                    debug_items.append(debug_entry)
                    continue

                generated_items += 1
                debug_file_paths = self.save_debug_files(
                    item_id=item_id,
                    prompt=prompt,
                    stdout=stdout,
                    stderr=stderr,
                    command_args=command_args,
                    return_code=debug_entry["return_code"],
                    schema_path=schema_path,
                    output_path=output_path,
                )
                debug_entry.update(debug_file_paths)
                outputs.append(
                    {
                        "item_id": item_id,
                        "page_slug": page_slug,
                        "section_name": section_name,
                        "filepath": filepath,
                        "status": "generated",
                    }
                )
                item_logs.append(
                    {
                        "item_id": item_id,
                        "page_slug": page_slug,
                        "section_name": section_name,
                        "status": "generated",
                        "message": "generated_successfully",
                    }
                )
                debug_items.append(debug_entry)
            except subprocess.TimeoutExpired:
                self.remove_generated_section_if_exists(item)
                failed_items += 1
                debug_entry["failure_reason"] = "timeout"
                item_logs.append(
                    {
                        "item_id": item_id,
                        "page_slug": page_slug,
                        "section_name": section_name,
                        "status": "failed",
                        "message": "timeout",
                    }
                )
                debug_items.append(debug_entry)
            except (FileNotFoundError, PermissionError, OSError):
                self.remove_generated_section_if_exists(item)
                failed_items += 1
                debug_entry["failure_reason"] = "subprocess_error"
                item_logs.append(
                    {
                        "item_id": item_id,
                        "page_slug": page_slug,
                        "section_name": section_name,
                        "status": "failed",
                        "message": "subprocess_error",
                    }
                )
                debug_items.append(debug_entry)

        return self.build_result(
            project_name=project_name,
            run_mode="codex_exec",
            target_batch=target_batch,
            message="Codex generation finished.",
            outputs=outputs,
            processed_items=processed_items,
            generated_items=generated_items,
            failed_items=failed_items,
            skipped_items=skipped_items,
            item_logs=item_logs,
            debug_items=debug_items,
            generation_enabled=True,
        )
