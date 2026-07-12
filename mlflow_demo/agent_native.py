"""MLflow demo — 裸 OpenAI SDK + 手写 agent loop, 用 MLflow tracing.

和 phoenix_native_demo/agent.py 逻辑完全一致, 差别只在 span 用 MLflow 而非 OTel:
    - agent.run 用 @mlflow.trace(span_type=AGENT) 装饰
    - LLM 调用由 mlflow.openai.autolog() 自动产生 (LLM type)
    - tool.* 用 mlflow.start_span(span_type=TOOL) 手埋
"""

import json
import os
from typing import Any

import mlflow
from mlflow.entities import SpanType
from openai import OpenAI


# ---------------------------------------------------------------------------
# 模拟订单系统 (字段和 common/sample_agent.py 完全一致)
# ---------------------------------------------------------------------------
_FAKE_ORDERS = {
    "A1001": {"status": "shipped", "carrier": "SF", "eta_days": 2},
    "A1002": {"status": "preparing", "carrier": None, "eta_days": 5},
    "A1003": {"status": "delivered", "carrier": "JD", "eta_days": 0},
}


def lookup_order(order_id: str) -> str:
    order = _FAKE_ORDERS.get(order_id.strip().upper())
    if order is None:
        return f"未找到订单 {order_id}"
    return (
        f"订单 {order_id} 状态={order['status']}, "
        f"承运={order['carrier'] or '尚未发货'}, "
        f"预计 {order['eta_days']} 天送达."
    )


def refund_policy(category: str) -> str:
    policies = {
        "electronics": "电子产品支持 7 天无理由退货, 需保持外包装完整.",
        "clothing": "服装类支持 15 天退换, 需吊牌完整未洗涤.",
        "food": "食品类一经售出不予退换, 食安问题除外.",
    }
    return policies.get(category.lower(), f"未收录品类 {category} 的退款政策.")


# ---------------------------------------------------------------------------
# OpenAI function-calling schema
# ---------------------------------------------------------------------------
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "lookup_order",
            "description": "根据订单号查询订单的物流状态. order_id 形如 'A1001'.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string", "description": "订单号"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "refund_policy",
            "description": "查询某类商品的退款政策. category 取值 electronics / clothing / food.",
            "parameters": {
                "type": "object",
                "properties": {"category": {"type": "string"}},
                "required": ["category"],
            },
        },
    },
]

TOOLS_REGISTRY = {"lookup_order": lookup_order, "refund_policy": refund_policy}

DEFAULT_SYSTEM_PROMPT = (
    "你是一名电商平台的客服助手。请基于工具查到的真实信息, 用 1-3 句话简洁回答用户问题. "
    "如果工具未返回结果, 直接说不知道, 不要编造."
)


def build_openai_client() -> OpenAI:
    """走 OPENAI_BASE_URL + OPENAI_API_KEY, 同代码支持 OpenAI / 智谱 / DeepSeek / vLLM."""
    return OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL") or None,
    )


@mlflow.trace(name="agent.run", span_type=SpanType.AGENT)
def run_agent(
    question: str,
    system_prompt: str | None = None,
    max_iter: int = 5,
) -> str:
    """裸 OpenAI SDK 实现的 agent loop.

    span 层级 (从 MLflow UI 看):
        agent.run (AGENT)
        ├── ChatCompletion (LLM)  ← mlflow.openai.autolog() 自动
        ├── tool.<name>  (TOOL)   ← mlflow.start_span 手埋
        ├── ChatCompletion (LLM)  ← 自动
        └── ...
    """
    client = build_openai_client()
    model = os.getenv("OPENAI_MODEL", "glm-4-flash")

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    final_answer = ""
    for _ in range(max_iter):
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS_SCHEMA,
        )
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            final_answer = msg.content or ""
            break

        for tc in msg.tool_calls:
            fn_name = tc.function.name
            with mlflow.start_span(name=f"tool.{fn_name}", span_type=SpanType.TOOL) as tool_span:
                tool_span.set_inputs({"arguments": tc.function.arguments})
                try:
                    fn_args = json.loads(tc.function.arguments)
                    fn = TOOLS_REGISTRY.get(fn_name)
                    result = fn(**fn_args) if fn else f"未知工具 {fn_name}"
                except Exception as e:
                    result = f"工具执行报错: {e}"
                tool_span.set_outputs({"result": str(result)[:500]})

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    return final_answer or "(agent 超过 max_iter, 未拿到最终答案)"


if __name__ == "__main__":
    # 裸跑不接 MLflow, 用来验证 agent 本身
    from dotenv import load_dotenv

    load_dotenv()
    print(run_agent("我的订单 A1001 到哪里了?"))
    print(run_agent("电子产品的退款政策是怎么样的?"))
