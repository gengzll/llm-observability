"""Phoenix — 数据集管理 (Datasets).

核心 API:
    client.datasets.create_dataset(name, inputs, outputs, metadata)   -> 创建/追加
    client.datasets.get_dataset(dataset=name)

Phoenix dataset 的 inputs / outputs 是 list[dict], 一一对应.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from phoenix.client import Client

from common.sample_dataset import DATASET_DESCRIPTION, DATASET_NAME, EVAL_EXAMPLES

load_dotenv()


def upload_dataset():
    client = Client()
    inputs = [{"input": ex["input"]} for ex in EVAL_EXAMPLES]
    outputs = [{"output": ex["expected"]} for ex in EVAL_EXAMPLES]

    dataset = client.datasets.create_dataset(
        name=DATASET_NAME,
        inputs=inputs,
        outputs=outputs,
        dataset_description=DATASET_DESCRIPTION,
    )
    print(f"已创建 dataset '{dataset.name}' (id={dataset.id}), 共 {len(inputs)} 条.")
    print("到 http://localhost:6006 > Datasets 查看, 再跑 02_evaluation.py.")


def list_dataset():
    client = Client()
    dataset = client.datasets.get_dataset(dataset=DATASET_NAME)
    for i, example in enumerate(dataset.examples, 1):
        print(f"[{i}] input={example.input}, output={example.output}")


if __name__ == "__main__":
    upload_dataset()
    print("\n--- dataset examples ---")
    list_dataset()
