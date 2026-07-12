"""MLflow demo — Tracing (裸 SDK 版 + LangGraph 版 都跑一遍).

分别演示 2 种 instrument 姿势:
    A. 裸 OpenAI SDK: mlflow.openai.autolog() 自动 instrument + @mlflow.trace 手埋 tool span
    B. LangGraph:     mlflow.langchain.autolog() 自动 instrument, agent 代码 0 修改

MLflow UI (http://localhost:5000) 会看到两个独立 experiment:
    - mlflow-native-demo    : 裸 SDK 版的 trace (agent.run > LLM > tool 嵌套)
    - mlflow-langgraph-demo : LangGraph 版的 trace (LangGraph 自动展开的 node)
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mlflow
from dotenv import load_dotenv

load_dotenv()

mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))


# ---------------------------------------------------------------------------
# A. 裸 OpenAI SDK 版
# ---------------------------------------------------------------------------
def demo_native():
    mlflow.set_experiment("mlflow-native-demo")
    # 自动 instrument OpenAI SDK: 每次 chat.completions.create 产生一个 LLM span
    mlflow.openai.autolog()

    from agent_native import run_agent

    questions = [
        "我的订单 A1001 到哪里了?",
        "电子产品多久能退?",
        "A1003 我收到了, 衣服可以退吗?",
    ]
    for q in questions:
        answer = run_agent(q)
        print(f"[native] Q: {q}")
        print(f"[native] A: {answer}\n")


# ---------------------------------------------------------------------------
# B. LangGraph 版 (0 agent 代码修改)
# ---------------------------------------------------------------------------
def demo_langgraph():
    mlflow.set_experiment("mlflow-langgraph-demo")
    # 自动 instrument LangChain / LangGraph, 每个 node / LLM / tool 都是一个 span
    mlflow.langchain.autolog()

    from agent_langgraph import ask, build_agent

    agent = build_agent()
    questions = [
        "我的订单 A1001 到哪里了?",
        "电子产品多久能退?",
    ]
    for q in questions:
        answer = ask(agent, q)
        print(f"[langgraph] Q: {q}")
        print(f"[langgraph] A: {answer}\n")


if __name__ == "__main__":
    demo_native()
    demo_langgraph()
    print("打开 http://localhost:5000 查看 traces")
    print("  Experiments > mlflow-native-demo      : 裸 SDK 版")
    print("  Experiments > mlflow-langgraph-demo   : LangGraph 版")
