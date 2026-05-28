"""Langfuse — 数据集管理 (Dataset & Items).

核心 API:
    langfuse.create_dataset(name, description, metadata)
    langfuse.create_dataset_item(dataset_name, input, expected_output, metadata)
    langfuse.get_dataset(name).items

两种数据来源:
    1. 代码里写死的种子集 (本例)
    2. 从生产 trace 里挑 trace -> "Add to dataset" (UI 操作)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from langfuse import get_client

from common.sample_dataset import DATASET_DESCRIPTION, DATASET_NAME, EVAL_EXAMPLES

load_dotenv()


def upload_dataset():
    langfuse = get_client()
    # create_dataset 是幂等的, 已存在不会报错
    langfuse.create_dataset(name=DATASET_NAME, description=DATASET_DESCRIPTION)

    for ex in EVAL_EXAMPLES:
        langfuse.create_dataset_item(
            dataset_name=DATASET_NAME,
            input={"input": ex["input"]},
            expected_output={"output": ex["expected"]},
        )

    langfuse.flush()
    print(f"已写入 {len(EVAL_EXAMPLES)} 条 dataset items 到 {DATASET_NAME}.")
    print("到 http://localhost:3000 > Datasets 下查看, 再用 02_evaluation.py 跑 eval.")


def list_dataset():
    langfuse = get_client()
    dataset = langfuse.get_dataset(DATASET_NAME)
    for i, item in enumerate(dataset.items, 1):
        print(f"[{i}] input={item.input}, expected={item.expected_output}")


if __name__ == "__main__":
    upload_dataset()
    print("\n--- dataset items ---")
    list_dataset()
