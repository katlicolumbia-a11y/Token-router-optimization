# Token Router Optimization

Automated router optimization tool for splitting a complex task into difficulty-aware stages and assigning each stage to the least expensive model tier that can preserve output quality.

The router is designed for workflows such as:

1. scanning a 5-page PDF with a low-cost model,
2. running straightforward analysis with a medium model, and
3. reserving the strongest/highest-reasoning model for the hardest synthesis or critique.

## Quick start

```bash
python -m token_router "Read a 5-page PDF, summarize it, identify easy trends, then produce a rigorous risk analysis"
```

Example output:

```json
{
  "stages": [
    {
      "name": "document intake",
      "difficulty": "easy",
      "recommended_model": "economy",
      "reasoning_effort": "low"
    }
  ]
}
```

## How routing works

The planner decomposes the task into stages, estimates each stage's difficulty, then picks the lowest-cost capable model tier:

| Difficulty | Model tier | Intended use |
| --- | --- | --- |
| Easy | `economy` | extraction, scanning, formatting, deduplication |
| Medium | `balanced` | summaries, simple analysis, comparisons |
| Hard | `frontier` | deep reasoning, strategy, high-stakes synthesis |

The router favors accuracy over cost savings. If a stage contains high-stakes language, ambiguous requirements, mathematical reasoning, security review, legal/medical/financial judgment, or multi-step synthesis, it escalates to a stronger tier.

## Python API

```python
from token_router import RouterPlanner

planner = RouterPlanner()
plan = planner.plan("Scan a PDF, summarize it, and perform a hard technical critique")
print(plan.to_dict())
```


## Attach and route a PDF

Save the PDF locally, then pass its path to the CLI:

```bash
python -m token_router --pdf ./paper.pdf "summarize the easy findings, then produce a rigorous risk analysis" --compare-baseline
```

When `pypdf` is installed, the CLI extracts PDF text. Without `pypdf`, it still falls back to the PDF page count so the router can plan document intake without requiring extra dependencies.

## Measuring token savings

Use `--compare-baseline` to add a `token_comparison` block. The baseline assumes every stage uses the `frontier` tier. The routed estimate applies relative tier weights to the stages selected by the planner.

The built-in estimator is intentionally approximate and provider-neutral. For production measurement, replace the default weights with provider prices or actual metered token counts from your model gateway.
