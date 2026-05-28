"""Opik — 链路追踪 (Tracing).

Opik 提供 3 种 LangGraph 集成方式 (推荐第一种):
    1. OpikTracer callback + config={"callbacks": [tracer]}
    2. track_langgraph(app, tracer)   -> 一次性 wrap, 后续 invoke 自动追踪
    3. @track 装饰器                  -> 给任意 Python 函数补埋点

环境变量 (本地自托管):
    OPIK_URL_OVERRIDE=http://localhost:5173/api
    OPIK_WORKSPACE=default
    # OPIK_API_KEY=  本地模式不需要 API key

也可以一次性配置:
    >>> import opik; opik.configure(use_local=True)
    会在 ~/.opik.config 写入本地连接信息.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from opik import opik_context, track
from opik.integrations.langchain import OpikTracer

from common.sample_agent import ask, build_agent

load_dotenv()


# ---------------------------------------------------------------------------
# A. OpikTracer callback — LangGraph 集成 (主推)
# ---------------------------------------------------------------------------
def demo_callback_tracer():
    agent = build_agent()
    # 传 graph=app.get_graph(xray=True) 给 tracer, UI 里就能看到 graph 拓扑图
    tracer = OpikTracer(graph=agent.get_graph(xray=True), project_name="llm-obs-demo")
    answer = ask(agent, "我的订单 A1001 到哪里了?", config={"callbacks": [tracer]})
    print("[A] callback answer:", answer)


# ---------------------------------------------------------------------------
# B. @track 装饰器 — 给非 LangChain 函数补埋点
# ---------------------------------------------------------------------------
@track(name="rag_pipeline", project_name="llm-obs-demo")
def rag_pipeline(question: str) -> str:
    agent = build_agent()
    tracer = OpikTracer(graph=agent.get_graph(xray=True))
    # @track 创建的当前 trace 会自动 link 到 OpikTracer 的 span (基于 contextvars)
    return ask(agent, question, config={"callbacks": [tracer]})


def demo_track_decorator():
    answer = rag_pipeline("电子产品多久能退?")
    print("[B] @track answer:", answer)


# ---------------------------------------------------------------------------
# C. 给当前 trace 加 metadata / tags / 反馈分
# ---------------------------------------------------------------------------
@track(name="tagged-conversation", project_name="llm-obs-demo")
def tagged_conversation(question: str) -> str:
    # 在 @track 内部, opik_context.update_current_trace 可以改当前 trace
    opik_context.update_current_trace(
        tags=["channel:web", "experiment:baseline"],
        metadata={"version": "v1.0", "user_id": "u-1234"},
        feedback_scores=[
            {"name": "user_thumbs_up", "value": 1.0}
        ],
    )
    agent = build_agent()
    tracer = OpikTracer(graph=agent.get_graph(xray=True))
    return ask(agent, question, config={"callbacks": [tracer]})


def demo_metadata():
    answer = tagged_conversation("A1003 我收到了, 能查到记录吗?")
    print("[C] tagged answer:", answer)


if __name__ == "__main__":
    demo_callback_tracer()
    demo_track_decorator()
    demo_metadata()
    print("\n打开 http://localhost:5173 查看 trace (project: llm-obs-demo).")
