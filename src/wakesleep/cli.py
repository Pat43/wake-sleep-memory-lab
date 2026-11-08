"""Small standard-library-only command-line interface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from .core import connect, evaluate, ingest, initialize, load_jsonl, recall, rehearsals, search, sleep, stats


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="wakesleep", description="Auditable local wake/sleep memory lab (not neural fine-tuning)"
    )
    parser.add_argument("--db", default="wakesleep.db", help="Local SQLite path (default: wakesleep.db)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Create the local SQLite schema")
    p_ingest = commands.add_parser("ingest", help="Append JSONL observations")
    p_ingest.add_argument("file", type=Path)
    p_sleep = commands.add_parser("sleep", help="Consolidate observations using a quality gate")
    p_sleep.add_argument("--golden", type=Path, help="Evaluation set: JSONL rows of old/new facts")
    p_sleep.add_argument("--min-old", type=float, default=0.0, help="Minimum old cohort accuracy")
    p_sleep.add_argument("--min-new", type=float, default=0.0, help="Minimum new cohort accuracy")
    p_recall = commands.add_parser("recall", help="Retrieve one verified consolidated key")
    p_recall.add_argument("subject")
    p_recall.add_argument("predicate")
    p_search = commands.add_parser("search", help="FTS5 search of consolidated memories")
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=5)
    p_eval = commands.add_parser("evaluate", help="Exact-key regression checks")
    p_eval.add_argument("golden", type=Path)
    p_dream = commands.add_parser("rehearsal", help="Export rehearsal Q&A from last accepted cycle")
    p_dream.add_argument("--output", type=Path, help="Optional JSONL output path")
    commands.add_parser("stats", help="Show local record counts")
    args = parser.parse_args()

    with connect(args.db) as db:
        initialize(db)
        if args.command == "init":
            result = {"database": args.db, "initialized": True}
        elif args.command == "ingest":
            result = {"ingested": ingest(db, load_jsonl(args.file))}
        elif args.command == "sleep":
            golden = load_jsonl(args.golden) if args.golden else []
            result = sleep(db, golden, args.min_old, args.min_new)
        elif args.command == "recall":
            result = recall(db, args.subject, args.predicate)
        elif args.command == "search":
            result = search(db, args.query, args.limit)
        elif args.command == "evaluate":
            result = evaluate(db, load_jsonl(args.golden))
        elif args.command == "rehearsal":
            result = rehearsals(db)
            if args.output:
                with args.output.open("w", encoding="utf-8") as handle:
                    for item in result:
                        handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        else:
            result = stats(db)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
