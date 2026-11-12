from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

VALID_STATUSES = {"queued", "running", "succeeded", "failed"}


def normalize(row: dict) -> dict:
    started_at = datetime.fromisoformat(str(row["started_at"]).replace("Z", "+00:00")).isoformat()
    parameters = row.get("parameters", {})
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be an object")
    status = str(row["status"]).lower().strip()
    if status not in VALID_STATUSES:
        raise ValueError("unsupported run status")
    artifacts = row.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise ValueError("artifacts must be a list")
    for artifact in artifacts:
        if not all(key in artifact for key in ("name", "uri", "sha256")):
            raise ValueError("artifact requires name, uri, and sha256")
    payload = {"dataset_id": str(row["dataset_id"]), "code_revision": str(row["code_revision"]), "parameters": parameters}
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "run_id": str(row["run_id"]),
        "dataset_id": payload["dataset_id"],
        "code_revision": payload["code_revision"],
        "parameters_json": json.dumps(parameters, sort_keys=True),
        "started_at": started_at,
        "status": status,
        "parent_run_id": row.get("parent_run_id"),
        "fingerprint": fingerprint,
        "artifacts": artifacts,
    }


def _schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL, code_revision TEXT NOT NULL,
            parameters_json TEXT NOT NULL, started_at TEXT NOT NULL, status TEXT NOT NULL,
            parent_run_id TEXT, fingerprint TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS artifacts (
            run_id TEXT NOT NULL, name TEXT NOT NULL, uri TEXT NOT NULL, sha256 TEXT NOT NULL,
            PRIMARY KEY(run_id, name)
        );
        CREATE TABLE IF NOT EXISTS lineage (
            parent_run_id TEXT NOT NULL, child_run_id TEXT NOT NULL, PRIMARY KEY(parent_run_id, child_run_id)
        );
        CREATE TABLE IF NOT EXISTS rejected_runs (
            run_id TEXT, reason TEXT NOT NULL, raw_json TEXT NOT NULL
        );
        """
    )


def run_pipeline(records: Iterable[dict], database: str | Path) -> dict[str, int]:
    conn = sqlite3.connect(database)
    _schema(conn)
    accepted = rejected = duplicates = 0
    for raw in records:
        try:
            run = normalize(raw)
            values = tuple(run[key] for key in ("run_id", "dataset_id", "code_revision", "parameters_json", "started_at", "status", "parent_run_id", "fingerprint"))
            cur = conn.execute("INSERT OR IGNORE INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)", values)
            if cur.rowcount:
                accepted += 1
                for artifact in run["artifacts"]:
                    conn.execute("INSERT OR REPLACE INTO artifacts VALUES (?, ?, ?, ?)", (run["run_id"], artifact["name"], artifact["uri"], artifact["sha256"]))
                if run["parent_run_id"]:
                    conn.execute("INSERT OR IGNORE INTO lineage VALUES (?, ?)", (run["parent_run_id"], run["run_id"]))
            else:
                duplicates += 1
        except (KeyError, TypeError, ValueError) as exc:
            rejected += 1
            conn.execute("INSERT INTO rejected_runs VALUES (?, ?, ?)", (str(raw.get("run_id")), str(exc), json.dumps(raw, sort_keys=True)))
    fingerprints = conn.execute("SELECT count(distinct fingerprint) FROM runs").fetchone()[0]
    total = conn.execute("SELECT count(*) FROM runs").fetchone()[0]
    conn.commit()
    conn.close()
    return {"accepted": accepted, "rejected": rejected, "duplicates": duplicates, "runs": total, "distinct_fingerprints": fingerprints}
