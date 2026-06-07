"""Langfuse — 离线评估 (Dataset Experiments).

Langfuse v3 SDK 提供统一 API ``langfuse.run_experiment(name, data, task, evaluators)``,
和 Phoenix ``run_experiment`` / Opik ``evaluate`` 风格一致.

工作流:
    1. 04_dataset.py 先把测试集上传到 Langfuse
    2. 本文件定义 task(item) -> output  和 evaluators(input, output, expected_output)
    3. langfuse.run_experiment 自动遍历 dataset, 并发跑 task + evaluators, 上报 UI
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langfuse import get_client
from langfuse.experiment import Evaluation

from common.sample_agent import ask, build_agent, build_llm
from common.sample_dataset import DATASET_NAME

load_dotenv()


JUDGE_SYSTEM = (
    "你是评审, 判断 [候选答案] 是否在语义上等价于 [参考答案]. "
    "完全一致输出 1.0, 大致一致输出 0.5, 不一致输出 0.0. 只输出一个数字, 不要解释."
)


def llm_as_judge(question: str, output: str, expected: str) -> float:
    llm = build_llm(temperature=0.0)
    resp = llm.invoke(
        [
            SystemMessage(content=JUDGE_SYSTEM),
            HumanMessage(
                content=f"用户问题: {question}\n候选答案: {output}\n参考答案: {expected}"
            ),
        ]
    )
    try:
        return float(resp.content.strip().split()[0])
    except (ValueError, IndexError):
        return 0.0


# ---------------------------------------------------------------------------
# task: 接收 dataset item, 跑 agent, 返回 output
# ---------------------------------------------------------------------------
def task(*, item, **kwargs):
    agent = build_agent()
    return ask(agent, item.input["input"])


# ---------------------------------------------------------------------------
# evaluator: 接收 input/output/expected_output, 返回 Evaluation 对象
# ---------------------------------------------------------------------------
def correctness_evaluator(*, input, output, expected_output, **kwargs):
    score = llm_as_judge(
        question=input["input"],
        output=output,
        expected=expected_output["output"],
    )
    return Evaluation(name="correctness", value=score)


def length_evaluator(*, output, **kwargs):
    """启发式: 答案长度 10-200 字符算合理."""
    length = len(output)
    return Evaluation(
        name="length_ok",
        value=1.0 if 10 <= length <= 200 else 0.0,
        comment=f"length={length}",
    )


def run_experiment(run_name: str | None = None) -> None:
    # 自动读取当前 .env 里的 OPENAI_MODEL 作为 run 名后缀; 默认 'unknown'.
    model = os.getenv("OPENAI_MODEL", "unknown")
    run_name = run_name or f"baseline-{model}"
    langfuse = get_client()
    dataset = langfuse.get_dataset(DATASET_NAME)

    result = langfuse.run_experiment(
        name="baseline",
        run_name=run_name,
        description=f"baseline run with {model}",
        data=dataset.items,
        task=task,
        evaluators=[correctness_evaluator, length_evaluator],
        max_concurrency=4,
    )
    langfuse.flush()
    print(f"Experiment '{run_name}' 完成.")
    print(f"在 UI > Datasets > {DATASET_NAME} > Runs > {run_name} 查看.")
    if hasattr(result, "item_results"):
        print(f"共 {len(result.item_results)} 个 item 完成.")


if __name__ == "__main__":
    run_experiment()
