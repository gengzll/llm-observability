"""共享评估数据集.

4 个 observability 框架都会用这同一份数据集做 offline evaluation, 这样
跑出来的评估指标可以横向对比.

每条样本包含:
    - input:    用户问题
    - expected: 参考答案 (用于 LLM-as-judge 比对)
"""

from typing import TypedDict


class Example(TypedDict):
    input: str
    expected: str


EVAL_EXAMPLES: list[Example] = [
    {
        "input": "我的订单 A1001 到哪里了?",
        "expected": "订单 A1001 已发货, 由顺丰承运, 预计 2 天送达.",
    },
    {
        "input": "A1002 这个单子什么时候能发?",
        "expected": "订单 A1002 正在备货, 预计 5 天内送达.",
    },
    {
        "input": "A1003 我收到了, 能查到记录吗?",
        "expected": "订单 A1003 已送达, 京东配送.",
    },
    {
        "input": "电子产品多久能退?",
        "expected": "电子产品支持 7 天无理由退货, 需保持外包装完整.",
    },
    {
        "input": "衣服可以退吗?",
        "expected": "服装类支持 15 天退换, 需吊牌完整未洗涤.",
    },
    {
        "input": "食品能不能退货?",
        "expected": "食品类一经售出不予退换, 食安问题除外.",
    },
    {
        "input": "订单 A9999 在哪?",
        # 故意造一个不存在的订单, 测试 agent 是否会编造
        "expected": "未找到该订单, 请确认订单号是否正确.",
    },
]


DATASET_NAME = "agent-cs-eval-v1"  # 4 个 demo 都用同一个数据集名
DATASET_DESCRIPTION = "电商客服 Agent 离线评估集 v1 (订单查询 + 退款政策)"
