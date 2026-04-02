# Next Task

## objective

Build a generated-first preview or handoff manifest that packages the current hybrid site outputs into one stable entry point for future template/code generation work.

## files_to_touch

- `main.py`
- `src/runner/generated_site_assembler.py`
- `src/runner/generated_html_renderer.py`
- `README.md`
- `PROJECT_STATE.md`
- `NEXT_TASK.md`

## constraints

- do not break stub flow
- do not remove `generated -> stub` fallback
- do not change existing generated page/site contracts unless the new artifact is additive
- keep the new layer deterministic and file-based
- prefer one compact manifest over a large new subsystem

## acceptance_criteria

- a new generated-first manifest or package artifact exists
- it points at the current generated site snapshot and generated rendered preview entry point
- it summarizes page coverage using existing generated artifacts
- existing generated/stub assembly and rendering still run without regression

## run_checks

- inspect `artifacts/generated_site_output_index.json`
- inspect `artifacts/generated_rendered_output_index.json`
- inspect `artifacts/generated_page_output_index.json`
- inspect the new handoff/preview artifact
- run `python main.py`
