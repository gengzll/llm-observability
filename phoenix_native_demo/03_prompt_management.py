"""Phoenix native 模式 — Prompt 版本管理.

Phoenix 的 prompts API 是 provider-agnostic 的: 拉下来 prompt 对象后,
prompt.format() 直接渲染成 OpenAI Chat Completion 入参格式,
**完全不需要 LangChain** 中间层.

核心 API:
    client.prompts.create(name, version=PromptVersion([...]))   -> 推送
    client.prompts.get(prompt_identifier=name)                  -> 拉最新
    client.prompts.get(..., tag="prod")                         -> 按 tag 拉
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
from phoenix.client import Client
from phoenix.client.types import PromptVersion

from agent import build_openai_client

load_dotenv()

PROMPT_NAME = "cs-agent-native-system"


def push_initial_prompt():
    client = Client()
    version = PromptVersion(
        [
            {
                "role": "system",
                "content": (
                    "你是一名 {{company}} 的客服助手。请用 {{tone}} 的语气, "
                    "在 1-3 句话内回答用户的 {{category}} 类问题. 不要编造信息."
                ),
            },
            {"role": "user", "content": "{{question}}"},
        ],
        model_name="glm-4-flash",
    )

    created = client.prompts.create(
        name=PROMPT_NAME,
        prompt_description="native demo 客服 system prompt",
        version=version,
    )
    print(f"已推送 prompt '{PROMPT_NAME}' (version_id={getattr(created, 'id', '?')})")


def pull_and_use_prompt():
    """演示从 Phoenix 拉 prompt → 渲染 → 直接喂裸 OpenAI SDK."""
    client = Client()
    prompt = client.prompts.get(prompt_identifier=PROMPT_NAME)

    rendered = prompt.format(
        variables={
            "company": "示例电商",
            "tone": "亲切",
            "category": "退款",
            "question": "电子产品多久能退?",
        }
    )

    # rendered["messages"] 是标准的 OpenAI chat completion messages 格式,
    # 直接喂裸 SDK, 不要 LangChain.
    oai = build_openai_client()
    model = os.getenv("OPENAI_MODEL", "glm-4-flash")
    resp = oai.chat.completions.create(
        model=model,
        messages=rendered["messages"],
    )
    print("答案:", resp.choices[0].message.content)


def pull_by_tag():
    """演示按 tag 拉取 prompt. 首次运行预期失败 (没打过 :prod tag)."""
    client = Client()
    try:
        prompt = client.prompts.get(prompt_identifier=PROMPT_NAME, tag="prod")
        print(f"成功拉取 :prod tag (version={prompt.id})")
    except Exception:
        print("没有 :prod tag — 首次运行的预期行为. 到 UI > Prompts 给某个 version 打 'prod' tag 后, 这里就能拉到.")


if __name__ == "__main__":
    push_initial_prompt()
    pull_and_use_prompt()
    pull_by_tag()
