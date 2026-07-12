"""MLflow demo — Prompt 版本管理.

MLflow 3.0+ 引入 Prompt Registry:
    mlflow.genai.register_prompt(name, template, commit_message, tags)  -> 创建/新版本
    mlflow.genai.load_prompt(name)                                       -> 拉最新
    mlflow.genai.load_prompt(f"{name}/1")                                -> 按 version 拉
    mlflow.genai.load_prompt(f"prompts:/{name}@production")              -> 按 alias 拉

变量语法用双大括号 {{var}} (mustache), 和 Langfuse / Phoenix / Opik 一致.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mlflow
from dotenv import load_dotenv

load_dotenv()

mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))

from agent_native import build_openai_client  # noqa: E402

PROMPT_NAME = "cs-agent-mlflow-system"


def push_initial_prompt():
    prompt = mlflow.genai.register_prompt(
        name=PROMPT_NAME,
        template=(
            "你是一名 {{company}} 的客服助手。请用 {{tone}} 的语气, "
            "在 1-3 句话内回答用户的 {{category}} 类问题. 不要编造信息.\n\n"
            "用户问题: {{question}}"
        ),
        commit_message="initial version",
        tags={"env": "dev", "owner": "demo"},
    )
    print(f"已推送 prompt '{prompt.name}' v{prompt.version}")


def pull_and_use_prompt():
    prompt = mlflow.genai.load_prompt(PROMPT_NAME)  # 默认拉最新

    rendered = prompt.format(
        company="示例电商",
        tone="亲切",
        category="退款",
        question="电子产品多久能退?",
    )

    client = build_openai_client()
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "glm-4-flash"),
        messages=[{"role": "user", "content": rendered}],
    )
    print("答案:", resp.choices[0].message.content)


def pull_by_alias():
    """演示按 alias 拉取 prompt. 首次运行预期会失败 — 因为还没打过 alias.

    在 UI > Prompts > 选某个 version > Set alias 打 'production' 后, 这里就能拉到.
    """
    try:
        prompt = mlflow.genai.load_prompt(f"prompts:/{PROMPT_NAME}@production")
        print(f"成功拉取 @production alias (v{prompt.version})")
    except Exception:
        print("没有 @production alias — 首次运行的预期行为. 到 UI > Prompts 打 alias 后可拉.")


if __name__ == "__main__":
    push_initial_prompt()
    pull_and_use_prompt()
    pull_by_alias()
