"""MLflow demo — Dataset.

MLflow 3.0+ 的 Datasets API 和 Phoenix / Langfuse / Opik 的语义有明显差异:

    - Phoenix / Langfuse / Opik:  dataset 是「一等公民」, 独立于 run 存在,
      UI 上有单独的 Datasets 视图, evaluation 时 dataset.items 遍历
    - MLflow:                     dataset 主要绑到 run 上 (mlflow.log_input),
      作为 run 的元数据存在; UI 里 Run 详情能看到, 也有独立的 Datasets 页

本 demo 展示两种记法:
    (a) 用 log_input 关联到 run  (MLflow 传统姿势)
    (b) 用 log_artifact 存 CSV  (更传统的 file-based 姿势)
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mlflow
import pandas as pd
from dotenv import load_dotenv

from common.sample_dataset import DATASET_NAME, EVAL_EXAMPLES

load_dotenv()

mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
mlflow.set_experiment("mlflow-dataset-demo")


def upload_dataset():
    df = pd.DataFrame([
        {"input": ex["input"], "expected": ex["expected"]}
        for ex in EVAL_EXAMPLES
    ])

    # 构造 MLflow Dataset 对象 (含 schema / profile 等元数据)
    dataset = mlflow.data.from_pandas(
        df,
        source="in-memory",
        name=DATASET_NAME,
    )

    with mlflow.start_run(run_name="dataset-upload") as run:
        # (a) log_input: 把 dataset 元数据关联到本次 run
        mlflow.log_input(dataset, context="eval")

        # (b) log_artifact: 把 CSV 存到 artifact_root, UI 里可下载
        csv_path = Path("dataset.csv")
        df.to_csv(csv_path, index=False)
        mlflow.log_artifact(str(csv_path))
        csv_path.unlink(missing_ok=True)

        print(f"已 log dataset '{dataset.name}' (共 {len(df)} 条)")
        print(f"到 http://localhost:5000/#/experiments/{run.info.experiment_id}/runs/{run.info.run_id} 查看.")

    print(f"\n--- {len(df)} 条数据 ---")
    for i, row in df.iterrows():
        print(f"[{i + 1}] input={row['input']!r}, expected={row['expected']!r}")


if __name__ == "__main__":
    upload_dataset()
