#!/usr/bin/env python3
"""
Sovereign ULA — AI Agent PR Review Runner ("gitapp-type" LLM calling).

This is a STANDALONE AI agent that reviews a GitHub PR diff using an external
LLM API. It is intentionally SEPARATE from the distro-deploy-listener workflow:
this runner only reads code and posts a review comment; it never builds or
deploys anything.

Flow:
  1. Fetch the PR diff + metadata from the GitHub API.
  2. Send the diff to an LLM (NVIDIA / OpenAI-compatible endpoint) for review.
  3. Post the model's review as a PR comment.

Secrets (set in repo Settings -> Secrets and variables -> Actions):
  GITHUB_TOKEN       auto-provided by Actions
  NVIDIA_API_KEY     (or VIBE_API_KEY) — LLM bearer token
  LLM_BASE_URL       optional override of the chat-completions endpoint
  LLM_MODEL          optional model name

Env inputs (from the workflow):
  REPO               owner/name
  PR_NUMBER          the PR to review

The runner degrades gracefully: if no LLM key is configured it posts a notice
and exits 0 (so the review job never red-blocks CI).
"""
import os
import sys
import json
import urllib.request
import urllib.error

GITHUB_API = "https://api.github.com"
REPO = os.environ["REPO"]
PR_NUMBER = os.environ["PR_NUMBER"]
TOKEN = os.environ["GITHUB_TOKEN"]

LLM_BASE_URL = os.environ.get(
    "LLM_BASE_URL",
    "https://integrate.api.nvidia.com/v1/chat/completions",
)
LLM_MODEL = os.environ.get("LLM_MODEL", "meta/llama-3.1-8b-instruct")
LLM_KEY = os.environ.get("NVIDIA_API_KEY") or os.environ.get("VIBE_API_KEY")


def github(path, method="GET", data=None):
    url = GITHUB_API + path
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "sovereign-ai-reviewer")
    if data is not None:
        req.add_header("Content-Type", "application/json")
        body = json.dumps(data).encode()
    else:
        body = None
    with urllib.request.urlopen(req, data=body, timeout=60) as r:
        return json.loads(r.read().decode())


def get_diff():
    # GitHub diff media type returns the raw patch.
    url = f"{GITHUB_API}/repos/{REPO}/pulls/{PR_NUMBER}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github.v3.diff")
    req.add_header("User-Agent", "sovereign-ai-reviewer")
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode()


def call_llm(diff_text, pr_title, pr_body):
    system = (
        "You are Sovereign-ULA's automated code-review agent. You review pull "
        "request diffs for an Android app (a UserLAnd fork rebranded "
        "dev.soveriegn.ula) and its Linux distro bootstrap scripts. Be concise "
        "and actionable. Structure your review EXACTLY as:\n"
        "## Critical\n- file:line — issue (fix)\n"
        "## Warnings\n- ...\n## Suggestions\n- ...\n## Looks Good\n- ...\n"
        "Focus on: correctness, security (no hardcoded secrets), shell/Kotlin "
        "bugs, missing wiring, and whether changes actually achieve their stated "
        "goal. Do not invent line numbers. If the diff is trivial, say so."
    )
    user = (
        f"PR: {pr_title}\n\nDescription:\n{pr_body or '(none)'}\n\n"
        f"DIFF (truncated to 24000 chars):\n{diff_text[:24000]}"
    )
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": 1500,
        "temperature": 0.2,
    }
    req = urllib.request.Request(LLM_BASE_URL, method="POST")
    req.add_header("Authorization", f"Bearer {LLM_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "sovereign-ai-reviewer")
    body = json.dumps(payload).encode()
    with urllib.request.urlopen(req, data=body, timeout=120) as r:
        resp = json.loads(r.read().decode())
    return resp["choices"][0]["message"]["content"].strip()


def main():
    if not LLM_KEY:
        notice = (
            "## AI Agent Review\n\n"
            "⚠️ No `NVIDIA_API_KEY` / `VIBE_API_KEY` secret is configured, so the "
            "AI review agent could not run. Add the secret in repo Settings → "
            "Secrets and variables → Actions to enable automatic LLM review."
        )
        github(f"/repos/{REPO}/issues/{PR_NUMBER}/comments", "POST",
               {"body": notice})
        print("No LLM key; posted notice and exited.")
        return

    pr = github(f"/repos/{REPO}/pulls/{PR_NUMBER}")
    diff = get_diff()
    print(f"Fetched diff ({len(diff)} chars) for PR #{PR_NUMBER}")

    review = call_llm(diff, pr.get("title", ""), pr.get("body", ""))
    comment = (
        "## 🤖 AI Agent Code Review (Sovereign-Ula)\n\n"
        f"_Model: `{LLM_MODEL}`_\n\n"
        f"{review}\n\n---\n*Automated gitapp-type LLM review runner.*"
    )
    github(f"/repos/{REPO}/issues/{PR_NUMBER}/comments", "POST", {"body": comment})
    print("Posted AI review comment.")


if __name__ == "__main__":
    main()
