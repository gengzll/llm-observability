"""LangSmith — 数据集管理 (Dataset & Examples).

核心 API:
    client.create_dataset(dataset_name, description)
    client.create_examples(dataset_id, examples=[{"inputs": ..., "outputs": ...}])
    client.read_dataset(dataset_name)

两种数据来源:
    1. 代码里写死的种子集 (本例) -> 适合首版评估集
    2. 从生产 trace 里筛选 + 加 reference -> 适合持续扩充测试集
       (UI 操作: Project > Runs > 选中行 > Add to Dataset)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from langsmith import Client
from langsmith.utils import LangSmithConflictError

from common.sample_dataset import DATASET_DESCRIPTION, DATASET_NAME, EVAL_EXAMPLES

load_dotenv()


def upload_dataset():
    """把 common/sample_dataset.py 里的种子集上传到 LangSmith."""
    client = Client()

    try:
        dataset = client.create_dataset(
            dataset_name=DATASET_NAME,
            description=DATASET_DESCRIPTION,
        )
        print(f"创建 dataset: {dataset.name}")
    except LangSmithConflictError:
        dataset = client.read_dataset(dataset_name=DATASET_NAME)
        print(f"复用已有 dataset: {dataset.name}")

    # LangSmith 的 example 必须是 {"inputs": dict, "outputs": dict}
    examples = [
        {
            "inputs": {"input": ex["input"]},
            "outputs": {"output": ex["expected"]},
        }
        for ex in EVAL_EXAMPLES
    ]
    client.create_examples(dataset_id=dataset.id, examples=examples)
    print(f"已写入 {len(examples)} 条 examples.")
    print("到 LangSmith UI > Datasets 下查看, 再用 02_evaluation.py 跑 eval.")


def list_dataset():
    """读取并打印 dataset 内容."""
    client = Client()
    examples = list(client.list_examples(dataset_name=DATASET_NAME))
    for i, ex in enumerate(examples, 1):
        print(f"[{i}] inputs={ex.inputs}, outputs={ex.outputs}")


if __name__ == "__main__":
    upload_dataset()
    print("\n--- dataset 内容 ---")
    list_dataset()
