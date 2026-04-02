# Next Task

## objective

Extend generated coverage to `service-areas` as the last uncovered tier-2 support page, while keeping local-fit semantics and generated -> stub fallback safety intact.

## files_to_touch

- `src/runner/codex_section_generator.py`
- `README.md`
- `PROJECT_STATE.md`
- `NEXT_TASK.md`

## constraints

- do not break stub flow
- do not remove `generated -> stub` fallback
- do not weaken existing CTA-critical hard-fail behavior
- keep service-area semantics deterministic and section-specific
- prefer narrow prompt guidance and narrow repair rules over broad heuristics

## acceptance_criteria

- `service-areas` becomes `generated_complete` or clearly fails with precise quality/debug reasons
- existing generated-complete pages remain stable
- `artifacts/codex_generation_log.json` and `artifacts/codex_generation_debug.json` clearly explain the run
- downstream hybrid artifacts stay consistent

## run_checks

- inspect `artifacts/codex_generation_log.json`
- inspect `artifacts/codex_generation_debug.json`
- inspect `artifacts/generated_page_output_index.json`
- inspect `outputs/generated_pages/service-areas.json`
- run `python main.py`
