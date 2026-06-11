"""Phoenix native 模式 — Dataset.

和 phoenix_demo/04_dataset.py 几乎一样 — dataset API 本身不依赖 LangChain.
共用 common/sample_dataset.py 的数据集, 方便和 LangGraph 版横向对比评估分数.
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
        # Phoenix v15 返回 dict, 旧版返回对象 - 兼容
        get = (lambda k: example[k]) if isinstance(example, dict) else (lambda k: getattr(example, k))
        print(f"[{i}] input={get('input')}, output={get('output')}")


if __name__ == "__main__":
    upload_dataset()
    print("\n--- dataset examples ---")
    list_dataset()
