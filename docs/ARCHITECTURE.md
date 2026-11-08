# Architecture V0.1

## Boundary

Two separable layers:

1. **External memory orchestrator (implemented).** SQL observations, provenances, staged consolidation, quarantines, fixed benchmark gate, retrieval, auditable rehearsal.
2. **Parametric learner (NOT implemented).** Frozen base LLM, expandable adapters / experts, distillation, optional synthetic replay + evaluation.

Do not confuse a persisted memory database with knowledge transferred into model parameters. The core package does not require or call a language model.

## Storage contract

`observations` are append-only (from the application interface), never automatically deleted. `memories` contain one currently approved value per subject/predicate. `quarantines` point to sleep cycle audits. `rehearsals` contain only restatements of approved memories. `cycles` record acceptance and exact-key metric scores.

## Promotion rule

- Group by exact `(subject, predicate)`; normalize externally if needed.
- If more than one `value` is observed, quarantine instead of choosing the most recent or most repeated.
- If one unique value exists, promote when `verified` is `true` on any observation, or when >=2 distinct `source_id` values support that value.
- Subsequent repeats from the **same source** do not count as independent evidence.
- Benchmark `old` must not regress; optional explicit `old` / `new` accuracy thresholds must pass.
- A failed quality gate rolls back proposed memory mutations. Audit and raw observations remain.

## Threat model / safety

- **Confidentiality:** never publish real observations. Default files are ignored in `.gitignore`, but `*.jsonl` examples can still be tracked—review before commit. Local DB is unencrypted. Device OS file permissions and disk encryption remain the user's responsibility.
- **Provenance poisoning:** source ID names are arbitrary. No cryptographic identity, source independence audit or truth verification.
- **Data poisoning:** manual `verified` is an explicit assertion, not a fact-check service.
- **Prompt injection:** no automatic execution of stored text; external LLM integrations must treat stored content as untrusted.
- **Privacy:** no GDPR/Quebec Law 25 workflows, PII classifier, deletion/retention policy or access control yet. Do not use for regulated production data.
- **Rollback:** restores only tentative SQL changes before commit. No global versioned memory snapshots, distributed transactions or model checkpoint manager.
- **Concurrency:** single-process demo only. No synchronization of multiple writers.

## Candidate next interface

Introduce a `Learner` protocol, separately from `Store` and evaluation:

```python
class Learner:
    def build_candidate_adapter(self, replay_dataset, frozen_model): ...
    def evaluate(self, adapter_path, holdout_sets): ...
    def promote_or_rollback(self, adapter_path): ...
```

Only attempt parameter expansion / LoRA once a real model and test harness exist. Retention and new-task performance must be tracked side by side.
