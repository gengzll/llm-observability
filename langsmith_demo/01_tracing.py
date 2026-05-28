"""LangSmith — 链路追踪 (Tracing).

LangSmith 是 LangChain 官方观测平台, 和 LangGraph 同源, 集成最丝滑:
**只要设置环境变量, 不写一行代码, LangGraph 会自动上报 trace.**

环境变量:
    LANGSMITH_TRACING=true
    LANGSMITH_API_KEY=lsv2_pt_xxx
    LANGSMITH_PROJECT=llm-obs-demo

运行后到 https://smith.langchain.com/ 查看 trace.

本文件演示 3 种 trace 接入方式:
    A. 零代码 (env vars only) — 推荐, 适合 LangGraph / LangChain 应用
    B. @traceable 装饰器     — 给非 LangChain 的函数补埋点
    C. RunTree 手动构造      — 完全自定义 span 结构 (少用)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from langsmith import traceable

from common.sample_agent import ask, build_agent

load_dotenv()


# ---------------------------------------------------------------------------
# A. 零代码 tracing — 最常用
# ---------------------------------------------------------------------------
def demo_auto_tracing():
    """只要环境变量 LANGSMITH_TRACING=true, LangGraph 自动上报."""
    agent = build_agent()
    answer = ask(agent, "我的订单 A1001 到哪里了?")
    print("[A] auto-tracing answer:", answer)


# ---------------------------------------------------------------------------
# B. @traceable 装饰器 — 给非 LangChain 函数补埋点
# ---------------------------------------------------------------------------
@traceable(run_type="chain", name="rag_pipeline")
def rag_pipeline(question: str) -> str:
    """演示一个非 LangChain 的自定义函数, 通过 @traceable 装饰也能进入 trace 树."""
    # 这里把 LangGraph agent 当成子步骤, 自动嵌套到 rag_pipeline span 下面
    agent = build_agent()
    return ask(agent, question)


def demo_traceable_decorator():
    answer = rag_pipeline("电子产品多久能退?")
    print("[B] @traceable answer:", answer)


# ---------------------------------------------------------------------------
# C. 给单次调用打 metadata / tags (便于在 UI 里筛选)
# ---------------------------------------------------------------------------
def demo_metadata_and_tags():
    agent = build_agent()
    config = {
        "tags": ["channel:web", "experiment:baseline"],
        "metadata": {"user_id": "u-1234", "session_id": "s-5678"},
        "run_name": "order-query-with-meta",
    }
    answer = ask(agent, "A1003 我收到了, 能查到记录吗?", config=config)
    print("[C] tagged answer:", answer)


if __name__ == "__main__":
    demo_auto_tracing()
    demo_traceable_decorator()
    demo_metadata_and_tags()
    print("\n打开 https://smith.langchain.com/ 在 project 'llm-obs-demo' 下查看 trace.")
