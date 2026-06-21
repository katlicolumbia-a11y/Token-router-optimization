"""Task decomposition and model-tier routing heuristics.

The planner intentionally uses transparent heuristics so teams can audit why a
stage was assigned to a low-cost, balanced, or frontier model tier.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Iterable


class Difficulty(str, Enum):
    """Supported task difficulty levels."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ModelTier(str, Enum):
    """Abstract model tiers that can be mapped to provider-specific models."""

    ECONOMY = "economy"
    BALANCED = "balanced"
    FRONTIER = "frontier"


@dataclass(frozen=True)
class Stage:
    """A routed unit of work within a larger task."""

    name: str
    description: str
    difficulty: Difficulty
    recommended_model: ModelTier
    reasoning_effort: str
    rationale: str

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "description": self.description,
            "difficulty": self.difficulty.value,
            "recommended_model": self.recommended_model.value,
            "reasoning_effort": self.reasoning_effort,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class RoutingPlan:
    """A complete difficulty-aware routing plan."""

    original_task: str
    stages: tuple[Stage, ...]
    estimated_savings: str
    quality_guardrail: str

    def to_dict(self) -> dict[str, object]:
        return {
            "original_task": self.original_task,
            "stages": [stage.to_dict() for stage in self.stages],
            "estimated_savings": self.estimated_savings,
            "quality_guardrail": self.quality_guardrail,
        }


class RouterPlanner:
    """Create a cost-aware model routing plan without sacrificing quality."""

    _EASY_PATTERNS = (
        "read",
        "scan",
        "extract",
        "parse",
        "format",
        "convert",
        "deduplicate",
        "list",
        "transcribe",
    )
    _MEDIUM_PATTERNS = (
        "summarize",
        "compare",
        "classify",
        "easy analysis",
        "trends",
        "organize",
        "outline",
        "cluster",
    )
    _HARD_PATTERNS = (
        "hard analysis",
        "rigorous",
        "optimize",
        "prove",
        "derive",
        "strategy",
        "architecture",
        "legal",
        "medical",
        "financial",
        "security",
        "risk",
        "critique",
        "multi-step",
        "ambiguous",
    )

    def plan(self, task: str) -> RoutingPlan:
        """Return a stage-by-stage routing plan for a user task."""
        clean_task = task.strip()
        if not clean_task:
            raise ValueError("task must not be empty")

        stages = tuple(self._build_stages(clean_task))
        return RoutingPlan(
            original_task=clean_task,
            stages=stages,
            estimated_savings=self._estimate_savings(stages),
            quality_guardrail=(
                "Escalate any stage to the frontier tier when confidence is low, "
                "requirements are ambiguous, or the output has high-stakes impact."
            ),
        )

    def _build_stages(self, task: str) -> Iterable[Stage]:
        clauses = self._split_task(task)
        for index, clause in enumerate(clauses, start=1):
            difficulty = self._classify(clause)
            model, effort = self._route(difficulty)
            yield Stage(
                name=self._stage_name(clause, index),
                description=clause,
                difficulty=difficulty,
                recommended_model=model,
                reasoning_effort=effort,
                rationale=self._rationale(difficulty),
            )

    def _split_task(self, task: str) -> list[str]:
        parts = [
            part.strip(" .")
            for part in re.split(r"(?:,?\s+then\s+|;|\n+|\.\s+)", task, flags=re.IGNORECASE)
            if part.strip(" .")
        ]
        if len(parts) == 1:
            parts = [
                part.strip(" .")
                for part in re.split(r",\s+(?=and\s+|identify|produce|summarize|analyze|scan|read)", task, flags=re.IGNORECASE)
                if part.strip(" .")
            ]
        return parts or [task]

    def _classify(self, text: str) -> Difficulty:
        lowered = text.lower()
        if self._contains_any(lowered, self._HARD_PATTERNS):
            return Difficulty.HARD
        if self._contains_any(lowered, self._MEDIUM_PATTERNS):
            return Difficulty.MEDIUM
        if self._contains_any(lowered, self._EASY_PATTERNS):
            return Difficulty.EASY
        return Difficulty.MEDIUM

    def _route(self, difficulty: Difficulty) -> tuple[ModelTier, str]:
        if difficulty is Difficulty.EASY:
            return ModelTier.ECONOMY, "low"
        if difficulty is Difficulty.MEDIUM:
            return ModelTier.BALANCED, "medium"
        return ModelTier.FRONTIER, "high"

    def _stage_name(self, text: str, index: int) -> str:
        lowered = text.lower()
        if self._contains_any(lowered, ("read", "scan", "extract", "parse")):
            return "document intake"
        if self._contains_any(lowered, ("summarize", "outline")):
            return "summary"
        if self._contains_any(lowered, ("analysis", "analyze", "critique", "risk")):
            return "analysis"
        return f"stage {index}"

    def _rationale(self, difficulty: Difficulty) -> str:
        if difficulty is Difficulty.EASY:
            return "Mechanical intake or transformation can use the least expensive capable tier."
        if difficulty is Difficulty.MEDIUM:
            return "Moderate interpretation benefits from a balanced model without frontier cost."
        return "Complex, ambiguous, or high-stakes reasoning should use the strongest tier."

    def _estimate_savings(self, stages: Iterable[Stage]) -> str:
        stage_list = list(stages)
        economy_or_balanced = sum(
            stage.recommended_model is not ModelTier.FRONTIER for stage in stage_list
        )
        if not stage_list or economy_or_balanced == 0:
            return "No savings expected because every stage requires frontier reasoning."
        percentage = round(economy_or_balanced / len(stage_list) * 100)
        return f"Up to {percentage}% of stages can avoid frontier-tier cost while preserving escalation safeguards."

    def _contains_any(self, text: str, patterns: Iterable[str]) -> bool:
        return any(pattern in text for pattern in patterns)
