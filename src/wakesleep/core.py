"""SQLite-based, deterministic memory consolidation with provenance and gating.

Security note: all inputs are local, but the database is unencrypted at rest.
The `verified` flag is an operator declaration, not an independent fact check.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sqlite3
from pathlib import Path
from typing import Any


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def connect(path: str | Path) -> sqlite3.Connection:
    db = sqlite3.connect(str(path))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 5000")
    return db


def initialize(db: sqlite3.Connection) -> None:
    db.executescript("""
    CREATE TABLE IF NOT EXISTS observations (
        id INTEGER PRIMARY KEY,
        subject TEXT NOT NULL,
        predicate TEXT NOT NULL,
        value TEXT NOT NULL,
        source_id TEXT NOT NULL,
        verified INTEGER NOT NULL DEFAULT 0 CHECK(verified IN (0,1)),
        observed_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS ix_obs_subject_predicate
      ON observations(subject, predicate);
    CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY,
        subject TEXT NOT NULL,
        predicate TEXT NOT NULL,
        value TEXT NOT NULL,
        support INTEGER NOT NULL,
        sources_json TEXT NOT NULL,
        promoted_at TEXT NOT NULL,
        UNIQUE(subject, predicate)
    );
    CREATE TABLE IF NOT EXISTS cycles (
        id INTEGER PRIMARY KEY,
        ran_at TEXT NOT NULL,
        status TEXT NOT NULL,
        promoted INTEGER NOT NULL,
        updated INTEGER NOT NULL,
        quarantined INTEGER NOT NULL,
        eval_json TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS quarantines (
        id INTEGER PRIMARY KEY,
        cycle_id INTEGER NOT NULL REFERENCES cycles(id),
        subject TEXT NOT NULL,
        predicate TEXT NOT NULL,
        variants_json TEXT NOT NULL,
        reason TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS rehearsals (
        id INTEGER PRIMARY KEY,
        cycle_id INTEGER NOT NULL REFERENCES cycles(id),
        subject TEXT NOT NULL,
        predicate TEXT NOT NULL,
        question TEXT NOT NULL,
        expected TEXT NOT NULL,
        UNIQUE(cycle_id, subject, predicate)
    );
    CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
        subject, predicate, value, content='memories', content_rowid='id'
    );
    CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
      INSERT INTO memories_fts(rowid, subject, predicate, value)
      VALUES (new.id, new.subject, new.predicate, new.value);
    END;
    CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
      INSERT INTO memories_fts(memories_fts, rowid, subject, predicate, value)
      VALUES ('delete', old.id, old.subject, old.predicate, old.value);
    END;
    CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
      INSERT INTO memories_fts(memories_fts, rowid, subject, predicate, value)
      VALUES ('delete', old.id, old.subject, old.predicate, old.value);
      INSERT INTO memories_fts(rowid, subject, predicate, value)
      VALUES (new.id, new.subject, new.predicate, new.value);
    END;
    """)
    db.commit()


def ingest(db: sqlite3.Connection, records: list[dict[str, Any]]) -> int:
    """Append an explicit fact only; no LLM inference, and no implicit trust."""
    prepared: list[tuple[str, str, str, str, int, str]] = []
    for idx, row in enumerate(records, 1):
        if not isinstance(row, dict):
            raise ValueError(f"Observation {idx} must be an object")
        keys = ("subject", "predicate", "value", "source_id")
        if not all(isinstance(row.get(k), str) and row[k].strip() for k in keys):
            raise ValueError(f"Observation {idx} requires nonempty string fields {keys}")
        verified = row.get("verified", False)
        if not isinstance(verified, bool):
            raise ValueError(f"Observation {idx} verified must be boolean")
        timestamp = row.get("observed_at", now())
        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError(f"Observation {idx} observed_at must be a nonempty string")
        prepared.append(tuple(row[k].strip() for k in keys) + (int(verified), timestamp))
    with db:
        db.executemany(
            """INSERT INTO observations
               (subject, predicate, value, source_id, verified, observed_at)
               VALUES (?, ?, ?, ?, ?, ?)""", prepared
        )
    return len(prepared)


def recall(db: sqlite3.Connection, subject: str, predicate: str) -> dict[str, Any] | None:
    row = db.execute(
        "SELECT subject, predicate, value, support, sources_json, promoted_at "
        "FROM memories WHERE subject=? AND predicate=?", (subject, predicate)
    ).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["sources"] = json.loads(result.pop("sources_json"))
    return result


def search(db: sqlite3.Connection, query: str, limit: int = 5) -> list[dict[str, Any]]:
    # FTS5 MATCH is a query language. Build quoted tokens rather than passing
    # arbitrary user input as a raw MATCH expression.
    tokens = re.findall(r"\w+", query, flags=re.UNICODE)
    if not tokens:
        return []
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    match = " OR ".join('"' + t.replace('"', '""') + '"' for t in tokens[:20])
    rows = db.execute(
        """SELECT m.subject, m.predicate, m.value, m.support,
                  m.sources_json, bm25(memories_fts) AS rank
           FROM memories_fts JOIN memories m ON m.id = memories_fts.rowid
           WHERE memories_fts MATCH ? ORDER BY rank LIMIT ?""", (match, limit)
    ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["sources"] = json.loads(item.pop("sources_json"))
        result.append(item)
    return result


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{n}: invalid JSON: {e}") from e
            if not isinstance(entry, dict):
                raise ValueError(f"{path}:{n}: JSONL rows must be objects")
            records.append(entry)
    return records


def evaluate(db: sqlite3.Connection, golden: list[dict[str, Any]]) -> dict[str, Any]:
    """Exact-key retention check, not a language-model capability benchmark."""
    scores: dict[str, dict[str, int]] = {}
    for row in golden:
        cohort = row.get("cohort", "all")
        if cohort not in ("old", "new", "all"):
            raise ValueError("Golden row cohort must be old, new, or all")
        if not all(isinstance(row.get(k), str) for k in ("subject", "predicate")):
            raise ValueError("Golden rows require string subject and predicate")
        expected = row.get("expected")
        if expected is not None and not isinstance(expected, str):
            raise ValueError("Golden expected must be a string or null")
        answer = recall(db, row["subject"], row["predicate"])
        actual = answer["value"] if answer else None
        group = scores.setdefault(cohort, {"correct": 0, "total": 0})
        group["total"] += 1
        group["correct"] += int(actual == expected)
    return {
        label: {**values, "accuracy": values["correct"] / values["total"]}
        for label, values in scores.items()
    }


def sleep(
    db: sqlite3.Connection,
    golden: list[dict[str, Any]] | None = None,
    min_old_accuracy: float = 0.0,
    min_new_accuracy: float = 0.0,
) -> dict[str, Any]:
    """Promote single-valued facts with 2 distinct sources or explicit approval.

    Aborts changes on evaluation regression or unmet explicit thresholds.
    Conflicts are recorded even when the corresponding memory is left intact.
    A 'dream' here is only a deterministic rehearsal question, never a model update.
    """
    if not (0 <= min_old_accuracy <= 1 and 0 <= min_new_accuracy <= 1):
        raise ValueError("Accuracy thresholds must be between 0 and 1")
    golden = golden or []
    before = evaluate(db, golden)
    rows = db.execute(
        "SELECT subject, predicate, value, source_id, verified "
        "FROM observations ORDER BY id"
    ).fetchall()
    groups: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for row in rows:
        per_key = groups.setdefault((row["subject"], row["predicate"]), {})
        variant = per_key.setdefault(row["value"], {"sources": set(), "verified": False})
        variant["sources"].add(row["source_id"])
        variant["verified"] |= bool(row["verified"])

    promoted = updated = 0
    conflicts: list[dict[str, Any]] = []
    new_cycle = None
    # All memory edits are tentative until the quality gate passes.
    db.execute("SAVEPOINT tentative_sleep")
    try:
        for (subject, predicate), variants in sorted(groups.items()):
            if len(variants) > 1:
                conflicts.append({
                    "subject": subject, "predicate": predicate,
                    "variants": {v: sorted(info["sources"]) for v, info in sorted(variants.items())}
                })
                continue
            value, evidence = next(iter(variants.items()))
            sources = sorted(evidence["sources"])
            if not evidence["verified"] and len(sources) < 2:
                continue
            old = recall(db, subject, predicate)
            if old is None:
                db.execute(
                    """INSERT INTO memories
                    (subject, predicate, value, support, sources_json, promoted_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (subject, predicate, value, len(sources), json.dumps(sources), now())
                )
                promoted += 1
            elif old["value"] == value and (
                old["support"] != len(sources) or old["sources"] != sources
            ):
                db.execute(
                    """UPDATE memories SET support=?, sources_json=?
                       WHERE subject=? AND predicate=?""",
                    (len(sources), json.dumps(sources), subject, predicate)
                )
                updated += 1
            elif old["value"] != value:
                # Defensive branch if an operator changed the staging set externally.
                conflicts.append({
                    "subject": subject, "predicate": predicate,
                    "variants": {old["value"]: old["sources"], value: sources}
                })

        after = evaluate(db, golden)
        before_old = before.get("old", {}).get("accuracy", 0.0)
        after_old = after.get("old", {}).get("accuracy", 0.0)
        after_new = after.get("new", {}).get("accuracy", 0.0)
        has_old = "old" in after
        has_new = "new" in after
        passed = (not has_old or (after_old >= before_old and after_old >= min_old_accuracy)) \
            and (not has_new or after_new >= min_new_accuracy)
        # For a requested threshold, require actual cohort tests, not a vacuous pass.
        if min_old_accuracy and not has_old or min_new_accuracy and not has_new:
            passed = False

        if not passed:
            db.execute("ROLLBACK TO SAVEPOINT tentative_sleep")
            promoted = updated = 0
        db.execute("RELEASE SAVEPOINT tentative_sleep")
        status = "accepted" if passed else "rejected"
        cursor = db.execute(
            """INSERT INTO cycles
               (ran_at, status, promoted, updated, quarantined, eval_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (now(), status, promoted, updated, len(conflicts),
             json.dumps({"before": before, "after": after}, ensure_ascii=False))
        )
        new_cycle = cursor.lastrowid
        for conflict in conflicts:
            variants_json = json.dumps(conflict["variants"], ensure_ascii=False)
            # Record each distinct conflict once; repeated sleep cycles over the
            # same unresolved contradiction must not inflate the quarantine log.
            already = db.execute(
                "SELECT 1 FROM quarantines WHERE subject=? AND predicate=? AND variants_json=?",
                (conflict["subject"], conflict["predicate"], variants_json)
            ).fetchone()
            if already:
                continue
            db.execute(
                """INSERT INTO quarantines
                   (cycle_id, subject, predicate, variants_json, reason)
                   VALUES (?, ?, ?, ?, ?)""",
                (new_cycle, conflict["subject"], conflict["predicate"],
                 variants_json, "contradictory_observations")
            )
        if passed:
            # Replay of approved memories, with no invented new facts.
            for row in db.execute("SELECT subject, predicate, value FROM memories ORDER BY id").fetchall():
                db.execute(
                    """INSERT INTO rehearsals
                       (cycle_id, subject, predicate, question, expected)
                       VALUES (?, ?, ?, ?, ?)""",
                    (new_cycle, row["subject"], row["predicate"],
                     f"Quelle est la valeur de « {row['predicate']} » pour « {row['subject']} » ?",
                     row["value"])
                )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {
        "cycle_id": new_cycle, "status": status, "promoted": promoted,
        "updated": updated, "quarantined": len(conflicts),
        "evaluation_before": before, "evaluation_after": after,
    }


def rehearsals(db: sqlite3.Connection, cycle_id: int | None = None) -> list[dict[str, Any]]:
    if cycle_id is None:
        row = db.execute("SELECT MAX(id) AS id FROM cycles WHERE status='accepted'").fetchone()
        cycle_id = row["id"]
    if cycle_id is None:
        return []
    return [dict(r) for r in db.execute(
        "SELECT subject, predicate, question, expected FROM rehearsals WHERE cycle_id=? ORDER BY id",
        (cycle_id,)
    )]


def stats(db: sqlite3.Connection) -> dict[str, int]:
    return {
        table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("observations", "memories", "cycles", "quarantines", "rehearsals")
    }
