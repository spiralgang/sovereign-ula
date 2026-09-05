#!/usr/bin/env python3
"""
Run the Gemini (gemma-4-31b-it) APK-edit job on a locally decoded APK tree.
This wrapper expects GEMINI_API_KEY in the environment and a decoded APK
filesystem present under /home/spiralgang/toolchain/work/ula_decoded/unknown/ula.

Behavior changes from the original:
- Validate inputs (APK file, decoded tree, manifest presence).
- Fail fast with clear messages if prerequisites are missing.
- Limit the manifest/tree payload size to avoid very large LLM inputs.
- Capture and persist the raw model response for later inspection.
- Use conservative defaults and robust error handling around the model call.
"""
import os
import sys
import json
import time
from typing import List

APK = os.environ.get("ULA_LOCAL_APK", "/storage/ula-app.zip")
DECODED_DIR = os.path.join("/home/spiralgang/toolchain/work/ula_decoded/unknown/ula")
OUT_PLAN = os.path.join("/home/spiralgang/toolchain/work/gemma_edit_plan.json")

# Limit sizes to keep requests within provider limits
MAX_MANIFEST_CHARS = 200_000
MAX_TREE_ENTRIES = 25_000


def fail(msg: str, code: int = 1):
    print(f"FATAL: {msg}", file=sys.stderr)
    sys.exit(code)


def gather_manifest(decoded_path: str) -> str:
    manifest_path = os.path.join(decoded_path, "AndroidManifest.xml")
    if not os.path.isfile(manifest_path):
        fail(f"Decoded manifest not found at: {manifest_path}")
    with open(manifest_path, "r", errors="replace", encoding="utf-8") as fh:
        manifest = fh.read()
    if len(manifest) > MAX_MANIFEST_CHARS:
        print("[warn] manifest exceeds size limit; truncating input to model")
        manifest = manifest[:MAX_MANIFEST_CHARS]
    return manifest


def gather_tree(decoded_path: str) -> List[str]:
    tree_lines = []
    for root, dirs, files in os.walk(decoded_path):
        rel_root = os.path.relpath(root, decoded_path)
        # keep manifest-relevant dirs only to shrink input
        top = rel_root.split(os.sep)[0] if rel_root != "." else "."
        if top in (".", "res", "smali", "smali_classes2", "smali_classes3", "assets", "lib"):
            for fn in files:
                tree_lines.append(os.path.relpath(os.path.join(root, fn), decoded_path))
        if len(tree_lines) >= MAX_TREE_ENTRIES:
            print("[warn] file tree exceeds MAX_TREE_ENTRIES; truncating list")
            break
    return sorted(tree_lines)


def main():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        fail("GEMINI_API_KEY not set in environment")

    if not os.path.isfile(APK):
        print(f"[warn] APK not found at {APK}; continuing with decoded tree if present")

    if not os.path.isdir(DECODED_DIR):
        fail(f"Decoded APK tree not found at: {DECODED_DIR}")

    manifest = gather_manifest(DECODED_DIR)
    tree_items = gather_tree(DECODED_DIR)

    print(f"[job] manifest {len(manifest)} chars; tree {len(tree_items)} files", flush=True)

    # Import locally to avoid failing at import time when SDK not present
    try:
        from google import genai
        from google.genai import types
    except Exception as e:
        fail(f"Google GenAI SDK import failed: {e}")

    client = genai.Client(api_key=key)

    model = "gemma-4-31b-it"
    prompt = (
        "Edit my app's data. Produce a precise, machine-applicable edit plan in JSON. "
        "Include: a full settings page, the edge panel settings suite, manifest changes "
        "to request external storage + Downloads access, disable billing/pay, require a signing cert, "
        "and enable/declare any permissions the app uses. Respond ONLY with valid JSON.\n\n"
        "APP MANIFEST:\n````xml\n" + manifest + "\n```\n\n"
        "DECODED FILE TREE:\n```\n" + "\n".join(tree_items[:MAX_TREE_ENTRIES]) + "\n```"
    )

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        ),
    ]

    # Tools: keep minimum config; code-execution may be included by model but not required.
    tools = [types.Tool(code_execution=types.ToolCodeExecution)]

    cfg = types.GenerateContentConfig(
        temperature=0.7,
        top_p=0.95,
        media_resolution="MEDIA_RESOLUTION_HIGH",
        tools=tools,
        response_mime_type="application/json",
        system_instruction=[
            types.Part.from_text(text=(
                "You are an expert Android engineer. Given an app's APK manifest "
                "and file tree, produce a precise, machine-applicable edit plan as JSON. "
                "Cover: full settings page, edge-panel settings suite, storage permissions, "
                "disable billing/pay, require signing cert, and enable requested manifest permissions. "
                "Respond ONLY with valid JSON. Do not include explanatory prose outside the JSON."
            ))]
    )

    print("[job] calling gemma-4-31b-it ...", flush=True)
    try:
        resp = client.models.generate_content(model=model, contents=contents, config=cfg)
    except Exception as e:
        fail(f"LLM call failed: {e}")

    # Capture response parts robustly
    parts_blob = []
    try:
        for p in resp.candidates[0].content.parts:
            if getattr(p, "text", None):
                parts_blob.append(p.text)
            if getattr(p, "executable_code", None):
                parts_blob.append(p.executable_code.code or "")
            if getattr(p, "code_execution_result", None):
                parts_blob.append(p.code_execution_result.output or "")
    except Exception as e:
        parts_blob.append(f"[parse-warn] {e}")

    full = "\n\n".join(parts_blob)
    print("=== MODEL RESPONSE (first 6000 chars) ===")
    print(full[:6000])

    # Persist the full response for manual inspection and as a JSON plan if possible
    try:
        with open(OUT_PLAN, "w", encoding="utf-8") as fh:
            fh.write(full)
        print(f"[job] full response ({len(full)} chars) written to {OUT_PLAN}")
    except Exception as e:
        fail(f"Failed to write output plan: {e}")

    # Attempt to parse the first JSON object in the response for automated use
    try:
        # naive: find first '{' and last '}' and parse
        start = full.index('{')
        end = full.rindex('}')
        candidate = full[start:end+1]
        parsed = json.loads(candidate)
        parsed_out = OUT_PLAN.replace('.json', '.parsed.json')
        with open(parsed_out, 'w', encoding='utf-8') as fh:
            json.dump(parsed, fh, indent=2)
        print(f"[job] parsed JSON plan written to {parsed_out}")
    except Exception:
        print("[warn] could not parse a JSON plan from the model response; manual inspection required")

    return OUT_PLAN


if __name__ == '__main__':
    main()
