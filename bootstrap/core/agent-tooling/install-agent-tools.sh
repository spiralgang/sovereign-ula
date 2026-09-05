#!/bin/bash
#
# Sovereign-ULA agentic-coder layer — baked into EVERY distro rootfs at
# bootstrap time (universal support layer -> bootstrap/core/).
#
# Installs (all open / free-tier):
#   * Antigravity CLI (agy)  — Google's agent-first terminal coding agent
#     (successor to the decommissioned Gemini CLI). Official curl installer
#     -> ~/.local/bin/agy. Auth on the first `agy` run.
#   * uv (Astral)            — python toolchain manager; the google-genai SDK
#     is installed into a uv-managed venv at /opt/agents (no system-pip hacks).
#   * Node 22 (NodeSource)   — server-hosted apt repo (docker-layer-cached =
#     "lag-managed"): Noble's apt Node is 18.x, which MCP servers REJECT
#     (engines >= 20.18.1).
#   * MCP plugin servers     — filesystem + github + context7 installed
#     GLOBALLY at build time so agent launches have ZERO npx cold-start lag.
#     Config written to ~/.gemini/config/mcp_config.json (Antigravity schema).
#
# hermes-agent (this repo's .agent/) is not a package: clone the repo in-env
# and run `python .agent/runner.py`. Proprietary UIs (aria-termux, freebuff,
# Antigravity desktop, ...) have no installable CLI cores beyond the above.
#
# Skip the whole layer (lean rootfs) with SOVEREIGN_SKIP_AGENT_TOOLS=1.
set -euo pipefail

if [ "${SOVEREIGN_SKIP_AGENT_TOOLS:-0}" = "1" ]; then
  echo "[agent-tools] skipped (SOVEREIGN_SKIP_AGENT_TOOLS=1)"
  exit 0
fi
export DEBIAN_FRONTEND=noninteractive
HOME_DIR="${HOME:-/root}"
export PATH="/usr/local/bin:${HOME_DIR}/.local/bin:/opt/agents/bin:$PATH"
echo "[agent-tools] installing agentic-coder layer..."

# --- 1. base runtimes (normally pre-installed by the distro main.sh) ---
for c in curl ca-certificates gnupg nodejs npm python3; do
  command -v "$c" >/dev/null 2>&1 || apt-get install -y --no-install-recommends "$c" >/dev/null 2>&1 || true
done

# --- 2. server-hosted Node 22 (apt Node 18 fails MCP engines >= 20.18.1) ---
NODE_MAJOR="$(node --version 2>/dev/null | sed 's/^v//' | cut -d. -f1 || echo 0)"
if [ "${NODE_MAJOR:-0}" -lt 20 ]; then
  echo "[agent-tools] upgrading Node $(node --version 2>/dev/null || echo none) -> NodeSource 22.x"
  if curl -fsSL https://deb.nodesource.com/setup_22.x -o /tmp/nodesource-setup.sh 2>/dev/null; then
    bash /tmp/nodesource-setup.sh >/dev/null 2>&1 || true
    apt-get install -y --no-install-recommends nodejs || \
      echo "[agent-tools] WARN: NodeSource upgrade failed — MCP servers need Node >= 20"
  else
    echo "[agent-tools] WARN: NodeSource unreachable — keeping apt Node $(node --version 2>/dev/null)"
  fi
fi

# --- 3. Antigravity CLI (agy) — successor to the decommissioned Gemini CLI ---
if ! command -v agy >/dev/null 2>&1 && [ ! -x "${HOME_DIR}/.local/bin/agy" ]; then
  echo "[agent-tools] installing Antigravity CLI (agy)..."
  if curl -fsSL https://antigravity.google/cli/install.sh | bash >/dev/null 2>&1; then
    echo "[agent-tools]   agy -> ${HOME_DIR}/.local/bin/agy"
  else
    echo "[agent-tools] WARN: agy install failed (offline?) — retry: curl -fsSL https://antigravity.google/cli/install.sh | bash"
  fi
fi

# --- 4. uv (Astral) python manager + google-genai in a managed venv ---
if ! command -v uv >/dev/null 2>&1; then
  echo "[agent-tools] installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1 || \
    echo "[agent-tools] WARN: uv install failed — falling back to system pip"
fi
if command -v uv >/dev/null 2>&1 && [ ! -x /opt/agents/bin/python ]; then
  uv venv /opt/agents >/dev/null 2>&1 || true
  uv pip install --python /opt/agents/bin/python --quiet google-genai 2>/dev/null || \
    /opt/agents/bin/python -m pip install --quiet google-genai || \
    echo "[agent-tools] WARN: google-genai install failed — retry: uv pip install --python /opt/agents/bin/python google-genai"
fi

# --- 5. MCP plugin servers: GLOBAL install = zero npx cold-start per launch ---
echo "[agent-tools] installing MCP servers globally (lag-free)..."
npm install -g --no-fund --no-audit --loglevel=error \
  @modelcontextprotocol/server-filesystem \
  @modelcontextprotocol/server-github \
  @upstash/context7-mcp || \
  echo "[agent-tools] WARN: global MCP install failed — config falls back to npx (slower first run)"

FS_BIN="$(command -v mcp-server-filesystem || true)"
GH_BIN="$(command -v mcp-server-github || true)"
C7_BIN="$(command -v context7-mcp || true)"

# --- 6. Antigravity MCP config, emitted by python (no shell-quoting traps) ---
#     Global: ~/.gemini/config/mcp_config.json   (Antigravity schema)
#     Example copy: /support/agent-tooling/mcp_config.json.example
python3 - "${HOME_DIR}" "${FS_BIN}" "${GH_BIN}" "${C7_BIN}" <<'PY'
import json
import os
import sys

home, fs_bin, gh_bin, c7_bin = sys.argv[1:5]

def server(binary, pkg, args):
    if binary:
        return {"command": binary, "args": args}
    return {"command": "npx", "args": ["-y", pkg] + args}

config = {
    "mcpServers": {
        "filesystem": server(fs_bin, "@modelcontextprotocol/server-filesystem",
                             ["/root", "/support", "/tmp"]),
        "github": server(gh_bin, "@modelcontextprotocol/server-github", []),
        "context7": server(c7_bin, "@upstash/context7-mcp", []),
    }
}
targets = [
    os.path.join(home, ".gemini", "config", "mcp_config.json"),
    "/support/agent-tooling/mcp_config.json.example",
]
for target in targets:
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)
        fh.write("\n")
PY

# --- 7. ship runtime scaffolding into /support/agent-tooling ---
install -Dm755 /core/agent-tooling/runtime/profile-agents.sh \
  /etc/profile.d/sovereign-agents.sh || true
install -Dm644 /core/agent-tooling/runtime/MCP-NOTES.txt \
  /support/agent-tooling/MCP-NOTES.txt
install -Dm644 /core/agent-tooling/runtime/README.md \
  /support/agent-tooling/README.md

echo "[agent-tools] done."
echo "[agent-tools]   agy      : $(command -v agy || echo "${HOME_DIR}/.local/bin/agy (if install succeeded)")"
echo "[agent-tools]   node     : $(node --version 2>/dev/null || echo '?')"
echo "[agent-tools]   uv/genai : $(command -v uv >/dev/null 2>&1 && echo '/opt/agents/bin/python ok' || echo 'uv missing (system pip fallback)')"
echo "[agent-tools]   MCP bins : filesystem=$([ -n "$FS_BIN" ] && echo ok || echo npx-fallback) github=$([ -n "$GH_BIN" ] && echo ok || echo npx-fallback) context7=$([ -n "$C7_BIN" ] && echo ok || echo npx-fallback)"
echo "[agent-tools]   config   : ${HOME_DIR}/.gemini/config/mcp_config.json"
