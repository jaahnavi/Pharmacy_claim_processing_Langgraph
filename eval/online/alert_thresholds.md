# Online alert thresholds

| Alert | Threshold | Action |
|-------|-----------|--------|
| Error rate | ≥ 5% over 15 minutes | Page on-call; check `/health` and public APIs |
| LLM failure rate | ≥ 10% over 15 minutes | Verify keys/quotas; confirm fallback rate |
| HITL integrity violations | **any** | Immediate investigate — block deploys |
| LLM non-override violations | **any** | Immediate investigate — rules/LLM prompt bug |
| p95 graph latency (ex-HITL) | ≥ 12 seconds | Check RxNorm/openFDA/NPI latency; scale or cache |
| LLM fallback rate | ≥ 30% over 1 hour | Model outage or misconfiguration |
| Fan-in integrity violations | **any** | Graph regression — roll back |

## Suggested dashboard panels

1. Requests by final `status`
2. `llm1_ok` / `llm2_ok` rates
3. Public API error counts (RxNorm, openFDA, NPI)
4. Time-to-HITL (p50/p95)
5. Approve vs reject vs request_changes mix
