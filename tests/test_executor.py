from types import SimpleNamespace

from token_router import ModelTier, OpenAIStageExecutor, RouterPlanner


class FakeResponses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            output_text=f"output from {kwargs['model']}",
            usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        )


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


def test_executor_calls_selected_model_for_each_stage():
    client = FakeClient()
    plan = RouterPlanner().plan("Read a PDF, then summarize it, then produce hard risk analysis")
    executor = OpenAIStageExecutor(
        client=client,
        model_map={
            ModelTier.ECONOMY: "economy-model",
            ModelTier.BALANCED: "balanced-model",
            ModelTier.FRONTIER: "frontier-model",
        },
    )

    result = executor.execute(plan, "PDF text")

    assert [call["model"] for call in client.responses.calls] == [
        "economy-model",
        "balanced-model",
        "frontier-model",
    ]
    assert result.total_tokens == 45
    assert result.final_output == "output from frontier-model"
    assert all("reasoning" in call for call in client.responses.calls)
