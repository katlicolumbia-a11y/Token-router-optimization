from token_router import ModelTier, RouterPlanner


ACADEMIC_PAPER_EXTRACT = """
Summarize the paper, identify key findings and evidence, then provide a rigorous limitations and risk critique.

PDF content:
Journal of Example AI Research 12(3) 2026
Page 1
A. Smith, B. Jones, and C. Patel
Abstract
We study routing policies for language model inference using a mixed-method benchmark.
The system reduces cost while preserving answer quality across document-analysis tasks.
1
https://example.org/papers/router
Introduction
Prior work has explored cascades and speculative decoding.
Smith et al., 2024.
Methods
We evaluate 240 prompts across summarization, extraction, and hard critique tasks.
Results
The routed approach lowers weighted token cost by 41% with no statistically significant quality loss.
Discussion
The method can fail when task boundaries are ambiguous or when the initial extraction loses evidence.
References
[1] Smith et al. 2024. Model cascades for efficient reasoning.
[2] Jones et al. 2025. Token budgets in document analysis.
doi: 10.1234/example
2025
"""


def test_academic_paper_text_creates_semantic_workflow_stages():
    plan = RouterPlanner().plan(ACADEMIC_PAPER_EXTRACT)

    assert [stage.name for stage in plan.stages] == [
        "PDF extraction/intake",
        "paper summarization",
        "key findings and evidence analysis",
        "rigorous limitations/risk critique",
    ]
    assert [stage.recommended_model for stage in plan.stages] == [
        ModelTier.ECONOMY,
        ModelTier.BALANCED,
        ModelTier.BALANCED,
        ModelTier.FRONTIER,
    ]
    assert len(plan.stages) == 4
    assert all("Smith et al" not in stage.description for stage in plan.stages)
    assert all("https://" not in stage.description for stage in plan.stages)
