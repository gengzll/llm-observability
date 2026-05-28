"""Phoenix — 链路追踪 (Tracing).

Phoenix 完全基于 OpenInference (OTel 的 LLM 语义约定) + OpenTelemetry, 集成方式:

    from phoenix.otel import register
    tracer_provider = register(project_name="...", auto_instrument=True)

    # auto_instrument=True 会自动加载所有已安装的 openinference-instrumentation-* 包,
    # 例如 openinference-instrumentation-langchain 会自动 instrument LangChain/LangGraph.

环境变量 (本地自托管):
    PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006

本文件演示:
    A. register(auto_instrument=True) — 一键自动埋点 (推荐, 适合 LangGraph)
    B. 手动 LangChainInstrumentor.instrument() — 等价但更显式
    C. 在 trace 上加 attributes / tags
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from openinference.instrumentation import using_attributes
from phoenix.otel import register

from common.sample_agent import ask, build_agent

load_dotenv()


# ---------------------------------------------------------------------------
# A. 自动埋点 (推荐)
# ---------------------------------------------------------------------------
def demo_auto_instrument():
    # auto_instrument=True: 自动 patch 所有装好的 openinference 适配器
    register(
        project_name="llm-obs-demo",
        auto_instrument=True,
        # endpoint 默认从 PHOENIX_COLLECTOR_ENDPOINT 环境变量读, 这里也可显式传:
        # endpoint="http://localhost:6006/v1/traces",
    )
    agent = build_agent()
    answer = ask(agent, "我的订单 A1001 到哪里了?")
    print("[A] auto-instrument answer:", answer)


# ---------------------------------------------------------------------------
# B. 显式 instrument LangChain (等价于 A 自动模式, 但能控制时机)
# ---------------------------------------------------------------------------
def demo_explicit_instrument():
    from openinference.instrumentation.langchain import LangChainInstrumentor

    tracer_provider = register(project_name="llm-obs-demo", auto_instrument=False)
    LangChainInstrumentor().instrument(tracer_provider=tracer_provider)

    agent = build_agent()
    answer = ask(agent, "电子产品多久能退?")
    print("[B] explicit-instrument answer:", answer)


# ---------------------------------------------------------------------------
# C. 给 trace 加 session_id / user_id / metadata (UI 里可筛)
# ---------------------------------------------------------------------------
def demo_attributes():
    register(project_name="llm-obs-demo", auto_instrument=True)
    agent = build_agent()
    with using_attributes(
        session_id="s-5678",
        user_id="u-1234",
        tags=["channel:web", "experiment:baseline"],
        metadata={"version": "v1.0"},
    ):
        answer = ask(agent, "A1003 我收到了, 能查到记录吗?")
        print("[C] tagged answer:", answer)


if __name__ == "__main__":
    # 注: register() 只能调用一次, 这里依次跑 3 个 demo 实际上 B / C 复用了 A 的 provider
    demo_auto_instrument()
    demo_explicit_instrument()
    demo_attributes()
    print("\n打开 http://localhost:6006 查看 trace (project: llm-obs-demo).")
