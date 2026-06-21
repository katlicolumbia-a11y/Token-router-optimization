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


@dataclass(frozen=True)
class StageTemplate:
    name: str
    description: str
    difficulty: Difficulty
    triggers: tuple[str, ...]


class RouterPlanner:
    """Create a cost-aware model routing plan without sacrificing quality.

    The planner builds semantic workflow stages from the user's requested work,
    not from every sentence in a source document. This prevents extracted PDFs
    from becoming hundreds of citation, URL, header, or line-break stages.
    """

    _SOURCE_BOUNDARIES = (
        r"\n\s*PDF content\s*:\s*\n",
        r"\n\s*Source content\s*:\s*\n",
        r"\n\s*Extracted text\s*:\s*\n",
        r"\n\s*References\s*\n",
        r"\n\s*Bibliography\s*\n",
    )
    _NOISE_LINE = re.compile(
        r"^\s*(?:\d+|page\s+\d+|https?://\S+|doi:?\s*\S+|\[[\d,\s-]+\]|[A-Z]\.)\s*$",
        re.IGNORECASE,
    )
    _CITATION_FRAGMENT = re.compile(r"^\s*[A-Z][A-Za-z-]+\s+et\s+al\.?,?\s+\d{4}[a-z]?\.?\s*$")

    _STAGE_TEMPLATES = (
        StageTemplate(
            name="PDF extraction/intake",
            description="Extract, clean, and normalize the PDF text while ignoring references, page headers, footers, URLs, isolated numbers, and citation fragments.",
            difficulty=Difficulty.EASY,
            triggers=("pdf", "paper", "document", "attached", "extract", "read", "scan"),
        ),
        StageTemplate(
            name="paper summarization",
            description="Summarize the paper's purpose, methods, scope, and main claims.",
            difficulty=Difficulty.MEDIUM,
            triggers=("summarize", "summary", "overview", "abstract"),
        ),
        StageTemplate(
            name="key findings and evidence analysis",
            description="Analyze the key findings, supporting evidence, results, and how strongly the evidence supports the claims.",
            difficulty=Difficulty.MEDIUM,
            triggers=("finding", "findings", "evidence", "result", "results", "trend", "trends"),
        ),
        StageTemplate(
            name="rigorous limitations/risk critique",
            description="Critique limitations, risks, assumptions, validity threats, and implications that require rigorous reasoning.",
            difficulty=Difficulty.HARD,
            triggers=("rigorous", "limitation", "limitations", "risk", "risks", "critique", "critical", "weakness", "bias", "validity"),
        ),
    )

    def plan(self, task: str) -> RoutingPlan:
        """Return a stage-by-stage routing plan for a user task."""
        clean_task = task.strip()
        if not clean_task:
            raise ValueError("task must not be empty")

        instruction_text = self._instruction_text(clean_task)
        stages = tuple(self._build_semantic_stages(instruction_text))
        return RoutingPlan(
            original_task=clean_task,
            stages=stages,
            estimated_savings=self._estimate_savings(stages),
            quality_guardrail=(
                "Escalate any stage to the frontier tier when confidence is low, "
                "requirements are ambiguous, or the output has high-stakes impact."
            ),
        )

    def _instruction_text(self, task: str) -> str:
        """Keep user instructions and discard pasted source/reference text."""
        normalized = self._drop_source_sections(task)
        semantic_lines = [
            line.strip()
            for line in normalized.splitlines()
            if self._is_semantic_instruction_line(line)
        ]
        return " ".join(semantic_lines) or normalized.strip()

    def _drop_source_sections(self, task: str) -> str:
        earliest_boundary = len(task)
        for pattern in self._SOURCE_BOUNDARIES:
            match = re.search(pattern, task, flags=re.IGNORECASE)
            if match:
                earliest_boundary = min(earliest_boundary, match.start())
        return task[:earliest_boundary]

    def _is_semantic_instruction_line(self, line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if self._NOISE_LINE.match(stripped) or self._CITATION_FRAGMENT.match(stripped):
            return False
        if len(stripped) <= 3:
            return False
        return True

    def _build_semantic_stages(self, instruction_text: str) -> Iterable[Stage]:
        lowered = instruction_text.lower()
        emitted = False
        for template in self._STAGE_TEMPLATES:
            if self._contains_any(lowered, template.triggers):
                emitted = True
                model, effort = self._route(template.difficulty)
                yield Stage(
                    name=template.name,
                    description=template.description,
                    difficulty=template.difficulty,
                    recommended_model=model,
                    reasoning_effort=effort,
                    rationale=self._rationale(template.difficulty),
                )

        if not emitted:
            difficulty = self._classify(instruction_text)
            model, effort = self._route(difficulty)
            yield Stage(
                name="requested task",
                description=instruction_text,
                difficulty=difficulty,
                recommended_model=model,
                reasoning_effort=effort,
                rationale=self._rationale(difficulty),
            )

    def _classify(self, text: str) -> Difficulty:
        lowered = text.lower()
        if self._contains_any(lowered, ("rigorous", "optimize", "prove", "derive", "strategy", "architecture", "legal", "medical", "financial", "security", "risk", "critique", "multi-step", "ambiguous")):
            return Difficulty.HARD
        if self._contains_any(lowered, ("summarize", "compare", "classify", "analysis", "trends", "organize", "outline", "cluster")):
            return Difficulty.MEDIUM
        return Difficulty.EASY

    def _route(self, difficulty: Difficulty) -> tuple[ModelTier, str]:
        if difficulty is Difficulty.EASY:
            return ModelTier.ECONOMY, "low"
        if difficulty is Difficulty.MEDIUM:
            return ModelTier.BALANCED, "medium"
        return ModelTier.FRONTIER, "high"

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
