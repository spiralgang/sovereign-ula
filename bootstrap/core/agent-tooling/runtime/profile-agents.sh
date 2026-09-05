#!/bin/sh
# Sovereign-ULA agentic-coder profile drop-in (installed to /etc/profile.d/).
# Runs on every login shell inside the distro. Nothing secret is stored here —
# auth happens on the first `agy` run (Google account / API key) or via env
# vars the Android env already provides (proot inherits them).

# PATH: agy (~/.local/bin), uv-managed python (/opt/agents), npm globals.
for _p in "${HOME:-/root}/.local/bin" /opt/agents/bin /usr/local/bin; do
  case ":${PATH}:" in
    *:"$_p":*) ;;
    *) export PATH="$_p:$PATH" ;;
  esac
done

# google-genai SDK lives in the uv venv; activate only when present.
if [ -x /opt/agents/bin/python ]; then
  export VIRTUAL_ENV=/opt/agents
  export UV_CACHE_DIR="${UV_CACHE_DIR:-${HOME:-/root}/.cache/uv}"
fi

# Pass through keys the app/env already provides (empty when unset — harmless).
export GEMINI_API_KEY="${GEMINI_API_KEY:-}"
export GITHUB_PERSONAL_ACCESS_TOKEN="${GITHUB_PERSONAL_ACCESS_TOKEN:-}"

if command -v agy >/dev/null 2>&1 || [ -x "${HOME:-/root}/.local/bin/agy" ]; then
  cat <<'EOF'
────────────────────────────────────────────────────────────
  Agentic-coder env is READY (Antigravity CLI + MCP plugins).
  - launch:  agy                  (first run: sign in)
  - MCP:     /mcp in agy lists filesystem/github/context7
             (config: ~/.gemini/config/mcp_config.json)
  - python:  genai SDK in uv venv -> use `python` (PATH already set)
  - docs:    cat /support/agent-tooling/README.md
  - hermes-agent (this repo's autonomous runner): clone the repo
    and run `python .agent/runner.py --mode analyze-only`
────────────────────────────────────────────────────────────
EOF
fi
