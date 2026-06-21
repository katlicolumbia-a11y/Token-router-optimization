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

## Where to run the test commands

Run all commands from the repository root, the directory that contains `pyproject.toml`:

```bash
cd /workspace/Token-router-optimization
python -m pytest
python -m token_router --compare-baseline "Read a 5-page PDF, then summarize it, then produce rigorous risk analysis"
```

If you cloned this repository somewhere else, replace `/workspace/Token-router-optimization` with your local clone path.

## Where to put PDFs

This CLI reads PDFs from your local filesystem; it does not automatically receive files attached to a chat UI. Put the PDF anywhere on disk and pass that path with `--pdf`.

A simple convention is to create a local `examples/pdfs/` folder:

```bash
mkdir -p examples/pdfs
cp ~/Downloads/paper.pdf examples/pdfs/paper.pdf
python -m token_router --pdf examples/pdfs/paper.pdf "summarize the easy findings, then produce a rigorous risk analysis" --compare-baseline
```

PDF files inside `examples/pdfs/` are ignored by Git so you can test private documents locally without committing them.


## Execute the routed workflow with real models

Set an OpenAI API key, then add `--execute`. The command executes each stage with the model selected for that stage and returns the final analysis plus actual API token usage, latency, and estimated cost.

```bash
export OPENAI_API_KEY="your_api_key"
python -m pip install -e .[pdf]
python -m token_router --pdf examples/pdfs/paper.pdf "summarize the easy findings, then produce a rigorous risk analysis" --compare-baseline --execute
```

The default model tier mapping is:

| Tier | Default model | Override environment variable |
| --- | --- | --- |
| `economy` | `gpt-5.4-mini` | `TOKEN_ROUTER_ECONOMY_MODEL` |
| `balanced` | `gpt-5.4` | `TOKEN_ROUTER_BALANCED_MODEL` |
| `frontier` | `gpt-5.5` | `TOKEN_ROUTER_FRONTIER_MODEL` |

The `execution` block reports per-stage model, model tier, prompt tokens, completion tokens, total tokens, latency, estimated cost, and output. The final stage output is repeated as `execution.final_output`.


## Use from a normal ChatGPT window

A normal ChatGPT chat cannot directly run this local Python package. To use it inside ChatGPT, run the included HTTP API and connect it to a Custom GPT Action. See `docs/chatgpt-action.md` for the complete setup.

Short version:

```bash
python -m pip install -e .[server,pdf]
export OPENAI_API_KEY="your_api_key"
uvicorn token_router.server:app --host 0.0.0.0 --port 8000
```

Then expose port 8000 over HTTPS and import `https://YOUR_HOST/openapi.json` into a Custom GPT Action.

## Planner decomposition behavior

The planner creates semantic workflow stages from the requested task instead of splitting every sentence in an extracted PDF. Pasted source text after markers such as `PDF content:`, `Source content:`, `Extracted text:`, `References`, or `Bibliography` is ignored for decomposition so citation fragments, URLs, page headers, footers, and isolated numbers do not become stages.
