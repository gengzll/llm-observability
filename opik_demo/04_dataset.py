"""Opik — 数据集管理 (Datasets).

核心 API:
    client = opik.Opik()
    dataset = client.get_or_create_dataset(name=..., description=...)
    dataset.insert(items=[{"input": "...", "expected": "..."}, ...])

dataset 是 schema-free 的 list[dict], 在 task / metric 里可以拿到 item 的全部字段.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import opik
from dotenv import load_dotenv

from common.sample_dataset import DATASET_DESCRIPTION, DATASET_NAME, EVAL_EXAMPLES

load_dotenv()


def upload_dataset():
    client = opik.Opik()
    dataset = client.get_or_create_dataset(
        name=DATASET_NAME,
        description=DATASET_DESCRIPTION,
    )
    # dataset.insert 在 server 侧用 (item hash) 去重, 重复跑不会膨胀
    dataset.insert(
        items=[
            {"input": ex["input"], "expected": ex["expected"]}
            for ex in EVAL_EXAMPLES
        ]
    )
    print(f"已写入 {len(EVAL_EXAMPLES)} 条到 dataset '{DATASET_NAME}'.")
    print("到 http://localhost:5173 > Datasets 查看, 再用 02_evaluation.py 跑 eval.")


def list_dataset():
    client = opik.Opik()
    dataset = client.get_dataset(name=DATASET_NAME)
    items = dataset.get_items()
    for i, item in enumerate(items, 1):
        print(f"[{i}] {item}")


if __name__ == "__main__":
    upload_dataset()
    print("\n--- dataset items ---")
    list_dataset()
