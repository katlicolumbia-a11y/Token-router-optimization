"""Execute routed stages against real model APIs."""

from __future__ import annotations

from dataclasses import dataclass
import os
import time
from typing import Any

from .planner import ModelTier, RoutingPlan, Stage


DEFAULT_MODEL_MAP: dict[ModelTier, str] = {
    ModelTier.ECONOMY: "gpt-5.4-mini",
    ModelTier.BALANCED: "gpt-5.4",
    ModelTier.FRONTIER: "gpt-5.5",
}

DEFAULT_USD_PER_1K_TOKENS: dict[ModelTier, float] = {
    ModelTier.ECONOMY: 0.0006,
    ModelTier.BALANCED: 0.003,
    ModelTier.FRONTIER: 0.015,
}


@dataclass(frozen=True)
class StageExecution:
    """Actual execution telemetry for one routed stage."""

    name: str
    model_tier: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    estimated_cost_usd: float
    output: str

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "model_tier": self.model_tier,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
            "estimated_cost_usd": self.estimated_cost_usd,
            "output": self.output,
        }


@dataclass(frozen=True)
class ExecutionResult:
    """Final output and aggregate telemetry for an executed routing plan."""

    final_output: str
    stages: tuple[StageExecution, ...]
    total_tokens: int
    total_latency_ms: int
    estimated_cost_usd: float

    def to_dict(self) -> dict[str, object]:
        return {
            "final_output": self.final_output,
            "stages": [stage.to_dict() for stage in self.stages],
            "total_tokens": self.total_tokens,
            "total_latency_ms": self.total_latency_ms,
            "estimated_cost_usd": self.estimated_cost_usd,
        }


class OpenAIStageExecutor:
    """Run each routed stage with the OpenAI Responses API."""

    def __init__(
        self,
        client: Any | None = None,
        model_map: dict[ModelTier, str] | None = None,
        pricing: dict[ModelTier, float] | None = None,
    ) -> None:
        self._client = client or self._build_openai_client()
        self._model_map = model_map or _model_map_from_env()
        self._pricing = pricing or DEFAULT_USD_PER_1K_TOKENS

    def execute(self, plan: RoutingPlan, source_text: str) -> ExecutionResult:
        """Execute each stage sequentially and pass prior outputs forward."""
        prior_output = ""
        executions: list[StageExecution] = []
        for stage in plan.stages:
            execution = self._execute_stage(stage, plan.original_task, source_text, prior_output)
            executions.append(execution)
            prior_output = execution.output

        return ExecutionResult(
            final_output=prior_output,
            stages=tuple(executions),
            total_tokens=sum(stage.total_tokens for stage in executions),
            total_latency_ms=sum(stage.latency_ms for stage in executions),
            estimated_cost_usd=round(sum(stage.estimated_cost_usd for stage in executions), 6),
        )

    def _execute_stage(
        self,
        stage: Stage,
        original_task: str,
        source_text: str,
        prior_output: str,
    ) -> StageExecution:
        model = self._model_map[stage.recommended_model]
        prompt = _stage_prompt(stage, original_task, source_text, prior_output)
        started = time.perf_counter()
        response = self._client.responses.create(
            model=model,
            input=prompt,
            reasoning={"effort": stage.reasoning_effort},
        )
        latency_ms = round((time.perf_counter() - started) * 1000)
        usage = _usage_from_response(response)
        total_tokens = usage["prompt_tokens"] + usage["completion_tokens"]
        return StageExecution(
            name=stage.name,
            model_tier=stage.recommended_model.value,
            model=model,
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            estimated_cost_usd=round(total_tokens / 1000 * self._pricing[stage.recommended_model], 6),
            output=getattr(response, "output_text", ""),
        )

    def _build_openai_client(self) -> Any:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("Set OPENAI_API_KEY before running with --execute.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install the OpenAI SDK first: python -m pip install openai") from exc
        return OpenAI()


def _model_map_from_env() -> dict[ModelTier, str]:
    return {
        ModelTier.ECONOMY: os.getenv("TOKEN_ROUTER_ECONOMY_MODEL", DEFAULT_MODEL_MAP[ModelTier.ECONOMY]),
        ModelTier.BALANCED: os.getenv("TOKEN_ROUTER_BALANCED_MODEL", DEFAULT_MODEL_MAP[ModelTier.BALANCED]),
        ModelTier.FRONTIER: os.getenv("TOKEN_ROUTER_FRONTIER_MODEL", DEFAULT_MODEL_MAP[ModelTier.FRONTIER]),
    }


def _stage_prompt(stage: Stage, original_task: str, source_text: str, prior_output: str) -> str:
    return f"""You are executing one stage in a routed workflow.

Original task:
{original_task}

Current stage:
{stage.name}

Stage description:
{stage.description}

Source content:
{source_text or '[No separate source content provided]'}

Prior stage output:
{prior_output or '[No prior stage output]'}

Return only the completed output for the current stage. Preserve important details needed by later stages.
"""


def _usage_from_response(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {"prompt_tokens": 0, "completion_tokens": 0}
    prompt_tokens = _read_usage_field(usage, "input_tokens", "prompt_tokens")
    completion_tokens = _read_usage_field(usage, "output_tokens", "completion_tokens")
    return {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens}


def _read_usage_field(usage: Any, *names: str) -> int:
    for name in names:
        if isinstance(usage, dict) and name in usage:
            return int(usage[name] or 0)
        value = getattr(usage, name, None)
        if value is not None:
            return int(value)
    return 0
