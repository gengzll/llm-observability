"""Phoenix — 离线评估 (Experiments).

Phoenix 的评估范式叫 **Experiment**:
    client.experiments.run_experiment(dataset, task, evaluators)

工作流:
    1. 04_dataset.py 把测试集传到 Phoenix
    2. 写一个 task(example) -> output, 跑 agent
    3. 写 evaluators (可以多个, Phoenix 内置 ClassificationEvaluator / 自定义函数)
    4. run_experiment 自动 fan-out 跑所有样本 + 评分, 上报 UI
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from phoenix.client import Client
from phoenix.otel import register

from common.sample_agent import ask, build_agent, build_llm
from common.sample_dataset import DATASET_NAME

load_dotenv()


# 评估时也希望 trace 能被关联到 experiment, 先 register 一次
register(project_name="llm-obs-demo-eval", auto_instrument=True)


# ---------------------------------------------------------------------------
# task: example -> output
# ---------------------------------------------------------------------------
def task(example) -> str:
    """Phoenix 把 dataset 的每条 example (含 input/output/metadata) 传给 task."""
    agent = build_agent()
    return ask(agent, example.input["input"])


# ---------------------------------------------------------------------------
# evaluator: (output, expected) -> score
#
# 可以是普通函数返回 float / bool / dict, 也可以是 phoenix.evals 提供的
# ClassificationEvaluator (LLM-as-judge with 选项分类). 这里两种都演示.
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


def correctness_evaluator(output: str, expected: str) -> float:
    """自定义 LLM-as-judge — 普通 Python 函数."""
    llm = build_llm(temperature=0.0)
    resp = llm.invoke(JUDGE_PROMPT.format(output=output, expected=expected))
    try:
        return float(resp.content.strip().split()[0])
    except (ValueError, IndexError):
        return 0.0


def length_evaluator(output: str) -> dict:
    """启发式: 答案长度合理 (10-200 字符) 即可."""
    length = len(output)
    return {
        "score": 1.0 if 10 <= length <= 200 else 0.0,
        "label": "good_length" if 10 <= length <= 200 else "bad_length",
        "explanation": f"length={length}",
    }


def run_experiment():
    client = Client()
    dataset = client.datasets.get_dataset(dataset=DATASET_NAME)

    experiment = client.experiments.run_experiment(
        dataset=dataset,
        task=task,
        evaluators=[correctness_evaluator, length_evaluator],
        experiment_name="baseline-gpt-4o-mini",
        experiment_description="baseline run with gpt-4o-mini",
    )
    print(f"Experiment 完成: {experiment}")
    print("到 http://localhost:6006 > Datasets > Experiments 查看.")


if __name__ == "__main__":
    run_experiment()
