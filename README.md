# A700cli

A Python CLI for interacting with Agent700 agents from the terminal.

It supports:
- interactive chat
- one-shot prompts
- file and stdin input
- streaming responses over WebSocket
- local session and conversation persistence
- local llm-wiki scaffold and provenance-preserving ingests (`--llm-wiki-*`)
- agent, org, MCP, billing, QA, and context-library admin commands

For the exact shipped CLI surface, run `a700cli --help`.

---

## Quick start

### Prerequisites
- Python 3.8+
- pip

### Install

```bash
pip install -r requirements.txt
pip install -e .
```

### First run

```bash
# start interactive setup

a700cli --interactive

# or send a single message

a700cli "Hello"
```

If `AGENT_UUID` is missing, the CLI will prompt for one. Use `a700cli --list-agents` to find available agents.

---

## Configuration

You can either let the CLI prompt for missing values or create a `.env` file yourself.

Example:

```env
EMAIL=your-email@company.com
PASSWORD=your-password
AGENT_UUID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
API_BASE_URL=https://api.agent700.ai
```

Notes:
- `API_BASE_URL` is optional and defaults to production.
- If `AGENT_UUID` is missing, the CLI will ask for it interactively.

---

## Local state

The CLI writes local state under your home directory:

- `~/.agent700/session.dat`
- `~/.agent700/conversations/default.json`

Project-local `.env` is still supported for credentials/config.

Legacy repo-local state files are still read if present, but new writes go to `~/.agent700/`.

---

## LLM Wiki (local-first)

These commands **do not** call the Agent700 API. They scaffold and record ingests using the usual llm-wiki layout: immutable `raw/`, maintained `wiki/`, `wiki/index.md`, `wiki/log.md`, and provenance in per-source `manifest.json` files under `raw/sources/<id>/`.

Initialize a wiki tree in the current directory (or pass `--llm-wiki-root`):

```bash
a700cli --llm-wiki-init
```

Record a URL (metadata only; add `--llm-wiki-fetch` to attempt a download into `raw/`):

```bash
a700cli --llm-wiki-ingest-url 'https://example.com/article'
```

Record a local file (copy into `raw/sources/<id>/` with SHA256 in the manifest):

```bash
a700cli --llm-wiki-ingest-file ./paper.pdf --llm-wiki-category fundamentals
```

| Flag | Purpose |
|------|---------|
| `--llm-wiki-init` | Create `raw/`, `wiki/`, `intake/`, `AGENTS.md`, `wiki/index.md`, `wiki/log.md` |
| `--llm-wiki-ingest-url URL` | URL ingest + `wiki/sources/` stub + index/log updates |
| `--llm-wiki-ingest-file PATH` | File ingest + same |
| `--llm-wiki-root DIR` | Wiki root (default: current working directory) |
| `--llm-wiki-fetch` | With ingest-url, save response bytes (errors recorded in manifest) |
| `--llm-wiki-category NAME` | Optional manifest label for file ingests |

---

## Core usage

### Interactive chat

```bash
a700cli --interactive
```

### Interactive chat with streaming

```bash
a700cli --interactive --streaming
```

### Single prompt

```bash
a700cli "Summarize this change"
```

### Read prompt from a file

```bash
a700cli --input-file prompt.txt
```

### Read prompt from stdin

```bash
echo "hello" | a700cli
```

### Write response to a file

```bash
a700cli "Generate release notes" --output-file release_notes.txt
```

### Quiet mode for scripts

```bash
result=$(a700cli "status check" --quiet)
echo "$result"
```

---

## Interactive commands

Interactive mode supports:

- `/exit`, `/quit`, `/q`
- `/clear`
- `/context`
- `/help`

`/context` shows recent saved conversation context.

---

## Streaming vs HTTP

### Default mode
By default, chat requests use HTTP.

```bash
a700cli "Explain this error"
```

### Streaming mode
Use `--streaming` to use the WebSocket client when available.

```bash
a700cli "Explain this error" --streaming
```

If the streaming path fails, the CLI falls back to HTTP.

---

## Agent discovery

```bash
# list agents
a700cli --list-agents

# search by name
a700cli --list-agents --search code

# JSON output for agent listing
a700cli --list-agents --format json
```

---

## Administrative commands

The CLI also exposes a set of account and platform operations.

| Area | Commands |
|---|---|
| Organizations | `--list-orgs` |
| App passwords | `--create-app-password`, `--list-app-passwords`, `--delete-app-password` |
| Agents | `--create-agent`, `--update-agent`, `--delete-agent`, `--show-agent`, `--list-agents` |
| MCP | `--list-mcp-servers`, `--mcp-tools`, `--mcp-health` |
| Billing | `--billing-usage`, `--start-date`, `--end-date` |
| QA / ratings | `--rate`, `--export-ratings`, `--qa-sheets` |
| Documents | `--parse-document` |
| Context library | `--context-library-list`, `--context-library-get`, `--context-library-set`, `--context-library-delete` |

For full argument details, use `a700cli --help`.

---

## Output behavior

### Default output
Human-oriented terminal output with Rich when available, with a plain fallback when it is not.

### Quiet output
`--quiet` prints raw assistant content without status chatter, which is the right mode for scripting.

### File output
`--output-file` writes raw assistant content to a file.

### Structured output
`--format json` is available for list-style/admin commands where supported, especially agent listing. Chat responses do not currently have a JSON response mode.

---

## Running from source

You can use either the installed entry point or the module form.

```bash
a700cli --help
python -m a700cli --help
```

---

## Development

### Setup

```bash
git clone <repository>
cd agent700-cli
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Tests

```bash
python -m pytest -q
```

---

## Troubleshooting

| Issue | What to check |
|---|---|
| Auth failures | `EMAIL` / `PASSWORD` in `.env`, account access, base URL |
| Invalid agent UUID | use `a700cli --list-agents` and copy the exact UUID |
| Streaming problems | retry without `--streaming` |
| Import/dependency issues | reinstall with `pip install -r requirements.txt && pip install -e .` |
| Unsure what is actually supported | run `a700cli --help` |

---

## License

MIT, see [LICENSE](LICENSE).
