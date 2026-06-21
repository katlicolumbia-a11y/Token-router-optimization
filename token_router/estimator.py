"""Token and cost comparison helpers for routed plans."""

from __future__ import annotations

from dataclasses import dataclass

from .planner import ModelTier, RoutingPlan


DEFAULT_TOKEN_RATES: dict[ModelTier, float] = {
    ModelTier.ECONOMY: 0.35,
    ModelTier.BALANCED: 1.0,
    ModelTier.FRONTIER: 4.0,
}


@dataclass(frozen=True)
class TokenComparison:
    """Estimated routed-vs-frontier token usage for a plan."""

    estimated_input_tokens: int
    routed_weighted_tokens: int
    frontier_only_weighted_tokens: int
    estimated_savings_percent: int

    def to_dict(self) -> dict[str, int]:
        return {
            "estimated_input_tokens": self.estimated_input_tokens,
            "routed_weighted_tokens": self.routed_weighted_tokens,
            "frontier_only_weighted_tokens": self.frontier_only_weighted_tokens,
            "estimated_savings_percent": self.estimated_savings_percent,
        }


class TokenEstimator:
    """Estimate relative token cost for a routed plan.

    The estimate is deliberately provider-neutral. It treats frontier-only routing
    as the baseline and applies configurable relative cost weights to each model
    tier. Replace ``token_rates`` with real provider pricing or metered token
    counts when integrating with a production model gateway.
    """

    def __init__(self, token_rates: dict[ModelTier, float] | None = None) -> None:
        self._token_rates = token_rates or DEFAULT_TOKEN_RATES

    def compare(self, plan: RoutingPlan, source_text: str) -> TokenComparison:
        """Compare routed execution with sending every stage to the frontier tier."""
        input_tokens = self.estimate_tokens(source_text)
        if not plan.stages:
            return TokenComparison(input_tokens, 0, 0, 0)

        tokens_per_stage = max(1, round(input_tokens / len(plan.stages)))
        routed_weighted = round(
            sum(tokens_per_stage * self._token_rates[stage.recommended_model] for stage in plan.stages)
        )
        frontier_weighted = round(
            input_tokens * self._token_rates[ModelTier.FRONTIER]
        )
        savings = 0
        if frontier_weighted:
            savings = round((frontier_weighted - routed_weighted) / frontier_weighted * 100)
        return TokenComparison(input_tokens, routed_weighted, frontier_weighted, savings)

    def estimate_tokens(self, text: str) -> int:
        """Approximate tokens from text using a common 4-characters-per-token rule."""
        return max(1, round(len(text) / 4))
