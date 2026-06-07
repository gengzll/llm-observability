"""Langfuse — Prompt 版本管理.

核心 API:
    langfuse.create_prompt(name, prompt=..., labels=[...])  # 创建/新增版本
    langfuse.get_prompt(name)                                # 拉取最新生产版
    langfuse.get_prompt(name, label="staging")               # 按 label 拉
    prompt.get_langchain_prompt()                            # 转 LangChain 模板

Langfuse 的 prompt 是 {{var}} 格式 (mustache), 转 LangChain 时会自动变成 {var}.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langfuse import get_client

from common.sample_agent import build_llm

load_dotenv()

PROMPT_NAME = "cs-agent-system"


def push_initial_prompt():
    langfuse = get_client()
    prompt = langfuse.create_prompt(
        name=PROMPT_NAME,
        type="chat",
        prompt=[
            {
                "role": "system",
                "content": (
                    "你是一名 {{company}} 的客服助手。请用 {{tone}} 的语气, "
                    "在 1-3 句话内回答用户的 {{category}} 类问题. 不要编造信息."
                ),
            },
            {"role": "user", "content": "{{question}}"},
        ],
        labels=["production"],   # 标记成生产版本, get_prompt 默认拉这个
        config={"model": "gpt-4o-mini", "temperature": 0.0},
    )
    print(f"已推送 prompt '{prompt.name}' v{prompt.version} (labels={prompt.labels})")


def pull_and_use_prompt():
    langfuse = get_client()
    fetched = langfuse.get_prompt(PROMPT_NAME)              # 默认 label=production
    # 转 LangChain 格式: {{var}} -> {var}
    chat_prompt = ChatPromptTemplate.from_messages(fetched.get_langchain_prompt())

    # 关键: chain.invoke 时绑定 langfuse_prompt, trace 里就能看到「这次调用用的是哪个 prompt 版本」
    chain = chat_prompt | build_llm()
    answer = chain.invoke(
        {
            "company": "示例电商",
            "tone": "亲切",
            "category": "退款",
            "question": "电子产品多久能退?",
        },
        config={"metadata": {"langfuse_prompt": fetched}},
    )
    print("答案:", answer.content)


def pull_specific_label():
    """演示按 label 拉取 prompt. 首次运行预期没 'staging' label, 会失败."""
    # Langfuse SDK 内部会向 stderr 打 warning ("not found during refresh, evicting from cache"),
    # 临时把 SDK logger 调高级别以抑制干扰输出.
    import logging
    lf_logger = logging.getLogger("langfuse")
    old_level = lf_logger.level
    lf_logger.setLevel(logging.ERROR)
    try:
        langfuse = get_client()
        prompt = langfuse.get_prompt(PROMPT_NAME, label="staging")
        print(f"成功拉取 staging label v{prompt.version}")
    except Exception:
        print("没有 'staging' label — 这是首次运行的预期行为. 到 UI > Prompts 给某个版本添加 'staging' label 后, 这里就能拉到.")
    finally:
        lf_logger.setLevel(old_level)


if __name__ == "__main__":
    push_initial_prompt()
    pull_and_use_prompt()
    pull_specific_label()
    get_client().flush()
