# LangSmith Demo

LangChain 官方观测平台。**仅云端 SaaS**（自托管需企业版 license，社区无开源镜像）。

## 准备

1. 注册 https://smith.langchain.com/ ，拿到 API Key。
2. 复制 `../.env.example` 为 `../.env`，填写：
   ```
   LANGSMITH_TRACING=true
   LANGSMITH_API_KEY=lsv2_pt_xxx
   LANGSMITH_PROJECT=llm-obs-demo
   OPENAI_API_KEY=sk-xxx
   ```
3. 安装依赖：
   ```powershell
   pip install -r requirements.txt
   ```

## 跑 demo

```powershell
# 1) 链路追踪 (LangGraph 全自动上报)
python 01_tracing.py

# 2) 评估 — 先建好 dataset, 再跑 eval
python 04_dataset.py
python 02_evaluation.py

# 3) Prompt 版本管理
python 03_prompt_management.py
```

跑完到 https://smith.langchain.com/ 在 `llm-obs-demo` project 下查看。

## 关键 API 速查

| 能力        | API                                                         |
| ----------- | ----------------------------------------------------------- |
| 自动 trace  | 只设 `LANGSMITH_TRACING=true` 环境变量, 0 代码              |
| 手动 trace  | `@traceable(run_type="chain", name="...")` 装饰任意函数      |
| 评估        | `client.evaluate(target, data, evaluators, ...)`            |
| 创建 dataset| `client.create_dataset(name)` + `client.create_examples(...)`|
| Prompt 推送 | `client.push_prompt(name, object=ChatPromptTemplate(...))`  |
| Prompt 拉取 | `client.pull_prompt(f"{name}:{tag}")`                       |

## 集成 LangGraph 的姿势

**最丝滑**：只要 `LANGSMITH_TRACING=true`，LangGraph 的每个 node、每次 LLM 调用、每个 tool 调用都会自动变成嵌套 span 上报，无需写任何 callback。这是 LangSmith 相对其他三家最大的优势。
