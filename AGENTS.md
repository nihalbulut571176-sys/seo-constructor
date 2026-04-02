# Codex Operating Guide

## Project Goal

Build a local Python workflow that turns `niche + city + site settings` into:

1. deterministic SEO planning artifacts
2. stub section/page/site outputs
3. generated section outputs via local `codex exec`
4. hybrid page/site assembly with `generated -> stub` fallback
5. local HTML preview
6. a stable foundation for future real site code generation

This repo is for a single local user first, not SaaS or production infra.

## Core Architecture

Primary entry point:

- `main.py`

Deterministic planning layer:

- `src/pipeline/context.py`
- `src/pipeline/orchestrator.py`
- `src/pipeline/steps.py`

Generated runtime layer:

- `src/runner/codex_section_generator.py`
- `src/runner/generated_page_assembler.py`
- `src/runner/generated_site_assembler.py`
- `src/runner/generated_html_renderer.py`

Stub runtime layer:

- `src/runner/consumer_runner.py`
- `src/runner/stub_output_writer.py`
- `src/runner/stub_page_assembler.py`
- `src/runner/stub_site_assembler.py`
- `src/runner/stub_html_renderer.py`

## Existing Layers

Planning artifacts already exist and are part of the expected pipeline:

- `competitors.json`
- `site_structure.json`
- `semantics.json`
- `build_spec.json`
- `seo_priorities.json`
- `pains.json`
- `gap_analysis.json`
- `page_blueprints.json`
- `execution_plan.json`
- `project_package.json`
- `page_task_queue.json`
- `section_briefs.json`
- `content_input_queue.json`
- `generation_batches.json`
- `generation_manifest.json`

Runner outputs already exist:

- stub sections in `outputs/sections/`
- generated sections in `outputs/generated_sections/`
- stub pages in `outputs/pages/`
- hybrid pages in `outputs/generated_pages/`
- stub site snapshot in `outputs/site/site_snapshot.json`
- hybrid site snapshot in `outputs/generated_site/site_snapshot.json`
- stub HTML preview in `outputs/rendered/`
- hybrid HTML preview in `outputs/generated_rendered/`

## Do Not Break

These are hard constraints:

- Do not break the deterministic pipeline.
- Do not break stub flow.
- Do not remove or weaken `generated -> stub` fallback.
- Do not delete stub outputs in favor of generated outputs.
- Do not replace local Codex generation with external API-first runtime.
- Do not introduce database, Docker, frontend framework, SaaS layers, or large orchestration systems without a clear project-level need.
- Do not rewrite architecture when a narrow patch is enough.

## Sources Of Truth

Use these as the main operational truth:

- `README.md` for the repo-level overview
- `PROJECT_STATE.md` for the current compact status snapshot
- `NEXT_TASK.md` for the active task definition
- `inputs/project.json` for the current project input
- `artifacts/page_blueprints.json` for page intent and required sections
- `artifacts/execution_plan.json` for build order
- `artifacts/generation_manifest.json` for batch/phase selection
- `artifacts/codex_generation_log.json` and `artifacts/codex_generation_debug.json` for generated-layer diagnosis
- `artifacts/generated_page_output_index.json` and `artifacts/generated_rendered_output_index.json` for downstream status

If docs disagree with runtime artifacts, trust the runtime artifacts.

## Token-Efficient Workflow

Default rule: read narrowly, not broadly.

Start every task with the smallest useful file set:

1. `AGENTS.md`
2. `PROJECT_STATE.md`
3. `NEXT_TASK.md`
4. one or two directly relevant implementation files

Only open more files if blocked.

For common task types, inspect in this order:

- pipeline task:
  - `src/pipeline/orchestrator.py`
  - `src/pipeline/context.py`
  - specific function in `src/pipeline/steps.py`
- generated content quality task:
  - `src/runner/codex_section_generator.py`
  - `artifacts/codex_generation_log.json`
  - `artifacts/codex_generation_debug.json`
  - one or two relevant files in `outputs/generated_sections/...`
- hybrid assembly task:
  - `src/runner/generated_page_assembler.py`
  - `src/runner/generated_html_renderer.py`
  - relevant output index artifact
- preview task:
  - `src/runner/generated_html_renderer.py`
  - `artifacts/generated_rendered_output_index.json`
  - one generated page JSON

Avoid re-reading:

- the entire repo
- large artifact files unrelated to the active bug
- full snapshots when one page-level file is enough

## Execution Loop

Use this default loop:

1. inspect the smallest relevant files
2. patch only the necessary files
3. run the smallest useful check
4. run full `python main.py` only when runtime/output behavior could be affected
5. update `PROJECT_STATE.md` only if the actual project state changed
6. replace `NEXT_TASK.md` with the next active task

## Checks

Preferred check order:

1. targeted file inspection
2. targeted runtime/artifact check
3. full run only if needed

Focused checks examples:

- inspect one generated section:
  - `Get-Content -Raw outputs/generated_sections/<page>/<section>.json`
- inspect current generation result:
  - `Get-Content -Raw artifacts/codex_generation_log.json`
- inspect hybrid page status:
  - `Get-Content -Raw artifacts/generated_page_output_index.json`

Full run:

```powershell
python main.py
```

Use full run when:

- changing `main.py`
- changing pipeline step ordering or context fields
- changing generator behavior
- changing assemblers/renderers
- changing artifact formats

## Code Style

- Keep functions small and explicit.
- Prefer deterministic rules over "smart" abstractions.
- Prefer direct `Path` and JSON handling.
- Prefer narrow helper functions over broad frameworks.
- Preserve downstream contracts unless a real migration is intended.
- Keep names literal and boring rather than clever.

## Working Rules For Codex

- Assume local, single-user, repo-first workflow.
- Prefer minimal, reversible edits.
- Prefer incremental section-specific quality rules over big general systems.
- When touching the generated layer, always think about stale output cleanup and fallback safety.
- When runtime behavior changes, inspect the affected artifacts after running.

## Quick Start For Future Tasks

Short prompt format for future runs:

1. read `AGENTS.md`, `PROJECT_STATE.md`, `NEXT_TASK.md`
2. do the task in `NEXT_TASK.md`
3. run the listed checks
4. update `PROJECT_STATE.md` and `NEXT_TASK.md`

Even shorter:

- `Read AGENTS.md, PROJECT_STATE.md, NEXT_TASK.md and execute NEXT_TASK.md.`
