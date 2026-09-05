"""Hermes knowledge base — cross-run learning.

Durability problem: Actions workspaces are ephemeral, so the durable store is
`.agent/history.jsonl` (one JSON line per run) which the runner COMMITS to the
`hermes-autonomous` branch after every cycle. A text log merges cleanly.

Each run we rebuild a queryable SQLite mirror (`.agent/knowledge.db`) from that
log and expose trend queries — blueprint-style runs/findings/future_work
tables, regenerated on every cycle so the binary DB never needs committing.
"""
import json
import sqlite3
from pathlib import Path

AGENT = Path(__file__).resolve().parent
HISTORY_PATH = AGENT / "history.jsonl"
DB_PATH = AGENT / "knowledge.db"

# Cap the durable log: every run appends a full findings snapshot, and the
# runner runs 48x/day — prune oldest records past the cap so the branch and
# the SQLite mirror both stay bounded. Trends are computed over the retained
# window (a few hundred runs is plenty of signal).
HISTORY_MAX_LINES = 600
HISTORY_KEEP_LINES = 300

_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY,
        ts TEXT,
        head TEXT,
        mode TEXT,
        findings_count INTEGER,
        secrets_count INTEGER,
        applied_count INTEGER,
        backlog_size INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS findings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT,
        type TEXT,
        severity TEXT,
        file TEXT,
        message TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS future_work (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT,
        title TEXT,
        priority_score REAL
    )
    """,
]


def append_run(record: dict) -> None:
    """Append one run record to the durable JSONL history, pruning old runs."""
    AGENT.mkdir(exist_ok=True)
    HISTORY_PATH.open("a", encoding="utf-8").write(json.dumps(record) + "\n")
    records = load_records()
    if len(records) > HISTORY_MAX_LINES:
        keep = records[-HISTORY_KEEP_LINES:]
        with HISTORY_PATH.open("w", encoding="utf-8") as handle:
            for rec in keep:
                handle.write(json.dumps(rec) + "\n")
        _log(f"pruned history.jsonl to last {len(keep)} runs")


def _log(msg: str) -> None:
    print(f"[knowledge] {msg}", flush=True)


def load_records() -> list:
    if not HISTORY_PATH.exists():
        return []
    records = []
    for line in HISTORY_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _rebuild_db(records: list) -> None:
    """Regenerate the SQLite mirror from the durable JSONL log."""
    conn = sqlite3.connect(DB_PATH)
    for stmt in _SCHEMA:
        conn.execute(stmt)
    conn.execute("DELETE FROM runs")
    conn.execute("DELETE FROM findings")
    conn.execute("DELETE FROM future_work")
    for rec in records:
        conn.execute(
            "INSERT INTO runs (run_id, ts, head, mode, findings_count, secrets_count, applied_count, backlog_size) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                rec.get("run_id", ""), rec.get("ts", ""), rec.get("head", ""),
                rec.get("mode", ""), len(rec.get("findings", [])),
                rec.get("secrets_count", 0), len(rec.get("applied", [])),
                len(rec.get("backlog", [])),
            ),
        )
        for finding in rec.get("findings", [])[:50]:
            conn.execute(
                "INSERT INTO findings (run_id, type, severity, file, message) VALUES (?, ?, ?, ?, ?)",
                (rec.get("run_id", ""), finding.get("type", ""), finding.get("severity", ""),
                 finding.get("file", ""), finding.get("message", "")[:200]),
            )
        for task in rec.get("backlog", [])[-10:]:
            conn.execute(
                "INSERT INTO future_work (run_id, title, priority_score) VALUES (?, ?, ?)",
                (rec.get("run_id", ""), str(task)[:200], 0.0),
            )
    conn.commit()
    conn.close()


def get_trends() -> dict:
    """Return aggregate trend stats across all recorded runs."""
    records = load_records()
    if not records:
        return {}
    _rebuild_db(records)
    conn = sqlite3.connect(DB_PATH)
    total_runs = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    avg_findings = conn.execute("SELECT AVG(findings_count) FROM runs").fetchone()[0] or 0.0
    avg_applied = conn.execute("SELECT AVG(applied_count) FROM runs").fetchone()[0] or 0.0
    top_types = conn.execute(
        "SELECT type, COUNT(*) FROM findings GROUP BY type ORDER BY COUNT(*) DESC LIMIT 5"
    ).fetchall()
    recent = conn.execute(
        "SELECT findings_count FROM runs ORDER BY ts DESC LIMIT 6"
    ).fetchall()
    conn.close()

    recent_counts = [r[0] for r in reversed(recent)]
    if len(recent_counts) >= 4:
        older = sum(recent_counts[: len(recent_counts) // 2]) / max(1, len(recent_counts) // 2)
        newer = sum(recent_counts[len(recent_counts) // 2:]) / max(1, len(recent_counts) - len(recent_counts) // 2)
        trend = "improving" if newer < older else ("worsening" if newer > older else "stable")
    else:
        trend = "stable"
    return {
        "total_runs": total_runs,
        "avg_findings": round(avg_findings, 1),
        "avg_applied_per_run": round(avg_applied, 1),
        "top_finding_types": [{"type": t, "count": c} for t, c in top_types],
        "trend": trend,
    }


def most_recent_run_id() -> str:
    records = load_records()
    return records[-1].get("run_id", "") if records else ""