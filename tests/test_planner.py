from token_router import Difficulty, ModelTier, RouterPlanner


def test_routes_pdf_workflow_across_model_tiers():
    plan = RouterPlanner().plan(
        "Read a 5-page PDF, then summarize the key points, then produce hard analysis of risks"
    )

    assert [stage.recommended_model for stage in plan.stages] == [
        ModelTier.ECONOMY,
        ModelTier.BALANCED,
        ModelTier.FRONTIER,
    ]
    assert [stage.difficulty for stage in plan.stages] == [
        Difficulty.EASY,
        Difficulty.MEDIUM,
        Difficulty.HARD,
    ]


def test_empty_task_is_rejected():
    planner = RouterPlanner()

    try:
        planner.plan("   ")
    except ValueError as exc:
        assert "task must not be empty" in str(exc)
    else:
        raise AssertionError("empty task should raise ValueError")
