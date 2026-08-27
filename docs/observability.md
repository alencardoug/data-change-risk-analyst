# Reading a LangSmith trace for one case

Tracing is env-only. In `.env`:

```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=dcra
```

Run one case (Streamlit or a script), then open the `dcra` project at
<https://smith.langchain.com>. Each `graph.invoke` / `resume` is one root run.

## What to look for

| In the trace | What it tells you |
|---|---|
| The tree of child runs under the root | the node execution order — `interpret`, the three `collect_*` **siblings running in parallel**, `assess_risk` after all three, then the conditional path |
| The `interpret` run's input/output | the raw text in, the `StructuredChange` out — a structured-output call, not free text |
| A gap in the tree ending at `human_review` | the `interrupt()` — the run pauses here; the next root run is the `resume` |
| `investigate` → nested agent runs | the ReAct loop: each `get_asset_metadata` / `get_dependencies` / `get_downstream_usage` tool call, and the model turns between them. Confirm it only ever calls those three tools and stops within the recursion cap |
| Token + latency on each model run | cost of interpretation vs recommendation vs the agent loop |
| `assess_risk`, routing | **no model run** — pure functions. If you see a model call here, something regressed the deterministic boundary |

## Correlating with the record

The persisted `analysis_record.step_log` is the same ordered account without the trace UI, e.g.:

```
interpret: DROP_COLUMN on orders
collect_asset: 1 item(s)
collect_deps: 2 item(s)
collect_usage: 1 item(s)
assess_risk: pass 1 → MEDIUM (REFERENCED_BY_VIEW, ACTIVELY_READ)
recommend: v1 PROCEED (NORMAL)
human_review: RETURN (evidence missing)
reassess: re-collecting evidence after 'evidence missing' feedback
...
assess_risk: pass 2 → MEDIUM (...); evidence gap
investigate: agent added 1 item(s); risk now HIGH
recommend: v2 PROCEED (NORMAL)
human_review: APPROVE
finalize: APPROVED
```

`thread_id` (= `analysis_record.id`) is the join key between the checkpoint rows, the trace, and
the final record.
