"""Phoenix — Prompt 版本管理.

Phoenix 的 prompts API (8.x 引入):
    client.prompts.create(name, prompt_version=...)   -> 创建/新增版本
    client.prompts.get(prompt_identifier=name)        -> 拉取最新版
    client.prompts.get(prompt_identifier=name, tag="prod")  -> 按 tag 拉

Phoenix prompt 是「provider-agnostic」的: 可以一份 prompt 直接 format 成
OpenAI / Anthropic / 自定义 LLM 接口需要的格式.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from phoenix.client import Client
from phoenix.client.types import PromptVersion

from common.sample_agent import build_llm

load_dotenv()

PROMPT_NAME = "cs-agent-system"


def push_initial_prompt():
    client = Client()
    version = PromptVersion(
        # Phoenix 用 mustache 风格 {{var}}
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
        model_name="gpt-4o-mini",
    )

    created = client.prompts.create(
        name=PROMPT_NAME,
        prompt_description="电商客服 system prompt",
        version=version,
    )
    # phoenix>=v15: client.prompts.create 返回 PromptVersion, 不含 name 字段
    print(f"已推送 prompt '{PROMPT_NAME}' (version_id={getattr(created, 'id', '?')})")


def pull_and_use_prompt():
    client = Client()
    prompt = client.prompts.get(prompt_identifier=PROMPT_NAME)

    # format 成 OpenAI Chat Completion 入参
    rendered = prompt.format(
        variables={
            "company": "示例电商",
            "tone": "亲切",
            "category": "退款",
            "question": "电子产品多久能退?",
        }
    )

    llm = build_llm()
    answer = llm.invoke(rendered["messages"])
    print("答案:", answer.content)


def pull_by_tag():
    """演示按 tag 拉取 prompt. 首次运行预期会失败 — 因为还没打过 :prod tag."""
    client = Client()
    try:
        prompt = client.prompts.get(prompt_identifier=PROMPT_NAME, tag="prod")
        print(f"成功拉取 :prod tag (version={prompt.id})")
    except Exception:
        print("没有 :prod tag — 这是首次运行的预期行为. 到 UI > Prompts 给某个 version 打 'prod' tag 后, 这里就能拉到.")


if __name__ == "__main__":
    push_initial_prompt()
    pull_and_use_prompt()
    pull_by_tag()
