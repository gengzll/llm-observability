"""共享 LangGraph 示例 Agent.

一个简化的「订单客服」Agent:
    用户输入 -> LLM 决定要不要查工具 -> 调工具 -> LLM 汇总 -> 输出
体现了一个真实 Agent 的核心调用链 (LLM + Tool + 多步循环), 4 个 observability
框架都会基于这同一个 graph 演示 tracing / eval / prompt / dataset.

切换 LLM Provider:
    默认走 OpenAI; 改 OPENAI_BASE_URL + OPENAI_MODEL 即可指向 DeepSeek /
    Together / 本地 vLLM 等 OpenAI 兼容网关. 若要换成 Anthropic, 把
    build_llm() 里替换为 ChatAnthropic.
"""

from __future__ import annotations

import os
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition


# ---------------------------------------------------------------------------
# 1. 工具定义 (模拟订单系统)
# ---------------------------------------------------------------------------
_FAKE_ORDERS = {
    "A1001": {"status": "shipped", "carrier": "SF", "eta_days": 2},
    "A1002": {"status": "preparing", "carrier": None, "eta_days": 5},
    "A1003": {"status": "delivered", "carrier": "JD", "eta_days": 0},
}


@tool
def lookup_order(order_id: str) -> str:
    """根据订单号查询订单的物流状态. order_id 形如 'A1001'."""
    order = _FAKE_ORDERS.get(order_id.strip().upper())
    if order is None:
        return f"未找到订单 {order_id}"
    return (
        f"订单 {order_id} 状态={order['status']}, "
        f"承运={order['carrier'] or '尚未发货'}, "
        f"预计 {order['eta_days']} 天送达."
    )


@tool
def refund_policy(category: str) -> str:
    """查询某类商品 (electronics / clothing / food) 的退款政策."""
    policies = {
        "electronics": "电子产品支持 7 天无理由退货, 需保持外包装完整.",
        "clothing": "服装类支持 15 天退换, 需吊牌完整未洗涤.",
        "food": "食品类一经售出不予退换, 食安问题除外.",
    }
    return policies.get(category.lower(), f"未收录品类 {category} 的退款政策.")


TOOLS = [lookup_order, refund_policy]


# ---------------------------------------------------------------------------
# 2. LLM 工厂
# ---------------------------------------------------------------------------
DEFAULT_SYSTEM_PROMPT = (
    "你是一名电商平台的客服助手。请基于工具查到的真实信息, 用 1-3 句话简洁回答用户问题. "
    "如果工具未返回结果, 直接说不知道, 不要编造."
)


def build_llm(model: str | None = None, temperature: float = 0.0) -> ChatOpenAI:
    """构造统一的 LLM 实例.

    所有 4 个 observability 框架都用同一个 LLM 实例, 这样跑出来的 trace 才有可比性.
    """
    return ChatOpenAI(
        model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=temperature,
        base_url=os.getenv("OPENAI_BASE_URL"),  # None 时走默认 openai 网关
        api_key=os.getenv("OPENAI_API_KEY"),
    )


# ---------------------------------------------------------------------------
# 3. LangGraph state + 节点
# ---------------------------------------------------------------------------
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def build_agent(system_prompt: str | None = None):
    """构造一个可调用 (.invoke / .stream) 的 LangGraph agent.

    返回 compiled graph; 4 个 demo 都通过 graph.invoke({"messages": [...]} , config=...)
    的方式注入 callbacks 或 instrumentation.
    """
    llm = build_llm()
    llm_with_tools = llm.bind_tools(TOOLS)

    system_msg = SystemMessage(content=system_prompt or DEFAULT_SYSTEM_PROMPT)

    def call_llm(state: AgentState) -> AgentState:
        response = llm_with_tools.invoke([system_msg, *state["messages"]])
        return {"messages": [response]}

    graph = StateGraph(AgentState)
    graph.add_node("llm", call_llm)
    graph.add_node("tools", ToolNode(TOOLS))

    graph.add_edge(START, "llm")
    # tools_condition: 如果上一条 AIMessage 触发了 tool_calls -> "tools", 否则 -> END
    graph.add_conditional_edges("llm", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "llm")

    return graph.compile()


def ask(agent, question: str, config: dict | None = None) -> str:
    """便捷封装: 跑一轮对话, 拿到最终回答字符串."""
    result = agent.invoke({"messages": [("user", question)]}, config=config or {})
    return result["messages"][-1].content


if __name__ == "__main__":
    # 本地裸跑 (不接任何 observability 框架), 验证 agent 本身能跑通
    from dotenv import load_dotenv

    load_dotenv()
    agent = build_agent()
    print(ask(agent, "我的订单 A1001 到哪里了?"))
    print(ask(agent, "电子产品的退款政策是怎么样的?"))
