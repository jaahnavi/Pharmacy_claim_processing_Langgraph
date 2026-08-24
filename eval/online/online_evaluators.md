# Online Evaluators (LangSmith / production signals)

Educational demo only — synthetic claim data.

## Signals to track

| Signal | Why |
|--------|-----|
| Error rate | Graph/node/API/LLM failures |
| LLM1 / LLM2 failure rates | Model or prompt regressions (`llm1_ok` / `llm2_ok` false) |
| LLM fallback rate | Too many template fallbacks |
| Fan-in integrity violations | Coverage before both branches ready |
| HITL integrity violations | Submit without approve |
| NPI / RxNorm / openFDA failure rates | Public dependency health |
| Token cost for LLM1+LLM2 | Cost control |
| Feedback: rationale quality, brief quality, no PHI leakage | Production quality |

## LangSmith setup

1. Set in `.env`:

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=...
LANGCHAIN_PROJECT=pharmacy-claim-orchestration
```

2. Traced LLM spans (required names):
   - `llm_coverage_rationale` (LLM Call 1)
   - `llm_reviewer_brief` (LLM Call 2)

3. Attach online evaluators in LangSmith project settings (or via SDK feedback).

## Online evaluator rules

### 1. HITL integrity
Fail if `status == submitted` AND `approval_status != approved`.

### 2. LLM non-override
Fail if `coverage.coverage_status != coverage.rule_status`.

### 3. Both LLM spans present (success path)
On paths that reach HITL, require non-empty:
- `coverage.rationale`
- `reviewer_brief`
and corresponding LangSmith runs named `llm_coverage_rationale` / `llm_reviewer_brief`.

### 4. Grounding
Fail brief/rationale that invents NPI/drug/member fields not present in state JSON.

### 5. No-PHI leakage
Fail SSN/MRN-like patterns beyond synthetic demo ids (`MEM-*`, `Demo` names).

## Implementation hooks

- Node messages include `fan_in_gate: member_ok=... drug_ok=...` for fan-in audits.
- API responses expose `llm1_ok`, `llm2_ok`, `provider_ok` for dashboards.
- Reject path never creates `submission.confirmation_id`.

See `alert_thresholds.md` for paging thresholds.
