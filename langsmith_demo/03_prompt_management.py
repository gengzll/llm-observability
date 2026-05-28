"""LangSmith — Prompt 版本管理.

核心 API:
    client.push_prompt(name, object=...)  -> 创建 / 更新 prompt, 自动版本化
    client.pull_prompt(name)              -> 拉取最新版 (或指定 commit hash)
    client.pull_prompt(f"{name}:{tag}")   -> 按 tag 拉取 (e.g. ':prod')

典型工作流:
    1. 工程师在代码里 push 初版 prompt
    2. PM / 产品经理在 LangSmith UI 上直接改 prompt, 标记 ':prod'
    3. 应用代码用 pull_prompt(':prod') 加载, 无需重新发版
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langsmith import Client

from common.sample_agent import build_llm

load_dotenv()

PROMPT_NAME = "cs-agent-system"


def push_initial_prompt():
    """把代码里维护的初版 system prompt 推到 LangSmith."""
    client = Client()
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是一名 {company} 的客服助手。请用 {tone} 的语气, "
                "在 1-3 句话内回答用户的 {category} 类问题. 不要编造信息.",
            ),
            ("user", "{question}"),
        ]
    )
    url = client.push_prompt(PROMPT_NAME, object=prompt)
    print(f"已推送 prompt {PROMPT_NAME}: {url}")


def pull_and_use_prompt():
    """从 LangSmith 拉最新 prompt, 渲染后调用 LLM."""
    client = Client()
    prompt: ChatPromptTemplate = client.pull_prompt(PROMPT_NAME)  # 拿 LangChain 对象
    chain = prompt | build_llm()
    answer = chain.invoke(
        {
            "company": "示例电商",
            "tone": "亲切",
            "category": "退款",
            "question": "电子产品多久能退?",
        }
    )
    print("答案:", answer.content)


def pull_specific_version():
    """按版本 / tag 拉取 (生产环境建议用 tag 锁版本)."""
    client = Client()
    # 按 commit hash:
    # prompt = client.pull_prompt(f"{PROMPT_NAME}:abc123ef")
    # 按 tag (需在 UI 里给 commit 打 tag):
    try:
        prompt = client.pull_prompt(f"{PROMPT_NAME}:prod")
        print("成功拉取 :prod tag")
        return prompt
    except Exception as e:
        print(f"还没有 :prod tag (这是正常的, 首次运行时还没打 tag): {e}")


if __name__ == "__main__":
    push_initial_prompt()
    pull_and_use_prompt()
    pull_specific_version()
