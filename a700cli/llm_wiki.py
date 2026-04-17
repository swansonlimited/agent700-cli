"""
Local-first LLM wiki scaffold and provenance-preserving ingest helpers.

Mirrors the core layout from the standalone llm-wiki pattern: raw/ immutable
captures, wiki/ for maintained pages, intake/ for queues, plus index.md and
log.md under wiki/.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from a700cli import __version__

DIRS = (
    "raw/inbox",
    "raw/sources",
    "raw/assets",
    "intake",
    "wiki/concepts",
    "wiki/formulas",
    "wiki/topics",
    "wiki/preferences",
    "wiki/notes",
    "wiki/domains",
    "wiki/sources",
    "wiki/syntheses",
)

AGENTS_MD = """# AGENTS.md — LLM Wiki (local)

This tree follows the LLM-wiki pattern: `raw/` holds immutable captures; `wiki/`
holds synthesized markdown. Preserve provenance for substantive claims.

## Directory contract

- `raw/inbox/` — unsorted materials
- `raw/sources/<source_id>/` — one directory per ingest (manifest + payload)
- `raw/assets/` — durable binary assets
- `intake/urls.md` — optional URL queue notes
- `wiki/preferences/` — durable user preferences for agents
- `wiki/notes/` — free-form notes
- `wiki/domains/` — workspace / file-domain summary pages
- `wiki/index.md` — catalog
- `wiki/log.md` — append-only chronology

## Ingest workflow

1. Capture into `raw/sources/<source_id>/` with `manifest.json`.
2. Add or update `wiki/sources/<page>.md` pointing at the raw path.
3. Update `wiki/index.md`.
4. Append to `wiki/log.md`.

## Second-brain entries

Use CLI flags to append preferences, notes, or domain summaries: each write markdown under
`wiki/preferences/`, `wiki/notes/`, or `wiki/domains/`, update `wiki/index.md`, and append
`wiki/log.md` with ISO timestamps and tool provenance.
"""

INTAKE_URLS_MD = """# URLs queue

Add one URL per line. Optional notes after `|`.

"""

WIKI_INDEX_TEMPLATE = """# LLM Wiki index

Local-first second brain. Immutable captures live under `raw/`; maintained pages live under `wiki/`.

## Preferences

## Notes

## Domain knowledge

## Sources

"""

WIKI_LOG_HEADER = """# Wiki log

Append-only chronology of ingests and notable actions.

"""


class LlmWikiError(Exception):
    """User-facing error for llm-wiki commands."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_z(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def source_id_from_digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()[:16]


def _slug_kebab(text: str, fallback: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or fallback


def slug_from_url(url: str, source_id: str) -> str:
    try:
        p = urlparse(url)
        host = (p.netloc or "").split("@")[-1]
        path = (p.path or "").strip("/")
        base = f"{host}-{path}" if path else host
        return _slug_kebab(base, source_id)[:80]
    except Exception:
        return f"source-{source_id}"


def slug_from_filename(path: Path, source_id: str) -> str:
    stem = path.stem or path.name
    return _slug_kebab(stem, source_id)[:80]


def page_name(slug: str, source_id: str) -> str:
    """Stable wiki filename: kebab slug plus short id to avoid collisions."""
    return f"{slug}-{source_id[:8]}"


def normalize_url_for_fetch(url: str) -> str:
    u = url.strip()
    if not urlparse(u).scheme:
        return "https://" + u
    return u


def wiki_root_resolve(root: Optional[Path]) -> Path:
    return (root or Path.cwd()).resolve()


def assert_wiki_initialized(root: Path) -> None:
    marker = root / "wiki" / "log.md"
    if not marker.is_file():
        raise LlmWikiError(
            f"Wiki not initialized at {root}. Run: a700cli --llm-wiki-init --llm-wiki-root {root}"
        )


def init_wiki(root: Path) -> Dict[str, Any]:
    root = wiki_root_resolve(root)
    created_dirs: list[str] = []
    for rel in DIRS:
        p = root / rel
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            created_dirs.append(rel)

    agents = root / "AGENTS.md"
    if not agents.is_file():
        agents.write_text(AGENTS_MD, encoding="utf-8")

    intake = root / "intake" / "urls.md"
    if not intake.is_file():
        intake.write_text(INTAKE_URLS_MD, encoding="utf-8")

    index = root / "wiki" / "index.md"
    if not index.is_file():
        index.write_text(WIKI_INDEX_TEMPLATE, encoding="utf-8")

    log = root / "wiki" / "log.md"
    if not log.is_file():
        log.write_text(WIKI_LOG_HEADER, encoding="utf-8")

    return {"root": str(root), "created_dirs": created_dirs, "fresh_scaffold": bool(created_dirs)}


def _write_manifest(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _append_log(root: Path, line: str) -> None:
    log = root / "wiki" / "log.md"
    with log.open("a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")


def _append_index_under_section(root: Path, section: str, bullet: str) -> None:
    """Insert a markdown bullet line under ## {section}, creating the section if missing."""
    idx = root / "wiki" / "index.md"
    text = idx.read_text(encoding="utf-8")
    header = f"## {section}"
    line_bullet = bullet.strip()
    if line_bullet and line_bullet in text:
        return
    lines = text.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip() == header)
    except StopIteration:
        idx.write_text(text.rstrip() + f"\n\n{header}\n\n{line_bullet}\n", encoding="utf-8")
        return
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## ") and lines[j].strip() != header:
            end = j
            break
    new_lines = lines[:end] + ([line_bullet] if line_bullet else []) + lines[end:]
    idx.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _append_index_source(root: Path, bullet: str) -> None:
    _append_index_under_section(root, "Sources", bullet)


def _write_source_page(
    root: Path,
    slug: str,
    title: str,
    source_id: str,
    manifest_rel: str,
    extra: str,
) -> Path:
    page = root / "wiki" / "sources" / f"{slug}.md"
    body = f"""# {title}

**Source id:** `{source_id}`

**Raw manifest:** `{manifest_rel}`

{extra}

## Sources

- Local raw capture: `{manifest_rel}`
"""
    page.write_text(body, encoding="utf-8")
    return page


def ingest_url(root: Path, url: str, fetch: bool = False) -> Dict[str, Any]:
    root = wiki_root_resolve(root)
    assert_wiki_initialized(root)
    url = url.strip()
    if not url:
        raise LlmWikiError("URL is empty")

    sid = source_id_from_digest(url.encode("utf-8"))
    slug = slug_from_url(normalize_url_for_fetch(url), sid)
    pname = page_name(slug, sid)
    dest = root / "raw" / "sources" / sid
    dest.mkdir(parents=True, exist_ok=True)

    captured = _utc_now()
    fetch_info: Dict[str, Any] = {"attempted": fetch, "path": None, "error": None}
    if fetch:
        fetch_url = normalize_url_for_fetch(url)
        try:
            req = Request(
                fetch_url, headers={"User-Agent": f"a700cli-llm-wiki/{__version__}"}
            )
            with urlopen(req, timeout=60) as resp:
                raw_bytes = resp.read()
            out = dest / "fetched.bin"
            out.write_bytes(raw_bytes)
            fetch_info["path"] = str(out.relative_to(root))
        except URLError as e:
            fetch_info["error"] = str(e.reason) if hasattr(e, "reason") else str(e)
        except Exception as e:  # noqa: BLE001 — surface to manifest for provenance
            fetch_info["error"] = str(e)

    manifest: Dict[str, Any] = {
        "captured_at": _iso_z(captured),
        "kind": "url",
        "source_id": sid,
        "tool": "a700cli",
        "tool_version": __version__,
        "url": url,
        "fetch": fetch_info,
    }
    mpath = dest / "manifest.json"
    _write_manifest(mpath, manifest)

    manifest_rel = str(mpath.relative_to(root))
    title = urlparse(normalize_url_for_fetch(url)).netloc or url
    extra = f"**URL:** {url}\n"
    if fetch and fetch_info.get("path"):
        extra += f"**Fetched bytes:** saved to `{fetch_info['path']}`\n"
    elif fetch and fetch_info.get("error"):
        extra += f"**Fetch error:** {fetch_info['error']}\n"

    page = _write_source_page(root, pname, title, sid, manifest_rel, extra)

    ts = _iso_z(captured)
    _append_log(
        root,
        f"- [{ts}] ingest url → `{manifest_rel}` (wiki: `{page.relative_to(root)}`)",
    )
    _append_index_source(
        root,
        f"- [{title}](wiki/sources/{pname}.md) — captured {ts} (`{sid}`)",
    )
    return {"source_id": sid, "manifest": manifest_rel, "wiki_page": str(page.relative_to(root))}


def ingest_file(root: Path, file_path: Path, category: Optional[str] = None) -> Dict[str, Any]:
    root = wiki_root_resolve(root)
    assert_wiki_initialized(root)
    src = file_path.expanduser().resolve()
    if not src.is_file():
        raise LlmWikiError(f"Not a file: {src}")

    data = src.read_bytes()
    sid = source_id_from_digest(data)
    slug = slug_from_filename(src, sid)
    pname = page_name(slug, sid)
    dest = root / "raw" / "sources" / sid
    dest.mkdir(parents=True, exist_ok=True)

    suffix = src.suffix or ""
    archived = dest / f"original{suffix}"
    shutil.copy2(src, archived)

    captured = _utc_now()
    manifest: Dict[str, Any] = {
        "captured_at": _iso_z(captured),
        "category": category,
        "kind": "file",
        "original_filename": src.name,
        "original_path": str(src),
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
        "source_id": sid,
        "stored_as": str(archived.relative_to(root)),
        "tool": "a700cli",
        "tool_version": __version__,
    }
    mpath = dest / "manifest.json"
    _write_manifest(mpath, manifest)

    manifest_rel = str(mpath.relative_to(root))
    title = src.name
    extra = f"**Original path:** `{src}`\n"
    if category:
        extra += f"**Category:** {category}\n"
    extra += f"**SHA256:** `{manifest['sha256']}`\n"

    page = _write_source_page(root, pname, title, sid, manifest_rel, extra)

    ts = _iso_z(captured)
    _append_log(
        root,
        f"- [{ts}] ingest file → `{manifest_rel}` (wiki: `{page.relative_to(root)}`)",
    )
    _append_index_source(
        root,
        f"- [{title}](wiki/sources/{pname}.md) — captured {ts} (`{sid}`)",
    )
    return {"source_id": sid, "manifest": manifest_rel, "wiki_page": str(page.relative_to(root))}


def _ensure_wiki_subdir(root: Path, name: str) -> Path:
    p = root / "wiki" / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def _brain_entry_fingerprint(seed: str, body: str, captured: datetime) -> tuple[str, str, str]:
    ts = _iso_z(captured)
    digest = source_id_from_digest(f"{seed}\n{body}\n{ts}".encode("utf-8"))
    short = digest[:8]
    slug_base = seed[:72] if seed.strip() else body[:72]
    slug = _slug_kebab(slug_base, short)
    return digest, short, slug


def add_preference(
    root: Path, body: str, title: Optional[str] = None
) -> Dict[str, Any]:
    root = wiki_root_resolve(root)
    assert_wiki_initialized(root)
    body = body.strip()
    if not body:
        raise LlmWikiError("Preference text is empty")
    _ensure_wiki_subdir(root, "preferences")
    captured = _utc_now()
    display = (title or "").strip() or (
        body.splitlines()[0][:72] if body.splitlines() else "preference"
    )
    digest, short, slug = _brain_entry_fingerprint(display, body, captured)
    fname = f"{slug}-{short}.md"
    page = root / "wiki" / "preferences" / fname
    ts = _iso_z(captured)
    page.write_text(
        f"""# {display}

**Kind:** preference
**Recorded at:** {ts}
**Tool:** a700cli {__version__}
**Entry id:** `{digest}`

---

{body}
""",
        encoding="utf-8",
    )
    rel = page.relative_to(root).as_posix()
    _append_log(root, f"- [{ts}] preference | {display} → `{rel}`")
    _append_index_under_section(
        root, "Preferences", f"- [{display}]({rel}) — {ts}"
    )
    return {"entry_id": digest, "wiki_page": rel, "title": display}


def add_note(root: Path, body: str, title: Optional[str] = None) -> Dict[str, Any]:
    root = wiki_root_resolve(root)
    assert_wiki_initialized(root)
    body = body.strip()
    if not body:
        raise LlmWikiError("Note text is empty")
    _ensure_wiki_subdir(root, "notes")
    captured = _utc_now()
    display = (title or "").strip() or (
        body.splitlines()[0][:72] if body.splitlines() else "note"
    )
    digest, short, slug = _brain_entry_fingerprint(display, body, captured)
    fname = f"{slug}-{short}.md"
    page = root / "wiki" / "notes" / fname
    ts = _iso_z(captured)
    page.write_text(
        f"""# {display}

**Kind:** note
**Recorded at:** {ts}
**Tool:** a700cli {__version__}
**Entry id:** `{digest}`

---

{body}
""",
        encoding="utf-8",
    )
    rel = page.relative_to(root).as_posix()
    _append_log(root, f"- [{ts}] note | {display} → `{rel}`")
    _append_index_under_section(root, "Notes", f"- [{display}]({rel}) — {ts}")
    return {"entry_id": digest, "wiki_page": rel, "title": display}


def add_domain_summary(
    root: Path,
    name: str,
    summary: str,
    context_path: Optional[str] = None,
) -> Dict[str, Any]:
    root = wiki_root_resolve(root)
    assert_wiki_initialized(root)
    name = name.strip()
    summary = summary.strip()
    if not name:
        raise LlmWikiError("Domain name is empty")
    if not summary:
        raise LlmWikiError("Domain summary is empty")
    _ensure_wiki_subdir(root, "domains")
    captured = _utc_now()
    digest, short, slug = _brain_entry_fingerprint(name, summary, captured)
    fname = f"{slug}-{short}.md"
    page = root / "wiki" / "domains" / fname
    ts = _iso_z(captured)
    ctx = context_path.strip() if context_path else ""
    page.write_text(
        f"""# Domain: {name}

**Kind:** domain summary
**Recorded at:** {ts}
**Tool:** a700cli {__version__}
**Context path:** `{ctx or "(none)"}`
**Entry id:** `{digest}`

---

{summary}
""",
        encoding="utf-8",
    )
    rel = page.relative_to(root).as_posix()
    _append_log(root, f"- [{ts}] domain | {name} → `{rel}`")
    _append_index_under_section(
        root, "Domain knowledge", f"- [{name}]({rel}) — {ts}"
    )
    return {"entry_id": digest, "wiki_page": rel, "name": name}


def ingest_file_with_summary(
    root: Path, file_path: Path, summary: str, category: Optional[str] = None
) -> Dict[str, Any]:
    root = wiki_root_resolve(root)
    summary = summary.strip()
    if not summary:
        raise LlmWikiError("Summary text is empty")
    out = ingest_file(root, file_path, category=category)
    _ensure_wiki_subdir(root, "domains")
    src = file_path.expanduser().resolve()
    captured = _utc_now()
    digest, short, slug = _brain_entry_fingerprint(src.name, summary, captured)
    fname = f"{slug}-{short}.md"
    page = root / "wiki" / "domains" / fname
    ts = _iso_z(captured)
    title = f"Summary: {src.name}"
    page.write_text(
        f"""# {title}

**Kind:** file domain summary
**Recorded at:** {ts}
**Tool:** a700cli {__version__}
**Source file:** `{src}`
**Ingest wiki page:** `{out['wiki_page']}`
**Manifest:** `{out['manifest']}`
**Entry id:** `{digest}`

---

{summary}
""",
        encoding="utf-8",
    )
    rel = page.relative_to(root).as_posix()
    sid = out["source_id"]
    sid_short = sid[:8]
    _append_log(
        root,
        f"- [{ts}] file summary | {src.name} → `{rel}` (ingest `{sid}`)",
    )
    _append_index_under_section(
        root,
        "Domain knowledge",
        f"- [{title}]({rel}) — {ts} (ingest `{sid_short}`)",
    )
    return {
        **out,
        "domain_wiki_page": rel,
        "domain_entry_id": digest,
    }


def wiki_status(root: Optional[Path]) -> Dict[str, Any]:
    root = wiki_root_resolve(root)
    assert_wiki_initialized(root)

    def count_md(sub: str) -> int:
        d = root / "wiki" / sub
        if not d.is_dir():
            return 0
        return sum(1 for p in d.glob("*.md") if p.is_file())

    log_path = root / "wiki" / "log.md"
    log_lines = 0
    if log_path.is_file():
        log_lines = len(log_path.read_text(encoding="utf-8").splitlines())

    raw_sources = root / "raw" / "sources"
    n_raw = 0
    if raw_sources.is_dir():
        n_raw = sum(1 for p in raw_sources.iterdir() if p.is_dir())

    return {
        "root": str(root),
        "preferences": count_md("preferences"),
        "notes": count_md("notes"),
        "domains": count_md("domains"),
        "source_pages": count_md("sources"),
        "raw_source_dirs": n_raw,
        "log_lines": log_lines,
    }


def wiki_index_text(root: Optional[Path]) -> str:
    root = wiki_root_resolve(root)
    assert_wiki_initialized(root)
    return (root / "wiki" / "index.md").read_text(encoding="utf-8")
