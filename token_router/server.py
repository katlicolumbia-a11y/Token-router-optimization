"""HTTP API for using the router from a Custom GPT Action."""

from __future__ import annotations

import base64
from pathlib import Path
import tempfile

from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException

from .estimator import TokenEstimator
from .executor import OpenAIStageExecutor
from .pdf import load_pdf_text
from .planner import RouterPlanner


class ExecuteRequest(BaseModel):
    """Request body for a routed execution."""

    task: str = Field(..., description="Analysis task to run against the PDF or source text.")
    source_text: str | None = Field(None, description="Optional text already extracted from an uploaded document.")
    pdf_base64: str | None = Field(None, description="Optional base64-encoded PDF bytes.")
    pdf_filename: str = Field("uploaded.pdf", description="Filename used when decoding pdf_base64.")
    compare_baseline: bool = Field(True, description="Include routed-vs-frontier-only comparison.")
    execute: bool = Field(True, description="Call real models. Set false to only return the routing plan.")


app = FastAPI(
    title="Token Router Optimization API",
    version="0.1.0",
    description="Route task stages to model tiers and optionally execute them with real model APIs.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/execute")
def execute(request: ExecuteRequest) -> dict[str, object]:
    """Plan and optionally execute a routed document analysis workflow."""
    try:
        source_text = _source_text_from_request(request)
        plan_task = _compose_task(request.task, source_text)
        plan = RouterPlanner().plan(plan_task)
        payload = plan.to_dict()

        if request.compare_baseline:
            comparison_source = "\n".join(part for part in (source_text, plan_task) if part)
            payload["token_comparison"] = TokenEstimator().compare(plan, comparison_source).to_dict()

        if request.execute:
            payload["execution"] = OpenAIStageExecutor().execute(plan, source_text).to_dict()

        return payload
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _source_text_from_request(request: ExecuteRequest) -> str:
    if request.source_text:
        return request.source_text
    if not request.pdf_base64:
        return ""

    try:
        pdf_bytes = base64.b64decode(request.pdf_base64, validate=True)
    except ValueError as exc:
        raise ValueError("pdf_base64 must be valid base64-encoded PDF bytes") from exc

    suffix = Path(request.pdf_filename).suffix or ".pdf"
    with tempfile.NamedTemporaryFile(suffix=suffix) as temp_pdf:
        temp_pdf.write(pdf_bytes)
        temp_pdf.flush()
        return load_pdf_text(temp_pdf.name)


def _compose_task(task: str, source_text: str) -> str:
    clean_task = task.strip()
    if not clean_task:
        raise ValueError("task must not be empty")
    if source_text:
        return f"Read the provided document, then {clean_task}"
    return clean_task
