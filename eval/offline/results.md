# Offline Evaluation Results

Generated: pending — run `python -m eval.offline.run_offline_eval`

**Disclaimer:** Educational demo only. Synthetic data — no real PHI.

## How to run

```bash
# Ensure .env is configured (LLM optional; fallbacks used if missing)
python -m eval.offline.run_offline_eval
```

## Expected thresholds

| Metric | Pass threshold |
|--------|----------------|
| Parallel fan-in correctness | 100% |
| LLM Call 1 present (success path) | 100% |
| LLM Call 1 non-override | 100% |
| LLM Call 2 present before HITL | 100% |
| HITL enforcement | 100% |
| Provider lookup correctness | ≥ 95% |
| Latency p95 (ex-HITL) | ≤ 12s local |

Dataset: `eval/offline/dataset.json` (≥ 20 cases).
