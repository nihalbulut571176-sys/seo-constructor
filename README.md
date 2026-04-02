# SEO Site Automation Skeleton

Local Python project for staged SEO site planning and local content stub generation from `niche + city` input.

The project stays intentionally simple:

- no web search
- no database
- no Docker
- no UI framework
- no site code generation
- no external API requirement for the main generation path

It builds deterministic planning artifacts first, then runs local stub consumers, and now includes an opt-in local AI generation layer via `codex exec`.

## Structure

- `README.md` - project overview and flow.
- `.env.example` - environment settings example.
- `requirements.txt` - minimal Python dependencies.
- `main.py` - entry point for the pipeline and runner layers.
- `config.py` - runtime settings loader.
- `inputs/project.json` - single project input file.
- `artifacts/` - pipeline and runner JSON artifacts.
- `outputs/sections/` - stub section outputs.
- `outputs/generated_sections/` - generated section outputs from local `codex exec`.
- `outputs/pages/` - stub-only page-level JSON outputs.
- `outputs/generated_pages/` - hybrid page-level outputs with generated-first fallback.
- `outputs/generated_site/site_snapshot.json` - hybrid generated-first site snapshot.
- `outputs/site/site_snapshot.json` - full site snapshot.
- `outputs/rendered/` - stub-only static HTML preview.
- `outputs/generated_rendered/` - hybrid static HTML preview.
- `src/pipeline/` - pipeline context, orchestrator, and steps.
- `src/runner/` - execution runners, writers, assemblers, renderers, and generators.
- `src/tools/` - file helpers and tool placeholders.
- `src/utils/` - shared utilities.
- `AGENTS.md` - compact operating instructions for future Codex runs.
- `PROJECT_STATE.md` - short current-state snapshot.
- `NEXT_TASK.md` - current active task definition.

## Working With Codex

This repo is set up for short, low-context Codex runs.

Use this lightweight workflow:

1. read `AGENTS.md`
2. read `PROJECT_STATE.md`
3. read `NEXT_TASK.md`
4. inspect only the few directly relevant code files
5. make the smallest useful change
6. run a focused check first
7. run `python main.py` only if runtime/output behavior changed

Meaning of the repo memory files:

- `AGENTS.md` - stable operating rules and file priorities
- `PROJECT_STATE.md` - compact current status of the project
- `NEXT_TASK.md` - the current task to execute next

## Input

`inputs/project.json` stores one project configuration:

- `project_name`
- `niche`
- `city`
- `country`
- `language`
- `site_type`
- `max_pages`
- `budget_mode`
- `include_images`
- `include_blog`
- `notes`

## Pipeline Context

`PipelineContext` is the shared state object passed through the pipeline.

Main fields:

- `input_data`
- `competitors`
- `pains`
- `semantics`
- `gap_analysis`
- `seo_priorities`
- `site_structure`
- `build_spec`
- `page_blueprints`
- `execution_plan`
- `project_package`
- `page_task_queue`
- `section_briefs`
- `content_input_queue`
- `generation_batches`
- `generation_manifest`
- `artifacts_index`

`artifacts_index` maps artifact keys to saved JSON filepaths.

## Deterministic Pipeline Artifacts

The pipeline creates these planning artifacts:

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

## Runner Layers

### Dry Run Consumer

`GenerationConsumerRunner` reads `generation_manifest.json` and `content_input_queue.json`, walks phases, batches, and items, and writes:

- `artifacts/execution_log.json`

This is still a dry-run layer and does not generate content.

### Stub Output Writer

`StubOutputWriter` reads the execution log and writes deterministic section stub files:

- `outputs/sections/{page_slug}/{section_name}.json`
- `artifacts/output_index.json`

### Stub Page Assembler

`StubPageAssembler` assembles section stub files into page-level JSON outputs:

- `outputs/pages/{page_slug}.json`
- `artifacts/page_output_index.json`

### Stub Site Assembler

`StubSiteAssembler` combines all page-level outputs into one site snapshot:

- `outputs/site/site_snapshot.json`
- `artifacts/site_output_index.json`

### Stub HTML Renderer

`StubHtmlRenderer` renders page-level outputs into simple static HTML files:

- `outputs/rendered/{page_slug}.html`
- `outputs/rendered/index.html`
- `artifacts/rendered_output_index.json`

This is the first locally viewable stub-only preview layer.

## Codex Section Generator

`CodexSectionGenerator` is the first opt-in AI generation layer in the main runtime path.

It uses local `codex exec` instead of any external API key flow.
It uses structured output mode via `--output-schema` and `-o`, so the final generated JSON is read from the output file instead of parsing normal stdout text.

It is intentionally limited and safe:

- disabled by default
- does not break the project when disabled
- does not replace stub outputs
- writes into a separate generated output layer
- only processes a very small subset of ready items
- does not try to generate the whole site at once

### Env Settings

Add these settings to `.env`:

- `ENABLE_CODEX_GENERATION=false`
- `CODEX_EXECUTABLE=codex`
- `CODEX_TARGET_BATCH=high__home`
- `CODEX_MAX_ITEMS=5`

### Safe Run Rules

- If `ENABLE_CODEX_GENERATION=false`, the generator is skipped.
- If the Codex CLI is not available, the generator is skipped safely.
- Existing stub outputs remain unchanged.
- By default it targets only batch `high__home`.
- If that batch is missing, it falls back to the first 3 ready items from `phase_1_foundation_high`.

### Generated Outputs

When enabled and successful, it writes:

- `outputs/generated_sections/{page_slug}/{section_name}.json`
- `artifacts/generated_output_index.json`
- `artifacts/codex_generation_log.json`
- `artifacts/codex_generation_debug.json`

`generated_output_index.json` tracks created generated files.

`codex_generation_log.json` tracks processed, generated, failed, and skipped items.

`codex_generation_debug.json` stores per-item schema/output/debug diagnostics for structured-output integration.

Failed items also save full subprocess debug files in `artifacts/codex_debug/`, including prompt, stdout, stderr, and command metadata.
CTA-critical sections now hard-fail on CTA intent mismatch, and debug sidecars are saved for both failed and successful runs.
CTA intent matching now uses normalized phrase-based semantic rules while CTA-critical sections still hard-fail on mismatch.
`services_overview` also has a narrow deterministic CTA normalization step when the output is otherwise valid but uses a contact-style CTA instead of a service-discovery CTA.
When the configured target batch is already fully generated, the Codex generator now advances automatically to the next pending high-priority page using `execution_plan` order.

`stdout` and `stderr` are treated only as diagnostics. They are not used as the final content channel.

A schema-valid output is not enough on its own. Generated sections also pass a deterministic quality gate before being written into `outputs/generated_sections/`.
Existing generated section files are also re-checked against the current quality gate before reuse, so stale weak outputs do not remain in the hybrid layer after stricter rules are introduced.
`faq_preview` now has stricter semantic checks for non-empty body copy, non-empty CTA, and natural-language bullet content instead of serialized JSON blobs.
For the `services` hub page, `faq_preview` also has a narrow deterministic recovery path for empty schema-valid output so the generated-first layer does not fall back just because the model returned a blank object.
`service_description` and `benefits` also have section-specific quality checks for service scope, value/trust language, and minimum structured detail, with narrow CTA normalization where the content is otherwise usable.
`local_relevance` and `service_summary` now have location-page quality checks for area relevance, local coverage wording, and minimum structured detail so generated geo pages can be trusted as generated-first outputs.
`local_relevance` also explicitly blocks JSON-like/meta copy and requires visible area-context language, which keeps geo pages usable in the generated-first snapshot instead of falling back to weak machine-shaped outputs.
`contact_cta` now blocks JSON-like body blobs and can recover embedded contact payloads before downstream assembly, which keeps generated-first pages cleaner for future template/code generation.
`contact_form` and `service_area_summary` now also repair embedded JSON/config-shaped outputs into clean section content, which keeps generated-first contact pages usable without weakening fallback safety.

This is the first local AI generation layer without requiring `OPENAI_API_KEY`.

## Generated Page Assembler

`GeneratedPageAssembler` is a hybrid page-level assembler layered on top of both generated and stub section outputs.

It reads:

- `artifacts/page_blueprints.json`
- `artifacts/output_index.json`
- `artifacts/generated_output_index.json` when present

Then it assembles pages into:

- `outputs/generated_pages/{page_slug}.json`
- `artifacts/generated_page_output_index.json`

### Fallback Logic

For each required section, it resolves sources in this order:

1. `outputs/generated_sections/{page_slug}/{section_name}.json`
2. `outputs/sections/{page_slug}/{section_name}.json`

This means:

- generated content is used first when available
- stub content is used automatically as fallback
- the existing stub flow remains untouched

### Assembly Statuses

- `generated_complete` - all required sections came from generated outputs
- `mixed_fallback` - generated and stub sections were mixed, with no missing sections
- `stub_only` - all sections came from stub outputs
- `partial` - at least one section found, but some are missing
- `missing` - no section outputs found for the page

### Difference Between Page Layers

- `outputs/pages/` - original stub-only assembled pages
- `outputs/generated_pages/` - hybrid assembled pages that prefer generated sections and fall back to stub sections

## Generated Site Assembler

`GeneratedSiteAssembler` assembles a site-level hybrid snapshot from `outputs/generated_pages/`.

It writes:

- `outputs/generated_site/site_snapshot.json`
- `artifacts/generated_site_output_index.json`

This gives the project one generated-first site-level handoff artifact for future delivery packaging and code generation work.

## Generated HTML Renderer

`GeneratedHtmlRenderer` renders HTML from `outputs/generated_pages/` instead of `outputs/pages/`.

It writes:

- `outputs/generated_rendered/{page_slug}.html`
- `outputs/generated_rendered/index.html`
- `artifacts/generated_rendered_output_index.json`

This renderer shows the hybrid layer:

- `generated` sections when available
- `stub` sections as automatic fallback
- `missing` sections when nothing is available

### Difference Between Rendered Layers

- `outputs/rendered/` - preview built from stub-only assembled pages
- `outputs/generated_rendered/` - preview built from generated-first, stub-fallback assembled pages

## Data Flow

1. `main.py` runs `PipelineOrchestrator`.
2. The pipeline reads `inputs/project.json`.
3. `PipelineContext` moves through all deterministic steps.
4. Each step writes a JSON artifact into `artifacts/`.
5. `GenerationConsumerRunner` produces a dry-run execution log.
6. `StubOutputWriter` writes section stub files.
7. `StubPageAssembler` builds page-level outputs.
8. `StubSiteAssembler` builds the site snapshot.
9. `StubHtmlRenderer` creates the stub-only HTML preview.
10. `CodexSectionGenerator` optionally creates generated section files through local `codex exec`.
11. `GeneratedPageAssembler` assembles hybrid page outputs from generated-first, stub-fallback section sources.
12. `GeneratedSiteAssembler` assembles a hybrid generated-first site snapshot from `outputs/generated_pages/`.
13. `GeneratedHtmlRenderer` renders the hybrid preview from `outputs/generated_pages/`.

## Run

```bash
pip install -r requirements.txt
python main.py
```

## Result After Run

After a normal run with Codex generation disabled:

- deterministic pipeline artifacts appear in `artifacts/`
- dry-run execution log is created
- stub section outputs are written to `outputs/sections/`
- page-level outputs are written to `outputs/pages/`
- hybrid page outputs are written to `outputs/generated_pages/`
- hybrid generated-first site snapshot is written to `outputs/generated_site/site_snapshot.json`
- site snapshot is written to `outputs/site/site_snapshot.json`
- stub preview HTML files are written to `outputs/rendered/`
- hybrid preview HTML files are written to `outputs/generated_rendered/`
- Codex generation artifacts are still written, but marked as disabled

When Codex generation is enabled and available:

- a small selected subset of sections is generated into `outputs/generated_sections/`
- `generated_output_index.json` and `codex_generation_log.json` describe the run
- `GeneratedPageAssembler` uses generated sections first and falls back to stubs for the rest
- `GeneratedHtmlRenderer` renders that hybrid page layer into browsable HTML files

## Next Logical Step

Build a preview or delivery manifest that points to `outputs/generated_rendered/index.html`, `outputs/generated_pages/`, `outputs/generated_site/site_snapshot.json`, and the key hybrid artifacts as a single handoff package.
