"""LangSmith — 离线评估 (Evaluation).

核心 API: ``client.evaluate(target, data, evaluators, ...)``

工作流:
    1. 把评估集上传成 LangSmith dataset (见 04_dataset.py)
    2. 写 target(inputs) -> outputs, 把 agent 包成一个可被评估的函数
    3. 写 evaluator(inputs, outputs, reference_outputs) -> {"key": ..., "score": ...}
       本例用 openevals 提供的 LLM-as-judge (CORRECTNESS_PROMPT)
    4. client.evaluate(...) 自动遍历 dataset, 跑 target, 跑 evaluator, 上报 UI
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from langsmith import Client
from openevals.llm import create_llm_as_judge
from openevals.prompts import CORRECTNESS_PROMPT

from common.sample_agent import ask, build_agent
from common.sample_dataset import DATASET_NAME

load_dotenv()


# ---------------------------------------------------------------------------
# 1. target: 把 agent 包成 (inputs -> outputs) 的函数
# ---------------------------------------------------------------------------
def target(inputs: dict) -> dict:
    agent = build_agent()
    answer = ask(agent, inputs["input"])
    return {"output": answer}


# ---------------------------------------------------------------------------
# 2. evaluator: LLM-as-judge, 看 output 是否和 expected 一致
# ---------------------------------------------------------------------------
def correctness_evaluator(inputs: dict, outputs: dict, reference_outputs: dict):
    """openevals 已内置一个 CORRECTNESS_PROMPT (英文), 这里直接复用.

    如需中文 / 业务定制, 把 prompt 替换为自己的字符串模板即可:
        prompt = '''
        你是一位评审, 判断 [actual] 是否在语义上等同于 [expected].
        actual: {outputs}
        expected: {reference_outputs}
        只输出 true / false.
        '''
    """
    judge = create_llm_as_judge(
        prompt=CORRECTNESS_PROMPT,
        model="openai:gpt-4o-mini",
        feedback_key="correctness",
    )
    return judge(
        inputs=inputs,
        outputs=outputs,
        reference_outputs=reference_outputs,
    )


# ---------------------------------------------------------------------------
# 3. 跑评估
# ---------------------------------------------------------------------------
def run_evaluation():
    client = Client()
    results = client.evaluate(
        target,
        data=DATASET_NAME,            # 04_dataset.py 里建好的 dataset 名
        evaluators=[correctness_evaluator],
        experiment_prefix="baseline-gpt-4o-mini",
        max_concurrency=4,
        # 想把多个版本对比: 把 experiment_prefix 改成 "v2-after-prompt-tune" 再跑一次,
        # UI 里就能 side-by-side diff.
    )
    print("评估完成, 在 LangSmith UI > Experiments 里查看结果.")
    return results


if __name__ == "__main__":
    run_evaluation()
