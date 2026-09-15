#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["jinja2==3.1.6", "playwright==1.62.0"]
# ///
"""Build the profile CV from JSON and its HTML template. Requires Google Chrome."""
import html
import json
import re
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

def kami_markup_factory(self_token: str):
    """Return a Jinja filter that converts the lightweight markup to HTML.

    Order matters: escape user text first, then inject our span markup so the
    spans themselves are not escaped.
    """
    self_span = f'<span class="self">{html.escape(self_token)}</span>'
    self_star_span = f'<span class="self">{html.escape(self_token)}*</span>'

    def render(text: str) -> str:
        if text is None:
            return ""
        out = html.escape(str(text), quote=False)
        # Citation article titles are the only straight double-quoted text; wrap
        # them FIRST, before injecting other spans whose attribute quotes
        # (class="self", class="muted") would otherwise be matched by this regex.
        out = re.sub(r'"([^"]+)"', r'"<span class="ptitle">\1</span>"', out)
        out = out.replace("{self*}", self_star_span)  # before {self}
        out = out.replace("{self}", self_span)
        out = re.sub(r"\*\*(.+?)\*\*", r'<span class="hl">\1</span>', out)
        out = re.sub(r"\[\[(.+?)\]\]", r'<span class="year">\1</span>', out)
        out = re.sub(r"//(.+?)//", r'<em class="muted">\1</em>', out)
        return out

    return render


def render_html(data: dict, template_dir: Path, template_name: str) -> str:
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(disabled_extensions=("html",), default=False),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["kami_markup"] = kami_markup_factory(data.get("self_author_token", ""))
    tmpl = env.get_template(template_name)
    return tmpl.render(**data)



def main():
    here = Path(__file__).resolve().parent
    data = json.loads((here / "cankun-cv.json").read_text())
    html_path = here / "cankun-cv.html"
    html_path.write_text(render_html(data, here, "cankun-cv.template.html"))
    pdf_path = here.parent / "Cankun_Wang_CV.pdf"
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        try:
            page = browser.new_page()
            page.goto(html_path.as_uri())
            page.evaluate("() => document.fonts.ready")
            page.pdf(path=str(pdf_path), prefer_css_page_size=True, print_background=True)
        finally:
            browser.close()
    print(f"Built {html_path} and {pdf_path}")

if __name__ == "__main__":
    main()
