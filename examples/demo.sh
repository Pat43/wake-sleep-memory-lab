#!/usr/bin/env bash
set -euo pipefail
DB="${1:-demo.db}"
rm -f "$DB"
wakesleep --db "$DB" init
wakesleep --db "$DB" ingest examples/day1.jsonl
wakesleep --db "$DB" sleep
wakesleep --db "$DB" ingest examples/day2.jsonl
wakesleep --db "$DB" sleep --golden examples/golden.jsonl --min-old 1 --min-new 1
wakesleep --db "$DB" evaluate examples/golden.jsonl
wakesleep --db "$DB" search 'développement'
wakesleep --db "$DB" rehearsal --output rehearsal.jsonl
wakesleep --db "$DB" stats
