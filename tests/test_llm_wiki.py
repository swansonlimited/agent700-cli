import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from a700cli import llm_wiki
from a700cli.llm_wiki import LlmWikiError


def test_init_creates_layout(tmp_path):
    info = llm_wiki.init_wiki(tmp_path)
    assert Path(info["root"]) == tmp_path.resolve()
    assert (tmp_path / "wiki" / "index.md").is_file()
    assert (tmp_path / "wiki" / "log.md").is_file()
    assert (tmp_path / "raw" / "inbox").is_dir()
    assert (tmp_path / "AGENTS.md").is_file()


def test_ingest_requires_init(tmp_path):
    with pytest.raises(LlmWikiError):
        llm_wiki.ingest_url(tmp_path, "https://example.com/article")


def test_ingest_url_writes_manifest_and_updates_wiki(tmp_path):
    llm_wiki.init_wiki(tmp_path)
    out = llm_wiki.ingest_url(tmp_path, "https://example.com/path?q=1")
    sid = out["source_id"]
    manifest = tmp_path / "raw" / "sources" / sid / "manifest.json"
    assert manifest.is_file()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["kind"] == "url"
    assert data["url"] == "https://example.com/path?q=1"
    assert data["source_id"] == sid
    assert "tool_version" in data

    log = (tmp_path / "wiki" / "log.md").read_text(encoding="utf-8")
    assert "ingest url" in log
    assert sid in log

    idx = (tmp_path / "wiki" / "index.md").read_text(encoding="utf-8")
    assert "wiki/sources/" in idx
    assert sid in idx


def test_ingest_file_copies_and_manifest(tmp_path):
    llm_wiki.init_wiki(tmp_path)
    f = tmp_path / "note.txt"
    f.write_text("hello provenance", encoding="utf-8")

    out = llm_wiki.ingest_file(tmp_path, f, category="notes")
    sid = out["source_id"]
    archived = tmp_path / "raw" / "sources" / sid / "original.txt"
    assert archived.is_file()
    assert archived.read_text(encoding="utf-8") == "hello provenance"

    data = json.loads(
        (tmp_path / "raw" / "sources" / sid / "manifest.json").read_text(encoding="utf-8")
    )
    assert data["kind"] == "file"
    assert data["category"] == "notes"
    assert data["sha256"] == hashlib.sha256(b"hello provenance").hexdigest()


def test_ingest_url_fetch_records_error_without_network(tmp_path):
    llm_wiki.init_wiki(tmp_path)
    with patch("a700cli.llm_wiki.urlopen", side_effect=OSError("no network")):
        out = llm_wiki.ingest_url(tmp_path, "https://example.invalid/x", fetch=True)
    sid = out["source_id"]
    data = json.loads(
        (tmp_path / "raw" / "sources" / sid / "manifest.json").read_text(encoding="utf-8")
    )
    assert data["fetch"]["attempted"] is True
    assert data["fetch"]["error"]


def test_normalize_url_for_fetch():
    assert llm_wiki.normalize_url_for_fetch("example.com/foo") == "https://example.com/foo"
