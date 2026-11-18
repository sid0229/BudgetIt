"""Heading/paragraph-aware chunking of the curated knowledge base.

Each markdown file in ``rag/knowledge`` starts with a front-matter block::

    ---
    title: Some title
    source: https://example.gov.in
    ---

The body is split into sections at markdown headings, then into paragraphs,
and paragraphs are packed into chunks of roughly ``min_chars``-``max_chars``
characters. Every chunk carries the document title/source and the heading of
the section it came from (prefixed into the text so both BM25 and embeddings
see the context). Chunk ids are ``"<file_stem>#<n>"`` (n starts at 0).
"""

from __future__ import annotations

import re
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge"

MIN_CHARS = 400
MAX_CHARS = 800

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def parse_front_matter(raw: str) -> tuple[dict, str]:
    """Return (metadata, body). Missing front matter yields an empty dict."""
    meta: dict[str, str] = {}
    text = raw.lstrip("﻿")
    if text.startswith("---"):
        lines = text.splitlines()
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                for line in lines[1:i]:
                    if ":" in line:
                        key, _, value = line.partition(":")
                        meta[key.strip().lower()] = value.strip().strip('"').strip("'")
                return meta, "\n".join(lines[i + 1 :])
    return meta, text


def _sections(body: str) -> list[tuple[str, list[str]]]:
    """Split body into (heading, paragraphs). Paragraphs are blank-line separated."""
    sections: list[tuple[str, list[str]]] = []
    heading = ""
    paras: list[str] = []
    buf: list[str] = []

    def flush_para():
        if buf:
            para = "\n".join(buf).strip()
            if para:
                paras.append(para)
            buf.clear()

    for line in body.splitlines():
        m = _HEADING_RE.match(line.strip())
        if m:
            flush_para()
            if paras:
                sections.append((heading, paras))
            heading = m.group(2).strip()
            paras = []
        elif not line.strip():
            flush_para()
        else:
            buf.append(line.rstrip())
    flush_para()
    if paras:
        sections.append((heading, paras))
    return sections


def _split_long(para: str, max_chars: int) -> list[str]:
    """Split an oversized paragraph on line breaks, then sentences."""
    if len(para) <= max_chars:
        return [para]
    pieces = para.split("\n") if "\n" in para else re.split(r"(?<=[.!?])\s+", para)
    out: list[str] = []
    cur = ""
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        if cur and len(cur) + 1 + len(piece) > max_chars:
            out.append(cur)
            cur = piece
        else:
            cur = f"{cur}\n{piece}" if cur else piece
    if cur:
        out.append(cur)
    # Last resort hard split for a single giant sentence.
    final: list[str] = []
    for p in out:
        while len(p) > max_chars:
            final.append(p[:max_chars])
            p = p[max_chars:]
        if p:
            final.append(p)
    return final


def chunk_text(
    raw: str,
    stem: str,
    title: str | None = None,
    source: str | None = None,
    min_chars: int = MIN_CHARS,
    max_chars: int = MAX_CHARS,
) -> list[dict]:
    """Chunk one markdown document into dicts {id, title, source, heading, text}."""
    meta, body = parse_front_matter(raw)
    title = title or meta.get("title") or stem.replace("_", " ").title()
    source = source or meta.get("source") or "BudgetIt editorial"

    chunks: list[dict] = []
    for heading, paras in _sections(body):
        # Skip a section whose heading is just the document title.
        prefix = f"{heading}\n" if heading and heading != title else ""
        cur = ""
        units: list[str] = []
        for p in paras:
            units.extend(_split_long(p, max_chars - len(prefix)))
        for unit in units:
            if cur and len(prefix) + len(cur) + 2 + len(unit) > max_chars and len(cur) >= min_chars // 2:
                chunks.append({"heading": heading, "text": prefix + cur})
                cur = unit
            else:
                cur = f"{cur}\n\n{unit}" if cur else unit
        if cur:
            chunks.append({"heading": heading, "text": prefix + cur})

    # Greedily pack neighbouring section chunks up to max_chars; always absorb
    # tiny fragments (e.g. a closing disclaimer line) into their predecessor.
    merged: list[dict] = []
    for ch in chunks:
        if merged and (
            len(merged[-1]["text"]) + 2 + len(ch["text"]) <= max_chars
            or len(ch["text"]) < min_chars // 3
        ):
            merged[-1]["text"] += "\n\n" + ch["text"]
        else:
            merged.append(dict(ch))

    return [
        {
            "id": f"{stem}#{i}",
            "title": title,
            "source": source,
            "heading": ch["heading"],
            "text": ch["text"].strip(),
        }
        for i, ch in enumerate(merged)
    ]


def load_chunks(knowledge_dir: Path | str | None = None) -> list[dict]:
    """Chunk every ``*.md`` file in the knowledge directory (sorted, deterministic)."""
    kdir = Path(knowledge_dir) if knowledge_dir else KNOWLEDGE_DIR
    chunks: list[dict] = []
    for path in sorted(kdir.glob("*.md")):
        chunks.extend(chunk_text(path.read_text(encoding="utf-8"), path.stem))
    return chunks
