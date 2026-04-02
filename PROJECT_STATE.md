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
- `faq`
- `emergency-service`
- `installation`
- `repair`
- `austin-downtown`
- `north-austin`
- `south-austin`

Remaining pages are now mostly tier-2/tier-3 support pages and non-commercial trust pages.

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

## Current Bottleneck

Generated layer now covers the full commercial core:

- `home`
- all three `service_detail` pages
- all three `location_page` pages
- the `services` hub page

The main remaining gap is the last uncovered tier-2 support page:

- `service-areas`

Tier-3 trust/support pages remain intentionally lower priority:

- `about`
- `contact`
- `blog`

## Most Valuable Next Directions

1. stabilize `service-areas` as the next generated tier-2 support page
2. keep improving generated-first site handoff quality for future page/template code generation
3. move selectively onto tier-3 trust/support pages only after the remaining tier-2 support page is stable
