import tempfile
import unittest
from pathlib import Path

from wakesleep.core import (connect, evaluate, ingest, initialize, load_jsonl,
                            recall, rehearsals, search, sleep, stats)


class WakeSleepTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = connect(Path(self.temp.name) / "test.sqlite")
        initialize(self.db)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_two_independent_sources_promote(self):
        ingest(self.db, [
            {"subject": "S", "predicate": "P", "value": "V", "source_id": "A"},
            {"subject": "S", "predicate": "P", "value": "V", "source_id": "B"},
        ])
        self.assertEqual(sleep(self.db)["promoted"], 1)
        self.assertEqual(recall(self.db, "S", "P")["value"], "V")
        self.assertEqual(len(rehearsals(self.db)), 1)

    def test_same_source_not_independent(self):
        ingest(self.db, [
            {"subject": "S", "predicate": "P", "value": "V", "source_id": "A"},
            {"subject": "S", "predicate": "P", "value": "V", "source_id": "A"},
        ])
        self.assertEqual(sleep(self.db)["promoted"], 0)
        self.assertIsNone(recall(self.db, "S", "P"))

    def test_verified_promotes_one_source(self):
        ingest(self.db, [{"subject":"S", "predicate":"P", "value":"V", "source_id":"A", "verified":True}])
        self.assertEqual(sleep(self.db)["promoted"], 1)

    def test_conflict_is_quarantined_and_no_overwrite(self):
        ingest(self.db, [{"subject":"S", "predicate":"P", "value":"old", "source_id":"A", "verified":True}])
        sleep(self.db)
        ingest(self.db, [{"subject":"S", "predicate":"P", "value":"new", "source_id":"B", "verified":True}])
        result = sleep(self.db)
        self.assertEqual(result["quarantined"], 1)
        self.assertEqual(recall(self.db, "S", "P")["value"], "old")
        self.assertEqual(stats(self.db)["quarantines"], 1)

    def test_threshold_rejection_rolls_back_memory(self):
        ingest(self.db, [{"subject":"S", "predicate":"P", "value":"V", "source_id":"A", "verified":True}])
        # Intentionally wrong benchmark: correct score 0, mandatory threshold 1.
        golden = [{"cohort":"new", "subject":"S", "predicate":"P", "expected":"wrong"}]
        result = sleep(self.db, golden, min_new_accuracy=1.0)
        self.assertEqual(result["status"], "rejected")
        self.assertIsNone(recall(self.db, "S", "P"))
        self.assertEqual(len(rehearsals(self.db)), 0)
        self.assertEqual(stats(self.db)["cycles"], 1)

    def test_retrieval_and_evaluation(self):
        ingest(self.db, [{"subject":"Projet Beta", "predicate":"statut", "value":"en développement", "source_id":"A", "verified":True}])
        sleep(self.db)
        self.assertEqual(search(self.db, "développement")[0]["subject"], "Projet Beta")
        self.assertEqual(search(self.db, "') OR NOT (*"), [])
        sample = [{"cohort":"old", "subject":"Projet Beta", "predicate":"statut", "expected":"en développement"}]
        self.assertEqual(evaluate(self.db, sample)["old"]["accuracy"], 1.0)

    def test_ingest_is_atomic_on_bad_row(self):
        with self.assertRaises(ValueError):
            ingest(self.db, [
                {"subject":"S", "predicate":"P", "value":"V", "source_id":"A"},
                {"subject":"BAD", "predicate":"P", "value":"V", "source_id":"A", "verified":"yes"},
            ])
        self.assertEqual(stats(self.db)["observations"], 0)

    def test_min_threshold_without_evaluation_cohort_fails(self):
        result = sleep(self.db, min_old_accuracy=1.0)
        self.assertEqual(result["status"], "rejected")

    def test_idempotence_memory(self):
        ingest(self.db, [{"subject":"S", "predicate":"P", "value":"V", "source_id":"A", "verified":True}])
        sleep(self.db)
        self.assertEqual(sleep(self.db)["promoted"], 0)
        self.assertEqual(stats(self.db)["memories"], 1)

    def test_repeated_sleep_does_not_duplicate_quarantine(self):
        ingest(self.db, [
            {"subject":"S", "predicate":"P", "value":"a", "source_id":"A"},
            {"subject":"S", "predicate":"P", "value":"b", "source_id":"B"},
        ])
        for _ in range(3):
            sleep(self.db)
        self.assertEqual(stats(self.db)["quarantines"], 1)
        # A new variant is a new conflict and must be recorded.
        ingest(self.db, [{"subject":"S", "predicate":"P", "value":"c", "source_id":"C"}])
        sleep(self.db)
        self.assertEqual(stats(self.db)["quarantines"], 2)

    def test_load_jsonl(self):
        test_file = Path(self.temp.name) / "facts.jsonl"
        test_file.write_text('# comment\n{"a": 1}\n', encoding="utf-8")
        self.assertEqual(load_jsonl(test_file), [{"a": 1}])


if __name__ == "__main__":
    unittest.main()
