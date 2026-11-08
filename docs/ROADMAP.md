# Roadmap

## V0.1 — done

- [x] Local wake/sleep orchestration using SQLite
- [x] Append observations with provenance
- [x] Distinct-source threshold and manual approval
- [x] Conflict quarantine
- [x] SQL quality gate + atomic rollback
- [x] Rehearsal dataset export (no LLM generation)
- [x] FTS5 retrieval, CLI, unit tests and CI

## V0.2 — practical memory correctness

- [ ] Review/resolve quarantined facts with human approval and audit log
- [ ] Temporal memory: valid-from, valid-to, source timestamp, supersession
- [ ] Source identity validation and document fingerprints
- [ ] Deletion and retention policy, redaction, no sensitive fields by default
- [ ] Benchmark search by natural-language query and source-grounded responses

## V0.3 — apples-to-apples experiment

- [ ] Append-only RAG baseline vs consolidated RAG under identical conditions
- [ ] Multi-stage synthetic + real public evaluation sets, no train/test leakage
- [ ] Track recall, faithfulness, latency and cost with CI regression artifacts
- [ ] Optional local LLM inference, explicit consent for network access

## V0.4 — parameter learning (separate experimental module)

- [ ] Frozen base LM with isolated LoRA/low-rank expansion (GPU optional)
- [ ] Teacher/student behavioral distillation (if compute available)
- [ ] Candidate checkpoint / rollback after held-out tests
- [ ] Strong ablation controls: no adaptation, standard SFT, RAG, replay
- [ ] Dream sample generation with human verification and corruption controls

## Research-grade (long-term)

- [ ] Study whether low-rank experts and on-policy GKD can be reproduced under a permitted license
- [ ] Assess feasibility of random-expert routing, RL imitation, gradient filtering
- [ ] Publish verifiable ablations and negative results

Do not call V0.4 or later capabilities shipped before tests and reproducible metrics exist.
