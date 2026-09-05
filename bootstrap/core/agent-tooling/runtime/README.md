# Agentic-coder layer (pre-seeded in this distro)

Every Sovereign-ULA distro rootfs ships an open agentic-coder environment —
built on the same toolchain the GitHub Actions runners use. All installs
happen in the containerized rootfs build (docker layer-cached), so nothing is
downloaded lazily at first launch on your phone.

## What you get

| Tool                   | What it is                                             | Auth                                      |
|------------------------|--------------------------------------------------------|-------------------------------------------|
| `agy` (Antigravity CLI)| Google's agent-first terminal coding agent (replaces the decommissioned Gemini CLI) | sign in on first `agy` run (Google account) |
| `uv` + venv `/opt/agents` | python toolchain manager; `google-genai` SDK inside   | `GEMINI_API_KEY` (AI Studio free tier)    |
| Node 22 + MCP plugins  | filesystem / github / context7 servers installed **globally** (zero launch lag) | github plugin needs `GITHUB_PERSONAL_ACCESS_TOKEN` exported before `agy` |
| hermes-agent (repo)    | this repo's autonomous runner — clone the repo, run `python .agent/runner.py` | NVIDIA or Gemini key |

## First run

```bash
agy                          # first run walks you through auth + setup
# inside agy: /mcp  -> filesystem, github, context7 are live
```

Python streaming one-liner (uv-managed venv is already on PATH):

```bash
export GEMINI_API_KEY="AIza..."   # free key: aistudio.google.com/apikey
python - <<'EOF'
import os
from google import genai
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
for chunk in client.models.generate_content_stream(
    model="gemini-2.5-flash",
    contents="write a fibonacci function in bash"):
    print(chunk.text or "", end="", flush=True)
print()
EOF
```

## Why this stack

- **agy over Gemini CLI** — Google decommissioned Gemini CLI on 2026-06-18;
  Antigravity CLI (`agy`) is the successor. MCP config lives at
  `~/.gemini/config/mcp_config.json` (shared with Antigravity 2.0/IDE).
- **uv over system pip** — the GenAI SDK is isolated in `/opt/agents`; no
  PEP-668 hacks, reproducible installs, fast uvx for ad-hoc python tools.
- **NodeSource Node 22** — "server-hosted": the stock Ubuntu Node is 18.x,
  which every current MCP server rejects; the apt repo + docker layer cache
  make this dependency free and lag-managed.
- **Global MCP installs over npx** — server binaries are on PATH at build
  time, so `agy` never waits on an npx download mid-session.
- **Docker everywhere possible** — the rootfs *is* a docker build (layer
  cache = the server-hosted lag manager for all of the above). On the repo
  side, Hermes + the verifier matrix run on GitHub-hosted runners the same
  way; a dev-container flavor of this layer can be produced for Codespaces.

## Honest name mapping

- **hermes-agent** — not a package; this repo's `.agent/` suite. Clone the
  repo in-env; identical code powers the GitHub Actions side.
- **aria-termux, freebuff, Antigravity desktop** — proprietary UIs. Their
  open, installable cores are exactly what is above (agy = Antigravity's CLI
  core). Nothing fake is installed under those names.

## Layout

- `~/.gemini/config/mcp_config.json` — live agent MCP config (generated)
- `/support/agent-tooling/mcp_config.json.example` — template copy
- `/support/agent-tooling/MCP-NOTES.txt` — plugin details + adding more
- `/support/agent-tooling/README.md` — this file
- `/etc/profile.d/sovereign-agents.sh` — login-shell wiring + ready hint

Keys are never baked into the image: auth on first `agy` run, or export
`GEMINI_API_KEY` / `GITHUB_PERSONAL_ACCESS_TOKEN` from the Android env.
