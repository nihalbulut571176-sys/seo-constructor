from dataclasses import dataclass, field
from typing import Any


@dataclass
class PipelineContext:
    input_data: dict[str, Any]
    competitors: list[Any] = field(default_factory=list)
    pains: dict[str, Any] = field(default_factory=dict)
    semantics: dict[str, Any] = field(default_factory=dict)
    gap_analysis: dict[str, Any] = field(default_factory=dict)
    seo_priorities: dict[str, Any] = field(default_factory=dict)
    site_structure: dict[str, Any] = field(default_factory=dict)
    build_spec: dict[str, Any] = field(default_factory=dict)
    page_blueprints: dict[str, Any] = field(default_factory=dict)
    execution_plan: dict[str, Any] = field(default_factory=dict)
    project_package: dict[str, Any] = field(default_factory=dict)
    page_task_queue: dict[str, Any] = field(default_factory=dict)
    section_briefs: dict[str, Any] = field(default_factory=dict)
    content_input_queue: dict[str, Any] = field(default_factory=dict)
    generation_batches: dict[str, Any] = field(default_factory=dict)
    generation_manifest: dict[str, Any] = field(default_factory=dict)
    artifacts_index: dict[str, Any] = field(default_factory=dict)
