"""裸 OpenAI SDK + 手写 agent loop, 不用 LangChain / LangGraph.

设计目标:
    - 不依赖任何 agent 框架, 直接 client.chat.completions.create + 手动循环
    - 兼容所有 OpenAI 兼容网关 (智谱 / DeepSeek / 火山 / 阿里通义 / 本地 vLLM)
    - 自带 OpenTelemetry span:
        - agent.run     : 整次 agent run 的父 span (手埋)
        - LLM call      : OpenAIInstrumentor 自动产生
        - tool.<name>   : 每次 tool 调用一个子 span (手埋)
      让 Phoenix UI 能看到完整调用链
"""

import json
import os
from typing import Any

from openai import OpenAI
from opentelemetry import trace


# ---------------------------------------------------------------------------
# Tracer — 手埋的 span 用这个; LLM 调用的 span 由 openinference-instrumentation-openai
# 自动产生, 不用我们埋
# ---------------------------------------------------------------------------
_tracer = trace.get_tracer("phoenix_native_demo.agent")


# ---------------------------------------------------------------------------
# 模拟订单系统 (字段和 common/sample_agent.py 完全一致, 这样评估时和 LangGraph 版可以横向比)
# ---------------------------------------------------------------------------
_FAKE_ORDERS = {
    "A1001": {"status": "shipped", "carrier": "SF", "eta_days": 2},
    "A1002": {"status": "preparing", "carrier": None, "eta_days": 5},
    "A1003": {"status": "delivered", "carrier": "JD", "eta_days": 0},
}


def lookup_order(order_id: str) -> str:
    """根据订单号查询订单的物流状态."""
    order = _FAKE_ORDERS.get(order_id.strip().upper())
    if order is None:
        return f"未找到订单 {order_id}"
    return (
        f"订单 {order_id} 状态={order['status']}, "
        f"承运={order['carrier'] or '尚未发货'}, "
        f"预计 {order['eta_days']} 天送达."
    )


def refund_policy(category: str) -> str:
    """查询某类商品 (electronics / clothing / food) 的退款政策."""
    policies = {
        "electronics": "电子产品支持 7 天无理由退货, 需保持外包装完整.",
        "clothing": "服装类支持 15 天退换, 需吊牌完整未洗涤.",
        "food": "食品类一经售出不予退换, 食安问题除外.",
    }
    return policies.get(category.lower(), f"未收录品类 {category} 的退款政策.")


# ---------------------------------------------------------------------------
# OpenAI function-calling 格式的 tool schema (给 LLM 看, 决定要不要调)
# ---------------------------------------------------------------------------
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "lookup_order",
            "description": "根据订单号查询订单的物流状态. order_id 形如 'A1001'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "订单号"},
                },
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
                "properties": {
                    "category": {"type": "string"},
                },
                "required": ["category"],
            },
        },
    },
]

# tool name -> 真实 Python callable, agent 收到 LLM 的 tool_call 后查这个表执行
TOOLS_REGISTRY = {
    "lookup_order": lookup_order,
    "refund_policy": refund_policy,
}


DEFAULT_SYSTEM_PROMPT = (
    "你是一名电商平台的客服助手。请基于工具查到的真实信息, 用 1-3 句话简洁回答用户问题. "
    "如果工具未返回结果, 直接说不知道, 不要编造."
)


def build_openai_client() -> OpenAI:
    """构造 OpenAI 客户端 — 走 OPENAI_BASE_URL + OPENAI_API_KEY 环境变量.

    同一份代码可以指向 OpenAI 官方 / 智谱 / DeepSeek / 火山 / 本地 vLLM 等任何
    OpenAI 兼容网关.
    """
    return OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL") or None,
    )


def run_agent(
    question: str,
    system_prompt: str | None = None,
    max_iter: int = 5,
) -> str:
    """裸 OpenAI SDK 实现的 agent loop.

    控制流:
        user 问题
          → LLM (决定要不要调 tool)
          → 如果有 tool_calls: 执行 tool, 把结果作为 tool message 加回 messages
          → 再 LLM (基于 tool 结果给最终回答)
          → 如果没有 tool_calls 或达到 max_iter: 返回

    所有 LLM 调用都会被 OpenAIInstrumentor 自动包成 span;
    我们额外加 agent.run 父 span + tool.* 子 span, 让 Phoenix UI 显示完整结构.
    """
    client = build_openai_client()
    model = os.getenv("OPENAI_MODEL", "glm-4-flash")

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    with _tracer.start_as_current_span("agent.run") as agent_span:
        agent_span.set_attribute("input.value", question)
        agent_span.set_attribute("llm.model_name", model)

        final_answer = ""
        for _ in range(max_iter):
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS_SCHEMA,
            )
            msg = resp.choices[0].message

            # 把 assistant 的回复加入 messages 历史 (含 tool_calls 序列化)
            messages.append(msg.model_dump(exclude_none=True))

            if not msg.tool_calls:
                final_answer = msg.content or ""
                break

            # 执行每个 tool call, 每个一个独立的 span
            for tc in msg.tool_calls:
                fn_name = tc.function.name
                fn_args_raw = tc.function.arguments
                with _tracer.start_as_current_span(f"tool.{fn_name}") as tool_span:
                    tool_span.set_attribute("tool.name", fn_name)
                    tool_span.set_attribute("tool.arguments", fn_args_raw)
                    try:
                        fn_args = json.loads(fn_args_raw)
                        fn = TOOLS_REGISTRY.get(fn_name)
                        result = fn(**fn_args) if fn else f"未知工具 {fn_name}"
                    except Exception as e:
                        result = f"工具执行报错: {e}"
                        tool_span.set_attribute("error", True)
                    tool_span.set_attribute("tool.result", str(result)[:500])

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

        if not final_answer:
            final_answer = "(agent 超过 max_iter, 未拿到最终答案)"

        agent_span.set_attribute("output.value", final_answer)
        return final_answer


if __name__ == "__main__":
    # 裸跑 (不接 Phoenix), 用来 sanity check agent 本身能跑通
    from dotenv import load_dotenv

    load_dotenv()
    print(run_agent("我的订单 A1001 到哪里了?"))
    print(run_agent("电子产品的退款政策是怎么样的?"))
