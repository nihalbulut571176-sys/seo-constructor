from config import get_settings
from src.pipeline.orchestrator import PipelineOrchestrator
from src.runner.consumer_runner import GenerationConsumerRunner
from src.runner.codex_section_generator import CodexSectionGenerator
from src.runner.generated_page_assembler import GeneratedPageAssembler
from src.runner.generated_html_renderer import GeneratedHtmlRenderer
from src.runner.generated_site_assembler import GeneratedSiteAssembler
from src.runner.stub_html_renderer import StubHtmlRenderer
from src.runner.stub_page_assembler import StubPageAssembler
from src.runner.stub_site_assembler import StubSiteAssembler
from src.runner.stub_output_writer import StubOutputWriter


def main() -> None:
    settings = get_settings()
    orchestrator = PipelineOrchestrator(settings=settings)
    context = orchestrator.run()
    runner = GenerationConsumerRunner(settings=settings)
    execution_log = runner.run()
    output_writer = StubOutputWriter(settings=settings)
    output_index = output_writer.run()
    page_assembler = StubPageAssembler(settings=settings)
    page_output_index = page_assembler.run()
    site_assembler = StubSiteAssembler(settings=settings)
    site_outputs = site_assembler.run()
    site_output_index = site_outputs.get("site_output_index", {})
    site_snapshot = site_outputs.get("site_snapshot", {})
    html_renderer = StubHtmlRenderer(settings=settings)
    rendered_output_index = html_renderer.run()
    codex_generator = CodexSectionGenerator(settings=settings)
    codex_outputs = codex_generator.run()
    generated_output_index = codex_outputs.get("generated_output_index", {})
    codex_generation_log = codex_outputs.get("codex_generation_log", {})
    generated_page_assembler = GeneratedPageAssembler(settings=settings)
    generated_page_output_index = generated_page_assembler.run()
    generated_site_assembler = GeneratedSiteAssembler(settings=settings)
    generated_site_outputs = generated_site_assembler.run()
    generated_site_output_index = generated_site_outputs.get("generated_site_output_index", {})
    generated_site_snapshot = generated_site_outputs.get("generated_site_snapshot", {})
    generated_html_renderer = GeneratedHtmlRenderer(settings=settings)
    generated_rendered_output_index = generated_html_renderer.run()
    execution_summary = execution_log.get("summary", {})
    codex_summary = codex_generation_log.get("summary", {})

    print(f"Project: {context.input_data.get('project_name')}")
    print(f"Artifacts created: {len(context.artifacts_index)}")
    for key, filepath in context.artifacts_index.items():
        print(f"- {key}: {filepath}")
    print("Dry-run execution:")
    print(f"- total phases: {execution_summary.get('total_phases', 0)}")
    print(f"- total batches: {execution_summary.get('total_batches', 0)}")
    print(f"- total items: {execution_summary.get('total_items', 0)}")
    print(f"- completed items: {execution_summary.get('completed_items', 0)}")
    print(f"- skipped items: {execution_summary.get('skipped_items', 0)}")
    print("Stub outputs:")
    print(f"- files created: {output_index.get('total_output_files', 0)}")
    print(f"- base directory: {settings.outputs_dir}")
    print("Page assembly:")
    print(f"- total pages: {page_output_index.get('total_pages', 0)}")
    print(f"- complete pages: {page_output_index.get('complete_pages', 0)}")
    print(f"- partial pages: {page_output_index.get('partial_pages', 0)}")
    print(f"- missing pages: {page_output_index.get('missing_pages', 0)}")
    print("Site assembly:")
    print(f"- total pages: {site_output_index.get('total_pages', 0)}")
    print(f"- complete pages: {site_output_index.get('complete_pages', 0)}")
    print(f"- partial pages: {site_output_index.get('partial_pages', 0)}")
    print(f"- missing pages: {site_output_index.get('missing_pages', 0)}")
    print(f"- total sections: {site_snapshot.get('summary', {}).get('total_sections', 0)}")
    print(f"- snapshot: {site_output_index.get('site_snapshot_filepath', '')}")
    print("HTML render:")
    print(f"- total rendered pages: {rendered_output_index.get('total_rendered_pages', 0)}")
    print(f"- index: {rendered_output_index.get('index_filepath', '')}")
    print("Codex generation:")
    if not generated_output_index.get("generation_enabled", False):
        print(f"- skipped: {codex_generation_log.get('message', 'Codex generation is disabled.')}")
    else:
        print(f"- processed items: {codex_summary.get('processed_items', 0)}")
        print(f"- generated items: {codex_summary.get('generated_items', 0)}")
        print(f"- failed items: {codex_summary.get('failed_items', 0)}")
        print(
            f"- generated output index: "
            f"{settings.artifacts_dir}\\generated_output_index.json"
        )
        print(
            f"- codex generation log: "
            f"{settings.artifacts_dir}\\codex_generation_log.json"
        )
    print("Generated page assembly:")
    print(f"- total pages: {generated_page_output_index.get('total_pages', 0)}")
    print(
        f"- generated complete: "
        f"{generated_page_output_index.get('generated_complete_pages', 0)}"
    )
    print(
        f"- mixed fallback: "
        f"{generated_page_output_index.get('mixed_fallback_pages', 0)}"
    )
    print(f"- stub only: {generated_page_output_index.get('stub_only_pages', 0)}")
    print(f"- partial: {generated_page_output_index.get('partial_pages', 0)}")
    print(f"- missing: {generated_page_output_index.get('missing_pages', 0)}")
    print("Generated site assembly:")
    print(f"- total pages: {generated_site_output_index.get('total_pages', 0)}")
    print(
        f"- generated complete: "
        f"{generated_site_output_index.get('generated_complete_pages', 0)}"
    )
    print(
        f"- mixed fallback: "
        f"{generated_site_output_index.get('mixed_fallback_pages', 0)}"
    )
    print(f"- partial: {generated_site_output_index.get('partial_pages', 0)}")
    print(f"- missing: {generated_site_output_index.get('missing_pages', 0)}")
    print(
        f"- total sections: "
        f"{generated_site_snapshot.get('summary', {}).get('total_sections', 0)}"
    )
    print(f"- snapshot: {generated_site_output_index.get('site_snapshot_filepath', '')}")
    print("Generated HTML render:")
    print(f"- total rendered pages: {generated_rendered_output_index.get('total_rendered_pages', 0)}")
    print(
        f"- generated complete: "
        f"{generated_rendered_output_index.get('summary', {}).get('generated_complete_pages', 0)}"
    )
    print(
        f"- mixed fallback: "
        f"{generated_rendered_output_index.get('summary', {}).get('mixed_fallback_pages', 0)}"
    )
    print(
        f"- stub only: "
        f"{generated_rendered_output_index.get('summary', {}).get('stub_only_pages', 0)}"
    )
    print(f"- partial: {generated_rendered_output_index.get('summary', {}).get('partial_pages', 0)}")
    print(f"- missing: {generated_rendered_output_index.get('summary', {}).get('missing_pages', 0)}")
    print(f"- index: {generated_rendered_output_index.get('index_filepath', '')}")


if __name__ == "__main__":
    main()
