"""Command-line entry point for the token router planner."""

from __future__ import annotations

import argparse
import json

from .estimator import TokenEstimator
from .executor import OpenAIStageExecutor
from .pdf import load_pdf_text
from .planner import RouterPlanner


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or execute a difficulty-aware model routing plan.")
    parser.add_argument("task", nargs="?", help="Task description to decompose and route")
    parser.add_argument("--pdf", help="Optional PDF path to include as the document-intake source")
    parser.add_argument(
        "--compare-baseline",
        action="store_true",
        help="Estimate routed weighted tokens versus sending every stage to the frontier tier",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Call the selected real model for each stage and return final output plus actual usage telemetry",
    )
    args = parser.parse_args()

    source_text = load_pdf_text(args.pdf) if args.pdf else ""
    task = _compose_task(args.task, source_text)
    plan = RouterPlanner().plan(task)
    payload = plan.to_dict()

    if args.compare_baseline:
        comparison_source = "\n".join(part for part in (source_text, task) if part)
        payload["token_comparison"] = TokenEstimator().compare(plan, comparison_source).to_dict()

    if args.execute:
        payload["execution"] = OpenAIStageExecutor().execute(plan, source_text).to_dict()

    print(json.dumps(payload, indent=2))


def _compose_task(task: str | None, source_text: str) -> str:
    if task and source_text:
        return f"Read the attached PDF, then {task.strip()}"
    if task:
        return task.strip()
    if source_text:
        return "Read the attached PDF and summarize it."
    raise SystemExit("Provide a task, --pdf, or both.")


if __name__ == "__main__":
    main()
