# Replay Analyst grounding

Replay Analyst is downstream, optional, read-only, and unrelated to matching decisions. The
shipped fallback accepts a question plus structured engine evidence and emits:

```json
{
  "summary": "...",
  "claims": [
    {"claim": "...", "evidence_ids": ["event:18224"]}
  ],
  "mode": "deterministic"
}
```

`validate_evidence` retains only claims with a nonempty evidence set wholly contained in the
provided evidence IDs. Tests prove that an invented `event:999` is removed. The rule-based mode
can summarize total/largest trade, the latest rejection reason, or latest engine event and
functions with no `OPENAI_API_KEY`.

If an LLM adapter is added later, it must use the same structured schema and post-validation.
Unsupported claims should be removed or cause an evaluation failure. A small fixture suite should
track citation validity, known-scenario attribution, and unsupported-claim rate.

The analyst explains simulated events. It is not financial advice, does not place orders, cannot
alter state, and makes no trading decisions.

