"""Phoenix native 模式 — Evaluation.

和 phoenix_demo/02_evaluation.py 完全一致的 client.experiments.run_experiment 流程,
只是 task 用裸 SDK 的 run_agent, judge 也用裸 OpenAI SDK (不依赖 LangChain).
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from openinference.instrumentation.openai import OpenAIInstrumentor
from phoenix.client import Client
from phoenix.otel import register

from agent import build_openai_client, run_agent
from common.sample_dataset import DATASET_NAME

load_dotenv()


# evaluation 时 trace 也要关联到 project, 先 register + instrument
tracer_provider = register(project_name="native-demo-eval")
OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)


# ---------------------------------------------------------------------------
# task: dataset example -> agent output
# ---------------------------------------------------------------------------
def task(example) -> str:
    return run_agent(example.input["input"])


# ---------------------------------------------------------------------------
# evaluator: LLM-as-judge + 长度检查
# 返回完整 dict (score + label + explanation) 让 Phoenix UI 显示得清楚
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


def correctness_evaluator(output: str, expected: str) -> dict:
    """裸 OpenAI SDK 实现的 LLM-as-judge (不依赖 LangChain)."""
    client = build_openai_client()
    model = os.getenv("OPENAI_MODEL", "glm-4-flash")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": JUDGE_PROMPT.format(output=output, expected=expected)},
        ],
        temperature=0.0,
    )
    raw = (resp.choices[0].message.content or "").strip()
    try:
        score = float(raw.split()[0])
    except (ValueError, IndexError):
        score = 0.0
    return {
        "score": score,
        "label": "correct" if score >= 0.8 else "partial" if score >= 0.4 else "incorrect",
        "explanation": f"judge raw: {raw[:80]}",
    }


def length_evaluator(output: str) -> dict:
    length = len(output)
    return {
        "score": 1.0 if 10 <= length <= 200 else 0.0,
        "label": "good_length" if 10 <= length <= 200 else "bad_length",
        "explanation": f"length={length}",
    }


def run_experiment():
    client = Client()
    dataset = client.datasets.get_dataset(dataset=DATASET_NAME)

    model = os.getenv("OPENAI_MODEL", "unknown")
    experiment = client.experiments.run_experiment(
        dataset=dataset,
        task=task,
        evaluators=[correctness_evaluator, length_evaluator],
        experiment_name=f"native-baseline-{model}",
        experiment_description=f"native (no langchain) baseline with {model}",
    )
    print(f"Experiment 完成: {experiment}")
    print("到 http://localhost:6006 > Datasets > Experiments 查看.")


if __name__ == "__main__":
    run_experiment()
