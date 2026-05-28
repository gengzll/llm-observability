"""Opik — 离线评估 (Evaluate).

核心 API:
    from opik.evaluation import evaluate
    from opik.evaluation.metrics import base_metric, score_result

    evaluate(
        experiment_name="...",
        dataset=opik.get_or_create_dataset("name"),
        task=lambda item: {"output": agent_run(item["input"])},
        scoring_metrics=[my_metric_instance, ...],
    )

Opik 的 metrics 是「类继承」式: 写一个继承 BaseMetric 的类, 实现 score() 即可.
内置了 Hallucination / AnswerRelevance / G-Eval / Moderation 等 LLM-as-judge metric,
也很方便自定义.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from opik import Opik
from opik.evaluation import evaluate
from opik.evaluation.metrics import base_metric, score_result

from common.sample_agent import ask, build_agent, build_llm
from common.sample_dataset import DATASET_NAME

load_dotenv()


# ---------------------------------------------------------------------------
# 自定义 LLM-as-judge metric
# ---------------------------------------------------------------------------
JUDGE_PROMPT = """\
你是评审, 判断 [候选答案] 是否在语义上等价于 [参考答案]:
- 完全一致 -> 1.0
- 大致一致 -> 0.5
- 不一致 -> 0.0

只输出一个数字, 不要解释.

候选答案: {output}
参考答案: {expected}
"""


class CorrectnessMetric(base_metric.BaseMetric):
    def __init__(self, name: str = "correctness"):
        super().__init__(name=name)
        self.llm = build_llm(temperature=0.0)

    def score(self, output: str, reference: str, **ignored) -> score_result.ScoreResult:
        resp = self.llm.invoke(JUDGE_PROMPT.format(output=output, expected=reference))
        try:
            value = float(resp.content.strip().split()[0])
        except (ValueError, IndexError):
            value = 0.0
        return score_result.ScoreResult(name=self.name, value=value)


class LengthMetric(base_metric.BaseMetric):
    """启发式: 答案长度合理 (10-200 字符)."""

    def __init__(self, name: str = "length_ok"):
        super().__init__(name=name)

    def score(self, output: str, **ignored) -> score_result.ScoreResult:
        length = len(output)
        return score_result.ScoreResult(
            name=self.name,
            value=1.0 if 10 <= length <= 200 else 0.0,
            reason=f"length={length}",
        )


# ---------------------------------------------------------------------------
# task: dataset item -> agent output
# ---------------------------------------------------------------------------
def task(dataset_item: dict) -> dict:
    agent = build_agent()
    answer = ask(agent, dataset_item["input"])
    # 返回的 dict 会作为各 metric.score() 的 kwargs
    return {"output": answer, "reference": dataset_item["expected"]}


def run_evaluation():
    client = Opik()
    dataset = client.get_dataset(name=DATASET_NAME)

    evaluate(
        experiment_name="baseline-gpt-4o-mini",
        dataset=dataset,
        task=task,
        scoring_metrics=[CorrectnessMetric(), LengthMetric()],
        experiment_config={"model": "gpt-4o-mini", "agent": "cs-v1"},
    )
    print("Experiment 完成, 到 http://localhost:5173 > Experiments 查看.")


if __name__ == "__main__":
    run_evaluation()
