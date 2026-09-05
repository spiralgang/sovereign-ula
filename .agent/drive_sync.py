"""Hermes Drive backup + report composition.

Transport layer for run reports:

  compose_report(...)  -> markdown report text (single source of truth for the
                          run log; the runner writes it to .agent/logs/ AND
                          hands it to upload_report)
  upload_report(...)   -> best-effort Google Drive upload of that text

Credentials come from env vars ONLY:
  GDRIVE_CREDENTIALS  — base64-encoded Google service-account JSON (required
                        to enable uploads; without it everything is a no-op)
  GDRIVE_FOLDER_ID    — destination Drive folder id. Optional: when missing
                        we find-or-create a folder named GDRIVE_FOLDER_NAME
                        (default "hermes-run-reports") under the service
                        account's own Drive root.
  GDRIVE_FOLDER_NAME  — optional folder-name override

Missing creds / missing google packages / API failures are logged, never
fatal: a Drive hiccup must not kill an agent cycle. Share the target Drive
folder with the service account's email or uploads will 403.

Setup (see .agent/ARCHITECTURE.md for the full walkthrough):
  1. console.cloud.google.com -> create a service account
  2. enable the Google Drive API for that project
  3. create a JSON key for the account, then locally:
       base64 -w0 sa-key.json        # paste output into GDRIVE_CREDENTIALS
  4. (optional) create a Drive folder and put its id in GDRIVE_FOLDER_ID;
     otherwise the folder is auto-created on first upload.
"""
import base64
import io
import json
import os
from datetime import datetime, timezone

FOLDER_MIME = "application/vnd.google-apps.folder"


# --------------------------------------------------------------------------
# Env / capability checks
# --------------------------------------------------------------------------

def enabled() -> bool:
    """True when a Drive backup is possible (creds set AND libs importable)."""
    if not os.environ.get("GDRIVE_CREDENTIALS"):
        return False
    try:
        from google.oauth2 import service_account  # noqa: F401
        from googleapiclient.discovery import build  # noqa: F401
    except ImportError:
        return False
    return True


def _log(msg: str) -> None:
    print(f"[hermes] {msg}", flush=True)


# --------------------------------------------------------------------------
# Service + folder resolution
# --------------------------------------------------------------------------

def _build_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds_json = json.loads(base64.b64decode(os.environ["GDRIVE_CREDENTIALS"]))
    creds = service_account.Credentials.from_service_account_info(
        creds_json, scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _folder_name() -> str:
    return os.environ.get("GDRIVE_FOLDER_NAME", "hermes-run-reports")


def _resolve_folder(svc) -> str:
    """Return the target folder id: env override, else find-or-create."""
    explicit = os.environ.get("GDRIVE_FOLDER_ID")
    if explicit:
        return explicit
    name = _folder_name()
    safe = name.replace("'", "\\'")
    query = (
        f"name='{safe}' and mimeType='{FOLDER_MIME}' and trashed=false"
    )
    found = (
        svc.files()
        .list(q=query, fields="files(id)", pageSize=10)
        .execute()
        .get("files", [])
    )
    if found:
        return found[0]["id"]
    created = (
        svc.files()
        .create(body={"name": name, "mimeType": FOLDER_MIME}, fields="id")
        .execute()
    )
    _log(f"📁 created Drive folder '{name}' ({created['id']})")
    return created["id"]


# --------------------------------------------------------------------------
# Report composition (single source of truth for the run log)
# --------------------------------------------------------------------------

def compose_report(
    mode: str,
    analysis: dict,
    plan: dict,
    results: list,
    state: dict,
    verify_failures: list,
    refactor_results: list | None = None,
    trends: dict | None = None,
    job: dict | None = None,
) -> str:
    """Render the full markdown run report for logs + Drive."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    plan = plan or {}
    refactor_results = refactor_results or []
    lines = [
        f"# Hermes Run Report — {now}",
        "",
        f"- mode: `{mode}`",
        f"- head: `{analysis.get('head')}`",
        f"- findings: {len(analysis.get('findings', []))}",
        f"- secrets flagged: {len(analysis.get('secrets', []))}",
        f"- run #: {state.get('runs', 0)}",
        "",
        "## Findings",
        "",
    ]
    for f in analysis.get("findings", [])[:30]:
        lines.append(f"- [{f['severity']}] {f['type']}: `{f['file']}` — {f['message']}")
    lines += ["", "## Secrets (never auto-fixed)", ""]
    for s in analysis.get("secrets", [])[:10]:
        lines.append(f"- {s['file']}:{s.get('line', '?')} — {s['message']}")
    lines += ["", "## Plan", "", f"- title: {plan.get('title', 'noop')}"]
    lines.append(f"- description: {plan.get('description', plan.get('reason', ''))}")
    if refactor_results:
        lines += ["", "## Refactor engine", ""]
        for r in refactor_results:
            note = r.get("message", "")
            ffile = r.get("file") or r.get("finding", {}).get("file", "?")
            lines.append(f"- {r.get('status')}: `{ffile}` — {note}")
    if results:
        lines += ["", "## Commands executed", ""]
        for r in results:
            lines.append(f"- `{r['command']}` → rc={r.get('rc', 'blocked')}")
    if verify_failures:
        lines += ["", "## Verify failures (changes reverted)", ""]
        for f in verify_failures:
            lines.append(f"- `{f['file']}` — {f['message']}")
    if job and job.get("status") != "done":
        lines += ["", "## Job (verify-until-green)", ""]
        lines.append(f"- slug: `{job.get('slug')}`")
        lines.append(f"- title: {job.get('title')}")
        lines.append(f"- status: {job.get('status')}")
        lines.append(f"- pulses: {job.get('pulses')} / {job.get('max_pulses')}")
        lines.append(f"- repairs this pulse: {job.get('repairs_used')} / {job.get('pulse_budget')}")
        if job.get("blocked_reason"):
            lines.append(f"- blocked reason: {job.get('blocked_reason')}")
        for err in job.get("last_errors", [])[:5]:
            first = err.splitlines()[0] if err.splitlines() else err
            lines.append(f"- failure: {first[:200]}")
    if trends:
        lines += ["", "## Knowledge / trends", ""]
        lines.append(f"- total runs: {trends.get('total_runs', 0)}")
        lines.append(f"- avg findings: {trends.get('avg_findings', '-')}")
        lines.append(f"- trend: {trends.get('trend', 'stable')}")
    lines += ["", "## Backlog (next runs)", ""]
    for item in state.get("backlog", [])[-15:]:
        lines.append(f"- {item}")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Upload
# --------------------------------------------------------------------------

def upload_report(text: str, filename: str) -> str | None:
    """Upload markdown text to Drive. Returns the file id or None.

    No-op (returns None, logs once) when creds are missing — run reports
    still land in .agent/logs/ either way.
    """
    if not os.environ.get("GDRIVE_CREDENTIALS"):
        return None
    try:
        from googleapiclient.http import MediaIoBaseUpload

        svc = _build_service()
        folder_id = _resolve_folder(svc)
        media = MediaIoBaseUpload(
            io.BytesIO(text.encode("utf-8")), mimetype="text/markdown"
        )
        file_id = (
            svc.files()
            .create(
                body={"name": filename, "parents": [folder_id]},
                media_body=media,
                fields="id",
            )
            .execute()["id"]
        )
        _log(f"✓ report backed up to Drive (folder {folder_id}, file {file_id})")
        return file_id
    except Exception as err:  # noqa: BLE001 — never let backup kill a run
        _log(f"⚠ Drive upload failed: {err}")
        return None
