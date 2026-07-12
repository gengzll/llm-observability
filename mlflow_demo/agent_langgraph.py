"""MLflow demo — LangGraph 版 agent (复用 common/sample_agent.py).

MLflow tracing 通过 `mlflow.langchain.autolog()` 自动完成, agent 代码本身不需要
任何修改 — 这是 MLflow 的优势 (相比裸 SDK 手埋 span, LangGraph 版更省事).

用法:
    import mlflow
    mlflow.langchain.autolog()

    from agent_langgraph import ask, build_agent
    agent = build_agent()
    answer = ask(agent, "订单 A1001 到哪了?")
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.sample_agent import ask, build_agent  # noqa: E402

__all__ = ["build_agent", "ask"]
