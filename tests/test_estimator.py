from token_router import RouterPlanner, TokenEstimator


def test_estimator_compares_routed_plan_to_frontier_baseline():
    plan = RouterPlanner().plan("Read a PDF, then summarize it, then produce hard risk analysis")
    comparison = TokenEstimator().compare(plan, "x" * 1200)

    assert comparison.estimated_input_tokens == 300
    assert comparison.routed_weighted_tokens < comparison.frontier_only_weighted_tokens
    assert comparison.estimated_savings_percent > 0
