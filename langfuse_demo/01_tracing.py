"""Langfuse — 链路追踪 (Tracing).

Langfuse v3 SDK 是基于 OpenTelemetry 的, 集成 LangGraph 的官方推荐方式是:
    from langfuse.langchain import CallbackHandler
    handler = CallbackHandler()
    graph.invoke(..., config={"callbacks": [handler]})

CallbackHandler 会自动把 LangGraph 的 chain / llm / tool 调用全部转成 span 上报.

环境变量 (本地自托管):
    LANGFUSE_HOST=http://localhost:3000
    LANGFUSE_PUBLIC_KEY=pk-lf-xxx
    LANGFUSE_SECRET_KEY=sk-lf-xxx

本文件演示 3 种 trace 方式:
    A. CallbackHandler           — LangGraph / LangChain 集成 (主推)
    B. @observe 装饰器           — 给非 LangChain 的函数补埋点
    C. metadata / tags / user_id — 给 trace 打标签, 便于 UI 筛选
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from langfuse import get_client, observe
from langfuse.langchain import CallbackHandler

from common.sample_agent import ask, build_agent

load_dotenv()


# ---------------------------------------------------------------------------
# A. CallbackHandler — LangGraph 集成
# ---------------------------------------------------------------------------
def demo_callback_handler():
    handler = CallbackHandler()
    agent = build_agent()
    answer = ask(agent, "我的订单 A1001 到哪里了?", config={"callbacks": [handler]})
    print("[A] callback answer:", answer)


# ---------------------------------------------------------------------------
# B. @observe — 装饰任意函数, 自动生成 span
# ---------------------------------------------------------------------------
@observe(name="rag_pipeline", as_type="span")
def rag_pipeline(question: str) -> str:
    handler = CallbackHandler()
    agent = build_agent()
    # 因为我们在 @observe 内部, 这里的 CallbackHandler 会自动接到当前 trace 上,
    # 子 span 嵌套在 rag_pipeline 之下.
    return ask(agent, question, config={"callbacks": [handler]})


def demo_observe_decorator():
    answer = rag_pipeline("电子产品多久能退?")
    print("[B] @observe answer:", answer)


# ---------------------------------------------------------------------------
# C. 给 trace 打 metadata / tags / user_id
# ---------------------------------------------------------------------------
def demo_metadata_and_tags():
    """v3 SDK 推荐做法: 通过 config.metadata 直接给当前 trace 打 user_id / session_id / tags.
    CallbackHandler 会自动把这些字段提到 trace 级别."""
    handler = CallbackHandler()
    agent = build_agent()
    config = {
        "callbacks": [handler],
        "run_name": "tagged-conversation",
        "metadata": {
            "langfuse_user_id": "u-1234",
            "langfuse_session_id": "s-5678",
            "langfuse_tags": ["channel:web", "experiment:baseline"],
            "version": "v1.0",
        },
    }
    answer = ask(agent, "A1003 我收到了, 能查到记录吗?", config=config)
    print("[C] tagged answer:", answer)


if __name__ == "__main__":
    demo_callback_handler()
    demo_observe_decorator()
    demo_metadata_and_tags()

    # 进程退出前 flush 一下, 保证 batch 上报落库
    get_client().flush()
    print("\n打开 http://localhost:3000 查看 trace.")
