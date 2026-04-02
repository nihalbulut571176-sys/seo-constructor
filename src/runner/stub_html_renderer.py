from html import escape
from pathlib import Path
from typing import Any

from config import Settings
from src.tools.file_store import ensure_directory, save_json_artifact
from src.utils.logger import get_logger


class StubHtmlRenderer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = get_logger(__name__, settings.log_level)

    def load_json(self, filepath: str) -> dict[str, Any]:
        import json

        with Path(filepath).open("r", encoding="utf-8") as file:
            return json.load(file)

    def render_list(self, items: list[str]) -> str:
        if not items:
            return "<p>None</p>"
        list_items = "".join(f"<li>{escape(str(item))}</li>" for item in items)
        return f"<ul>{list_items}</ul>"

    def render_section(self, section: dict[str, Any]) -> str:
        section_name = escape(str(section.get("section_name", "")))
        status = str(section.get("status", ""))

        if status == "missing_stub":
            return (
                "<section>"
                f"<h2>{section_name}</h2>"
                "<p><strong>Missing section stub</strong></p>"
                "</section>"
            )

        headline = escape(str(section.get("headline", "")))
        subheadline = escape(str(section.get("subheadline", "")))
        bullet_points = self.render_list([str(item) for item in section.get("bullet_points", [])])
        cta_label = escape(str(section.get("cta_label", "")))

        cta_html = f"<p><button>{cta_label}</button></p>" if cta_label else "<p></p>"

        return (
            "<section>"
            f"<h2>{section_name}</h2>"
            f"<p><strong>{headline}</strong></p>"
            f"<p>{subheadline}</p>"
            f"{bullet_points}"
            f"{cta_html}"
            "</section>"
        )

    def build_page_html(self, page: dict[str, Any]) -> str:
        title_hint = escape(str(page.get("title_hint", "")))
        sections_html = "".join(self.render_section(section) for section in page.get("sections", []))
        seo_notes_html = self.render_list([str(item) for item in page.get("seo_notes", [])])
        target_keywords_html = self.render_list([str(item) for item in page.get("target_keywords", [])])
        pain_groups_html = self.render_list([str(item) for item in page.get("relevant_pain_groups", [])])

        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title_hint}</title>
  <style>
    body {{ font-family: Arial, sans-serif; max-width: 960px; margin: 0 auto; padding: 24px; line-height: 1.5; }}
    section {{ border-top: 1px solid #ddd; padding-top: 16px; margin-top: 16px; }}
    .meta p {{ margin: 4px 0; }}
    button {{ padding: 8px 12px; }}
  </style>
</head>
<body>
  <h1>{title_hint}</h1>
  <div class="meta">
    <p><strong>page_slug:</strong> {escape(str(page.get("page_slug", "")))}</p>
    <p><strong>page_type:</strong> {escape(str(page.get("page_type", "")))}</p>
    <p><strong>priority_tier:</strong> {escape(str(page.get("priority_tier", "")))}</p>
    <p><strong>build_priority:</strong> {escape(str(page.get("build_priority", "")))}</p>
    <p><strong>assembly_status:</strong> {escape(str(page.get("assembly_status", "")))}</p>
  </div>
  <section>
    <h2>SEO Notes</h2>
    {seo_notes_html}
  </section>
  <section>
    <h2>Target Keywords</h2>
    {target_keywords_html}
  </section>
  <section>
    <h2>Relevant Pain Groups</h2>
    {pain_groups_html}
  </section>
  {sections_html}
</body>
</html>
"""

    def build_index_html(self, project_name: str, pages: list[dict[str, Any]], summary: dict[str, Any]) -> str:
        links = "".join(
            (
                "<li>"
                f"<a href=\"{escape(str(page.get('page_slug', '')))}.html\">"
                f"{escape(str(page.get('page_slug', '')))}"
                "</a> "
                f"({escape(str(page.get('assembly_status', '')))}"
                ")</li>"
            )
            for page in pages
        )

        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(project_name)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; max-width: 960px; margin: 0 auto; padding: 24px; line-height: 1.5; }}
  </style>
</head>
<body>
  <h1>{escape(project_name)}</h1>
  <p><strong>Total pages:</strong> {summary.get("total_pages", 0)}</p>
  <p><strong>Complete:</strong> {summary.get("complete_pages", 0)}</p>
  <p><strong>Partial:</strong> {summary.get("partial_pages", 0)}</p>
  <p><strong>Missing:</strong> {summary.get("missing_pages", 0)}</p>
  <h2>Pages</h2>
  <ul>{links}</ul>
</body>
</html>
"""

    def run(self) -> dict[str, Any]:
        page_output_index_path = Path(self.settings.artifacts_dir) / "page_output_index.json"
        self.logger.info("Loading page output index from %s", page_output_index_path)
        page_output_index = self.load_json(str(page_output_index_path))

        rendered_dir = ensure_directory(str(Path(self.settings.outputs_dir) / "rendered"))
        rendered_pages = []

        for page_entry in page_output_index.get("pages", []):
            page_filepath = str(page_entry.get("filepath", ""))
            if not page_filepath:
                continue

            page = self.load_json(page_filepath)
            html = self.build_page_html(page)
            output_path = Path(rendered_dir) / f"{page.get('page_slug', '')}.html"
            output_path.write_text(html, encoding="utf-8")

            rendered_pages.append(
                {
                    "page_slug": page.get("page_slug", ""),
                    "page_type": page.get("page_type", ""),
                    "assembly_status": page.get("assembly_status", ""),
                    "filepath": str(output_path.resolve()),
                }
            )

        summary = {
            "total_pages": len(rendered_pages),
            "complete_pages": sum(1 for page in rendered_pages if page["assembly_status"] == "complete"),
            "partial_pages": sum(1 for page in rendered_pages if page["assembly_status"] == "partial"),
            "missing_pages": sum(1 for page in rendered_pages if page["assembly_status"] == "missing"),
        }

        index_html = self.build_index_html(
            project_name=page_output_index.get("project_name", ""),
            pages=rendered_pages,
            summary=summary,
        )
        index_path = Path(rendered_dir) / "index.html"
        index_path.write_text(index_html, encoding="utf-8")

        rendered_output_index = {
            "project_name": page_output_index.get("project_name", ""),
            "total_rendered_pages": len(rendered_pages),
            "index_filepath": str(index_path.resolve()),
            "pages": rendered_pages,
        }
        artifact_path = save_json_artifact(rendered_output_index, "rendered_output_index.json")
        self.logger.info("Saved rendered output index to %s", artifact_path)
        return rendered_output_index
