"""LangSmith — 离线评估 (Evaluation).

核心 API: ``client.evaluate(target, data, evaluators, ...)``

注意:
    官方推荐用 openevals 提供的 LLM-as-judge, 但它依赖 OpenAI 的 structured output
    (JSON mode), 智谱 / DeepSeek 等兼容网关不支持. 所以这里改用手写 LLM-as-judge,
    和 Langfuse / Phoenix demo 风格统一, 也更便携.

工作流:
    1. 把评估集上传成 LangSmith dataset (04_dataset.py)
    2. 写 target(inputs) -> outputs
    3. 写 evaluator(inputs, outputs, reference_outputs) -> dict
    4. client.evaluate(...) 自动遍历 dataset, 跑 target, 跑 evaluator, 上报 UI
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import Client

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
# target: 把 agent 包成 (inputs -> outputs) 的函数
# ---------------------------------------------------------------------------
def target(inputs: dict) -> dict:
    agent = build_agent()
    answer = ask(agent, inputs["input"])
    return {"output": answer}


# ---------------------------------------------------------------------------
# evaluators: 手写 LLM-as-judge + 启发式长度检查
# ---------------------------------------------------------------------------
def correctness_evaluator(inputs: dict, outputs: dict, reference_outputs: dict):
    score = llm_as_judge(
        question=inputs["input"],
        output=outputs["output"],
        expected=reference_outputs["output"],
    )
    return {"key": "correctness", "score": score}


def length_evaluator(outputs: dict):
    length = len(outputs["output"])
    return {
        "key": "length_ok",
        "score": 1.0 if 10 <= length <= 200 else 0.0,
        "comment": f"length={length}",
    }


# ---------------------------------------------------------------------------
# 跑评估
# ---------------------------------------------------------------------------
def run_evaluation():
    client = Client()
    results = client.evaluate(
        target,
        data=DATASET_NAME,
        evaluators=[correctness_evaluator, length_evaluator],
        experiment_prefix="baseline-glm-4-flash",
        max_concurrency=4,
    )
    print("评估完成, 在 LangSmith UI > Experiments 查看结果.")
    return results


if __name__ == "__main__":
    run_evaluation()
