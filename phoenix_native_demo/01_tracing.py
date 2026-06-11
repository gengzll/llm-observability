"""Phoenix native 模式 — Tracing.

埋点 3 层:
    1. agent.run 父 span      — agent.py 里手埋 (整次 agent run)
    2. LLM 调用 span           — OpenAIInstrumentor 自动产生 (每次 chat.completions.create)
    3. tool.* 子 span         — agent.py 里手埋 (每次 tool 调用)

依赖:
    - phoenix server 已通过 00_launch_phoenix.py 在另一个终端启动
    - openinference-instrumentation-openai 装好
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
from openinference.instrumentation import using_attributes
from openinference.instrumentation.openai import OpenAIInstrumentor
from phoenix.otel import register

from agent import run_agent

load_dotenv()


# ---------------------------------------------------------------------------
# 配置 OTel: trace 上报到本地 Phoenix server (走 PHOENIX_COLLECTOR_ENDPOINT)
# ---------------------------------------------------------------------------
tracer_provider = register(project_name="native-demo")

# ---------------------------------------------------------------------------
# 自动 instrument OpenAI SDK
# 之后每次 client.chat.completions.create 都自动产生一个 LLM span,
# 含 llm.model_name / llm.prompts / llm.token_count.* / output.value 等
# OpenInference 标准字段
# ---------------------------------------------------------------------------
OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)


# ---------------------------------------------------------------------------
# A. 基础调用 — 看 trace 的 agent.run / LLM / tool 嵌套结构
# ---------------------------------------------------------------------------
def demo_basic():
    answer = run_agent("我的订单 A1001 到哪里了?")
    print("[A] basic:", answer)


# ---------------------------------------------------------------------------
# B. 带 session_id / user_id / tags 的调用 (UI 里能筛)
# ---------------------------------------------------------------------------
def demo_with_attributes():
    with using_attributes(
        session_id="s-5678",
        user_id="u-1234",
        tags=["channel:web", "experiment:baseline"],
        metadata={"version": "v1.0"},
    ):
        answer = run_agent("电子产品多久能退?")
        print("[B] with attributes:", answer)


# ---------------------------------------------------------------------------
# C. 多步 / 多 tool 调用 - 在 UI 上能清楚看到嵌套结构
# ---------------------------------------------------------------------------
def demo_multi_tool():
    answer = run_agent("A1003 我收到了, 衣服可以退吗?")
    print("[C] multi-tool:", answer)


if __name__ == "__main__":
    demo_basic()
    demo_with_attributes()
    demo_multi_tool()
    print("\n打开 http://localhost:6006 看 trace (project: native-demo).")
