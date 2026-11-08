# Scientific fidelity and validation plan

Reference: https://arxiv.org/abs/2606.03979

| Research mechanism | V0.1 status | Implication |
|---|---|---|
| Active/wake observation | Implemented as JSONL intake | External record keeping only |
| Consolidation during sleep | Heuristic staging + promotion | **Not** weight consolidation / GKD |
| Capacity expansion & low-rank MoE | Not implemented | No newly learned model parameters |
| On-policy distillation | Not implemented | No teacher/student distributions |
| RL imitation reward | Not implemented | No optimization of model outputs |
| Synthetic dreaming & random expert routes | Not implemented | Deterministic rehearsal Q&A only |
| Gradient-based data filtering | Not implemented | No learned sample ranking |
| Benchmarks for catastrophic forgetting | Not implemented | Exact-key regression tests only |
| Rollback | SQL transaction of tentative promotions | Not adapter/model rollback |

## Falsifiable evaluation before any impressive claim

A serious test must run the SAME frozen base LLM on identical held-out queries under at least four conditions: (A) no memory; (B) append-only retrieval; (C) consolidated memory + retrieval; (D) parameter adaptation, once implemented. Ensure equal token budgets, controlled prompts, and the same retrieval policy where applicable. Split facts by subject and source to avoid leakage; include information not present in pretrained knowledge.

Repeated stages: T0 old tasks, T1 novel facts, T2 contradictory/time-changing facts, T3 unrelated skills. Report every stage, not just final average.

Primary outcomes: old-task retention, new-task accuracy, unsupported assertion rate, answer abstention quality, source coverage, retrieval precision/recall, latency and hardware cost. Add 95% confidence intervals where feasible and manually inspect false positives. Grade with an independent, frozen answer key or human adjudication; never let the model grading itself determine its own reward unreviewed.

Acceptance criterion for V1 research: consolidated memory outperforms a strong append-only RAG baseline on a blinded held-out set **without significant decrease** in old-fact correctness, and with acceptably low maintenance costs. A failed comparison is a useful outcome: keep the simpler baseline.

## Do not infer

- This external memory pipeline prevents catastrophic forgetting *in model weights*.
- A percentage from the Google paper transfers to this project.
- Parameter changes are useful just because rehearsal produces plausible text.
- Automatic hallucinated facts are safe training targets.
