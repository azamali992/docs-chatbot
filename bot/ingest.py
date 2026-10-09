"""Load a folder of documents and split it into sections the bot can cite.

Supported: .md, .txt, .html/.htm, .pdf. Markdown is split on headings so each
chunk is one topic ("Shipping > Delivery times"). PDFs are split per page,
then by size. Long sections are split again so no chunk is huge.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

MAX_WORDS = 220


@dataclass
class Chunk:
    id: str          # stable id, e.g. "shipping#delivery-times"
    source: str      # file name
    title: str       # "Shipping and delivery > Delivery times"
    text: str


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "section"


def _split_long(body: str) -> list[str]:
    words = body.split()
    if len(words) <= MAX_WORDS:
        return [body.strip()]  # keep line breaks so lists stay readable in citations
    step = MAX_WORDS - 40  # 40-word overlap so a fact on the boundary isn't lost
    return [" ".join(words[i:i + MAX_WORDS]) for i in range(0, len(words), step) if words[i:i + MAX_WORDS]]


def _markdown_sections(text: str) -> list[tuple[str, str]]:
    """Return (heading path, body) pairs. H1 is the doc title, H2/H3 are sections."""
    doc_title, sections, heading, body = "", [], None, []
    for line in text.splitlines():
        m = re.match(r"^(#{1,3})\s+(.*)", line)
        if m and len(m.group(1)) == 1:
            doc_title = m.group(2).strip()
            continue
        if m:
            if heading is not None or "".join(body).strip():
                sections.append((heading, "\n".join(body).strip()))
            heading, body = m.group(2).strip(), []
        else:
            body.append(line)
    sections.append((heading, "\n".join(body).strip()))
    out = []
    for h, b in sections:
        if not b:
            continue
        out.append((f"{doc_title} > {h}" if doc_title and h else (h or doc_title or "Overview"), b))
    return out


def _html_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|nav|footer).*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<h([1-3])[^>]*>", lambda m: "\n" + "#" * int(m.group(1)) + " ", raw)
    raw = re.sub(r"(?i)</h[1-3]>|<br\s*/?>|</p>|</li>", "\n", raw)
    return html.unescape(re.sub(r"<[^>]+>", " ", raw))


def load_file(path: Path) -> list[Chunk]:
    ext = path.suffix.lower()
    stem = path.stem
    pairs: list[tuple[str, str]]
    if ext == ".pdf":
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            pairs = [(f"{stem} p.{i}", page.extract_text() or "") for i, page in enumerate(pdf.pages, start=1)]
    elif ext in {".html", ".htm"}:
        pairs = _markdown_sections(_html_text(path.read_text(errors="ignore")))
    elif ext in {".md", ".txt"}:
        text = path.read_text(errors="ignore")
        pairs = _markdown_sections(text) if ext == ".md" else [(stem, text)]
    else:
        return []

    chunks, seen = [], set()
    for title, body in pairs:
        for n, part in enumerate(_split_long(body)):
            if not part.strip():
                continue
            cid = f"{stem}#{_slug(title.split(' > ')[-1])}" + (f"-{n + 1}" if n else "")
            while cid in seen:
                cid += "x"
            seen.add(cid)
            chunks.append(Chunk(id=cid, source=path.name, title=title, text=part))
    return chunks


def load_folder(folder: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            chunks.extend(load_file(path))
    return chunks
