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


def test_second_brain_entries_update_index_and_status(tmp_path):
    llm_wiki.init_wiki(tmp_path)

    pref = llm_wiki.add_preference(
        tmp_path,
        "Jimmy prefers direct, verifiable answers.",
        title="Response style",
    )
    note = llm_wiki.add_note(
        tmp_path,
        "Keep the first PR local-first and avoid backend dependencies.",
        title="Feature scope",
    )
    domain = llm_wiki.add_domain_summary(
        tmp_path,
        "agent700-cli",
        "CLI stores local state under ~/.agent700 and now has local second-brain commands.",
        context_path="/Users/Fred/.openclaw/workspace-work/agent700-cli",
    )

    index = llm_wiki.wiki_index_text(tmp_path)
    assert pref["wiki_page"] in index
    assert note["wiki_page"] in index
    assert domain["wiki_page"] in index

    status = llm_wiki.wiki_status(tmp_path)
    assert status["preferences"] == 1
    assert status["notes"] == 1
    assert status["domains"] == 1
    assert status["source_pages"] == 0


def test_ingest_file_with_summary_creates_domain_page(tmp_path):
    llm_wiki.init_wiki(tmp_path)
    f = tmp_path / "design.md"
    f.write_text("retrieval design", encoding="utf-8")

    out = llm_wiki.ingest_file_with_summary(
        tmp_path,
        f,
        "Design note for the retrieval and provenance path.",
        category="design",
    )

    assert (tmp_path / out["domain_wiki_page"]).is_file()
    domain_text = (tmp_path / out["domain_wiki_page"]).read_text(encoding="utf-8")
    assert "Source file:" in domain_text
    assert out["manifest"] in domain_text

    status = llm_wiki.wiki_status(tmp_path)
    assert status["domains"] == 1
    assert status["source_pages"] == 1
    assert status["raw_source_dirs"] == 1


@pytest.mark.cli
@pytest.mark.unit
def test_cli_llm_wiki_status_exits_before_auth(tmp_path, capsys):
    llm_wiki.init_wiki(tmp_path)

    with patch("sys.argv", ["a700cli", "--llm-wiki-status", "--llm-wiki-root", str(tmp_path)]):
        with patch("a700cli.__main__.load_environment") as mock_env:
            from a700cli.__main__ import main

            with pytest.raises(SystemExit) as exc:
                main()

    assert exc.value.code == 0
    mock_env.assert_not_called()
    captured = capsys.readouterr()
    assert "LLM wiki root:" in captured.out
    assert "preferences:" in captured.out


def test_normalize_url_for_fetch():
    assert llm_wiki.normalize_url_for_fetch("example.com/foo") == "https://example.com/foo"
