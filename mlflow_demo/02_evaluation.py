"""MLflow demo — Evaluation.

MLflow 传统上的评估姿势 (和其他 4 家不太一样):
    - 每次评估是一个 mlflow.start_run 上下文
    - 用 log_metric(name, value, step=i) 记单条得分
    - log_metric(name+"_avg", mean_value) 记聚合
    - log_artifact(csv) 存详细结果

也可以用 mlflow.evaluate() 高级 API, 但对智谱等兼容网关不友好 (类似 langsmith
的 openevals 问题). 所以本 demo 走手动 loop + LLM-as-judge, 稳定且清晰.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mlflow
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
mlflow.set_experiment("mlflow-eval-demo")
mlflow.openai.autolog()

from agent_native import build_openai_client, run_agent  # noqa: E402
from common.sample_dataset import EVAL_EXAMPLES  # noqa: E402


JUDGE_PROMPT = """\
你是评审, 判断 [候选答案] 是否在语义上等价于 [参考答案]:
- 完全一致 -> 1.0
- 大致一致 -> 0.5
- 不一致 -> 0.0

只输出一个数字, 不要解释.

候选答案: {output}
参考答案: {expected}
"""


def llm_judge(output: str, expected: str) -> float:
    client = build_openai_client()
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "glm-4-flash"),
        messages=[
            {"role": "user", "content": JUDGE_PROMPT.format(output=output, expected=expected)},
        ],
        temperature=0.0,
    )
    raw = (resp.choices[0].message.content or "").strip()
    try:
        return float(raw.split()[0])
    except (ValueError, IndexError):
        return 0.0


def run_evaluation():
    model = os.getenv("OPENAI_MODEL", "unknown")

    with mlflow.start_run(run_name=f"baseline-{model}") as run:
        mlflow.log_param("model", model)
        mlflow.log_param("num_examples", len(EVAL_EXAMPLES))
        mlflow.log_param("judge_model", model)

        results = []
        for i, ex in enumerate(EVAL_EXAMPLES):
            answer = run_agent(ex["input"])
            score = llm_judge(answer, ex["expected"])
            length_ok = 1.0 if 10 <= len(answer) <= 200 else 0.0

            # 每条样本的分数
            mlflow.log_metric("correctness", score, step=i)
            mlflow.log_metric("length_ok", length_ok, step=i)

            results.append({
                "input": ex["input"],
                "expected": ex["expected"],
                "actual": answer,
                "correctness": score,
                "length_ok": length_ok,
            })
            print(f"[{i + 1}/{len(EVAL_EXAMPLES)}] correctness={score}, length_ok={length_ok}")

        df = pd.DataFrame(results)
        correctness_avg = float(df["correctness"].mean())
        length_ok_avg = float(df["length_ok"].mean())

        # 聚合指标 (UI 顶部显示)
        mlflow.log_metric("correctness_avg", correctness_avg)
        mlflow.log_metric("length_ok_avg", length_ok_avg)

        # 详细结果存 artifact
        csv_path = Path("eval_results.csv")
        df.to_csv(csv_path, index=False)
        mlflow.log_artifact(str(csv_path))
        csv_path.unlink(missing_ok=True)

        print()
        print(f"Experiment 完成. Run ID: {run.info.run_id}")
        print(f"  correctness_avg = {correctness_avg:.3f}")
        print(f"  length_ok_avg   = {length_ok_avg:.3f}")
        print(f"到 http://localhost:5000/#/experiments/{run.info.experiment_id}/runs/{run.info.run_id} 查看.")


if __name__ == "__main__":
    run_evaluation()
