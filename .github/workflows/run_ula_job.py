#!/usr/bin/env python3
"""Run the Gemini (gemma-4-31b-it) APK-edit job on the local ula-app.zip.
Real LLM call only -- reads GEMINI_API_KEY from env. No mock path.
Loads the LOCAL apk bytes (no Drive fetch from this env).
"""
import os, sys, base64, json

# local toolchain env so apktool/jarsigner could be invoked later
sys.path.insert(0, "/home/spiralgang/toolchain")

from google import genai
from google.genai import types

APK = "/storage/ula-app.zip"

def generate():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("FATAL: GEMINI_API_KEY not set (real LLM required).")
    client = genai.Client(api_key=key)

    # Gemini caps inline zip at 10MB; ula-app.zip is 15.1MB. Send the
    # manifest + decoded file tree instead (drives the requested edits).
    decoded = "/home/spiralgang/toolchain/work/ula_decoded/unknown/ula"
    manifest_path = os.path.join(decoded, "AndroidManifest.xml")
    with open(manifest_path, "r", errors="replace") as f:
        manifest = f.read()
    tree_lines = []
    for root, dirs, files in os.walk(decoded):
        rel_root = os.path.relpath(root, decoded)
        # keep manifest-relevant dirs only to shrink input
        if rel_root == "." or rel_root.split("/")[0] in (
            "res", "smali", "smali_classes2", "smali_classes3", "assets", "lib"
        ):
            for fn in files:
                tree_lines.append(os.path.relpath(os.path.join(root, fn), decoded))
    tree = "\n".join(sorted(tree_lines))
    print(f"[job] manifest {len(manifest)} chars; tree {len(tree_lines)} files", flush=True)

    model = "gemma-4-31b-it"
    prompt = (
        "edit my app's data, I only need a full settings page, the edge panel"
        "—where settings exists already, needs a full suite of all settings the"
        "app can ask from android, including direct access to shared storage"
        "downloads, and of course turn off pay billing settings, certificates of"
        "signing are mandatory, and enabling all its requests of manifest"
        "permissions.\n\n"
        "APP MANIFEST:\n```xml\n" + manifest + "\n```\n\n"
        "DECODED FILE TREE:\n```\n" + tree + "\n```"
    )
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        ),
    ]
    tools = [types.Tool(code_execution=types.ToolCodeExecution)]
    cfg = types.GenerateContentConfig(
        temperature=1.85,
        top_p=0.8,
        media_resolution="MEDIA_RESOLUTION_HIGH",
        tools=tools,
        response_mime_type="application/json",
        system_instruction=[
            types.Part.from_text(text=(
                "You are an expert Android engineer. Given an app's APK manifest "
                "and file tree, produce a precise, machine-applicable edit plan as "
                "JSON. Cover: full settings page, edge-panel settings suite, "
                "READ_EXTERNAL_STORAGE/MANAGE_EXTERNAL_STORAGE/WRITE_EXTERNAL_STORAGE "
                "+ Downloads access, disable billing/pay, mandatory signing cert, "
                "enable all manifest permissions the app requests. Respond ONLY "
                "valid JSON."
            ))
        ],
    )
    print("[job] calling gemma-4-31b-it ...", flush=True)
    resp = client.models.generate_content(
        model=model, contents=contents, config=cfg
    )
    # Capture ALL parts (text + code_execution results), not just resp.text,
    # because the model answer may live in non-text parts.
    parts_blob = []
    try:
        for p in resp.candidates[0].content.parts:
            if getattr(p, "text", None):
                parts_blob.append("[TEXT]\n" + p.text)
            if getattr(p, "executable_code", None):
                parts_blob.append("[CODE]\n" + (p.executable_code.code or ""))
            if getattr(p, "code_execution_result", None):
                parts_blob.append("[RESULT]\n" + (p.code_execution_result.output or ""))
    except Exception as e:
        parts_blob.append(f"[parse-warn] {e}")
    full = "\n\n".join(parts_blob)
    print("=== MODEL RESPONSE (first 6000 chars) ===")
    print(full[:6000])
    out = "/home/spiralgang/toolchain/work/gemma_edit_plan.json"
    with open(out, "w") as fh:
        fh.write(full)
    print(f"\n[job] full response ({len(full)} chars) written to {out}")
    return out

if __name__ == "__main__":
    generate()
