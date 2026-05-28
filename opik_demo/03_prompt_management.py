"""Opik — Prompt 版本管理.

核心 API:
    p = opik.Prompt(name=..., prompt=..., metadata=...)
    # 构造时自动创建 / 新增版本, 不会报已存在
    p.format(var1=..., var2=...)  -> 把 {{var}} 替换成实际值, 返回字符串

按 commit 拉历史版本:
    client = opik.Opik()
    p = client.get_prompt(name=..., commit="abc1234")
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import opik
from dotenv import load_dotenv

from common.sample_agent import build_llm

load_dotenv()

PROMPT_NAME = "cs-agent-system"


def push_initial_prompt():
    """Opik.Prompt() 构造时自动写入服务端, 内容相同则不会新增 commit."""
    prompt = opik.Prompt(
        name=PROMPT_NAME,
        prompt=(
            "你是一名 {{company}} 的客服助手。请用 {{tone}} 的语气, "
            "在 1-3 句话内回答用户的 {{category}} 类问题. 不要编造信息.\n\n"
            "用户问题: {{question}}"
        ),
        metadata={"owner": "ai-platform", "model": "gpt-4o-mini"},
    )
    print(f"已推送 prompt '{prompt.name}' (commit={prompt.commit})")


def pull_and_use_prompt():
    client = opik.Opik()
    prompt = client.get_prompt(name=PROMPT_NAME)        # 拉最新版
    rendered = prompt.format(
        company="示例电商",
        tone="亲切",
        category="退款",
        question="电子产品多久能退?",
    )
    llm = build_llm()
    answer = llm.invoke(rendered)
    print("答案:", answer.content)


def pull_specific_commit():
    client = opik.Opik()
    latest = client.get_prompt(name=PROMPT_NAME)
    # 演示按 commit 拉旧版 (这里拉自己, 仅作 API 示例)
    pinned = client.get_prompt(name=PROMPT_NAME, commit=latest.commit)
    print(f"按 commit={latest.commit} 拉取成功")


if __name__ == "__main__":
    push_initial_prompt()
    pull_and_use_prompt()
    pull_specific_commit()
