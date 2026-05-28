"""Langfuse — 离线评估 (Dataset Experiments).

Langfuse 的评估范式: **dataset.run(name) 包裹一个 trace**, 让框架知道这条 trace
属于哪个 experiment. 你需要在每条 trace 上自己写评分逻辑 (score), 再 link 回 trace.

工作流:
    1. 04_dataset.py 把测试集传到 Langfuse
    2. 本文件遍历 dataset.items, 每条 item:
          - 用 item.run(run_name=...) 起一个 experiment span
          - 跑 agent, 拿到 output
          - 用 LLM-as-judge 算分
          - langfuse.create_score() 把分数挂到当前 trace
    3. UI > Datasets > Runs 里能看到所有 trace 的得分汇总
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langfuse import get_client
from langfuse.langchain import CallbackHandler

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


def run_experiment(run_name: str = "baseline-gpt-4o-mini") -> None:
    langfuse = get_client()
    dataset = langfuse.get_dataset(DATASET_NAME)

    for item in dataset.items:
        # 关键: item.run() 把这次执行 link 回 dataset, 跑完 UI 可见
        with item.run(
            run_name=run_name,
            run_description="baseline run with gpt-4o-mini",
        ) as root_span:
            handler = CallbackHandler()
            agent = build_agent()
            answer = ask(
                agent, item.input["input"], config={"callbacks": [handler]}
            )

            score = llm_as_judge(
                question=item.input["input"],
                output=answer,
                expected=item.expected_output["output"],
            )

            # 把分数挂到这次 run 上
            root_span.score_trace(name="correctness", value=score)

    langfuse.flush()
    print(f"Experiment '{run_name}' 完成, UI > Datasets > {DATASET_NAME} > Runs 查看.")


if __name__ == "__main__":
    run_experiment()
