"""Hermes LLM client — multi-provider, keyed by environment variables only.

Provider selection (env, in order of precedence):
  LLM_PROVIDER=nvidia|gemini   explicit choice
  else NVIDIA_API_KEY set      -> NVIDIA NIM (nemotron reasoning model)
  else GEMINI_API_KEY set      -> Google GenAI free tier (gemini-2.5-flash)

GenAI (Google, free tier):
  GEMINI_API_KEY   — AI Studio key (https://aistudio.google.com/apikey)
  GENAI_MODEL      — default "gemini-2.5-flash"; streaming supported via the
                     google-genai SDK (optional dependency; degrade gracefully)
NVIDIA (NIM):
  NVIDIA_API_KEY   — build.nvidia.com key
  matches the repo's existing LLM settings: nemotron-3-nano-omni-30b-a3b-
  reasoning, 64k max tokens, 16k reasoning budget.

Keys are NEVER hardcoded or committed. complete() is the non-streaming call
used by planner/refactor/jobs; pass stream=True to stream tokens to stdout
(live terminal + Actions logs) and still return the full text.
"""
import os
import time

import requests

NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NIM_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
NIM_MAX_TOKENS = 65536
NIM_REASONING_BUDGET = 16384
TEMPERATURE = 0.6
TOP_P = 0.95
API_RETRIES = 4

DEFAULT_GENAI_MODEL = "gemini-2.5-flash"

try:
    from google import genai  # type: ignore  # noqa: E402

    _GENAI_IMPORTABLE = True
except Exception:  # noqa: BLE001 — optional dependency
    _GENAI_IMPORTABLE = False


def provider() -> str:
    """Resolve which backend will be used: 'nvidia' | 'gemini' | '' (none)."""
    explicit = (os.environ.get("LLM_PROVIDER") or "").strip().lower()
    if explicit in ("nvidia", "gemini"):
        return explicit
    if os.environ.get("NVIDIA_API_KEY"):
        return "nvidia"
    if os.environ.get("GEMINI_API_KEY") and _GENAI_IMPORTABLE:
        return "gemini"
    return ""


def available() -> bool:
    """True when a key (+ importable SDK for gemini) is present so the runner
    can degrade gracefully to static-analysis-only."""
    p = provider()
    if p == "nvidia":
        return bool(os.environ.get("NVIDIA_API_KEY"))
    if p == "gemini":
        return bool(os.environ.get("GEMINI_API_KEY")) and _GENAI_IMPORTABLE
    return False


def _gemini_client():
    from google import genai

    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def _gemini_model() -> str:
    return os.environ.get("GENAI_MODEL", DEFAULT_GENAI_MODEL).strip() or DEFAULT_GENAI_MODEL


def complete(system: str, user: str, timeout: int = 300, stream: bool = False) -> str:
    """Single completion. Raises RuntimeError after retries. stream=True prints
    tokens to stdout as they arrive (Actions logs) and still returns the text."""
    p = provider()
    if p == "gemini":
        if not os.environ.get("GEMINI_API_KEY"):
            raise RuntimeError("GEMINI_API_KEY is not set (AI Studio free-tier key)")
        if not _GENAI_IMPORTABLE:
            raise RuntimeError("google-genai SDK not installed (pip install google-genai)")
        return _gemini_complete(system, user, timeout=timeout, stream=stream)
    if p == "nvidia":
        if not os.environ.get("NVIDIA_API_KEY"):
            raise RuntimeError("NVIDIA_API_KEY is not set (build.nvidia.com key)")
        return _nim_complete(system, user, timeout=timeout)
    raise RuntimeError(
        "no LLM key set: export NVIDIA_API_KEY (NIM) or GEMINI_API_KEY (GenAI free tier)"
    )


# --------------------------------------------------------------------------
# Google GenAI (free tier, streaming)
# --------------------------------------------------------------------------

def _gemini_complete(system: str, user: str, timeout: int, stream: bool) -> str:
    if not _GENAI_IMPORTABLE:
        raise RuntimeError("google-genai SDK not installed (pip install google-genai)")
    from google.genai import types

    client = _gemini_client()
    config = types.GenerateContentConfig(
        system_instruction=system,
        temperature=TEMPERATURE,
        max_output_tokens=32768,
    )
    contents = [{"role": "user", "content": user}]
    last_err = None
    for attempt in range(1, API_RETRIES + 1):
        try:
            if stream:
                chunks = []
                for chunk in client.models.generate_content_stream(
                    model=_gemini_model(), contents=contents, config=config
                ):
                    tok = chunk.text or ""
                    if tok:
                        chunks.append(tok)
                        print(tok, end="", flush=True)
                print()
                return "".join(chunks)
            resp = client.models.generate_content(
                model=_gemini_model(), contents=contents, config=config
            )
            return (resp.text or "").strip()
        except Exception as err:  # noqa: BLE001 — SDK raises typed errors; retry uniformly
            last_err = err
            if "429" in str(err) or "ResourceExhausted" in str(err):
                # free-tier rate limit — back off longer, up to ~1 min total
                wait = min(2 ** attempt * 4, 45)
            else:
                wait = 2 ** attempt * 3
            print(f"  [hermes] ⚠ GenAI error ({err}); retry {attempt}/{API_RETRIES} in {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"GenAI API unreachable after {API_RETRIES} retries: {last_err}")


# --------------------------------------------------------------------------
# NVIDIA NIM (existing behavior, unchanged)
# --------------------------------------------------------------------------

def _nim_complete(system: str, user: str, timeout: int) -> str:
    headers = {
        "Authorization": f"Bearer {os.environ['NVIDIA_API_KEY']}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "model": NIM_MODEL,
        "max_tokens": NIM_MAX_TOKENS,
        "reasoning_budget": NIM_REASONING_BUDGET,
        "stream": False,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    last_err = None
    for attempt in range(1, API_RETRIES + 1):
        try:
            resp = requests.post(NIM_URL, headers=headers, json=payload, timeout=timeout)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except (requests.RequestException, KeyError, IndexError, ValueError) as err:
            last_err = err
            wait = 2 ** attempt * 3
            print(f"  [hermes] ⚠ NIM API error ({err}); retry {attempt}/{API_RETRIES} in {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"NIM API unreachable after {API_RETRIES} retries: {last_err}")
