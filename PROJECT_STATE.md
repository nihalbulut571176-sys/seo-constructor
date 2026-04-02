# Project State

## Current Snapshot

- Deterministic planning pipeline is implemented and stable.
- Stub flow is implemented and stable.
- Local generated flow via `codex exec` is implemented and stable.
- Hybrid assembly and hybrid HTML preview are implemented.

## Main Runtime Status

- `codex exec` structured output works through `--output-schema` and `-o`
- generated sections are written to `outputs/generated_sections/`
- stale generated files are cleaned when a section fails quality
- generated outputs are re-checked before reuse
- fallback `generated -> stub` is preserved

## Generated Coverage

Currently generated-complete pages:

- `home`
- `services`
- `about`
- `contact`
- `service-areas`
- `faq`
- `emergency-service`
- `installation`
- `repair`
- `austin-downtown`
- `north-austin`
- `south-austin`

Only one page is still stub-only:

- `blog`

## Key Artifacts In Active Use

- `artifacts/page_blueprints.json`
- `artifacts/execution_plan.json`
- `artifacts/generation_manifest.json`
- `artifacts/codex_generation_log.json`
- `artifacts/codex_generation_debug.json`
- `artifacts/generated_page_output_index.json`
- `artifacts/generated_site_output_index.json`
- `artifacts/generated_rendered_output_index.json`

## What Was Fixed Recently

- structured-output integration for local Codex generation
- subprocess argv ordering for `codex exec`
- stale generated cleanup on failure
- CTA-critical hard fail logic
- better CTA intent matching
- stricter `faq_preview` quality checks
- section-specific rules for:
  - `services_overview`
  - `service_description`
  - `benefits`
  - `local_relevance`
  - `service_summary`
- strengthened `local_relevance` prompt and checks to block JSON-like/meta copy on geo pages
- stricter `faq_preview` generation for the `services` hub page, including deterministic recovery for empty schema-valid output
- `contact_cta` cleanup to block JSON-like body blobs and preserve clean generated outputs for downstream assembly
- deterministic repair for `contact_form` embedded JSON/config output
- deterministic repair for `service_area_summary` embedded JSON/config output

## Current Bottleneck

Generated layer now covers the full practical site core:

- `home`
- `services`
- `about`
- `contact`
- `service-areas`
- `faq`
- all three `service_detail` pages
- all three `location_page` pages

The remaining uncovered page is the low-priority content page:

- `blog`

The higher-value next move is no longer raw page coverage. It is packaging the generated-first site into a clean handoff layer for future template/code generation.

## Most Valuable Next Directions

1. build a generated-first preview or handoff manifest on top of `outputs/generated_site/` and `outputs/generated_rendered/`
2. keep improving generated-first site handoff quality for future page/template code generation
3. only then decide whether the low-priority `blog` page deserves generated coverage
