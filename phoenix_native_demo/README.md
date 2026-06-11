# Phoenix native demo — 不用 docker, 不用 LangChain

这个 demo 给「**直接调 OpenAI SDK / OpenAI 兼容网关，没用 LangChain/LangGraph**」的真实生产场景准备。

特点：

- **不用 docker** —— `phoenix.launch_app()` 内嵌启动 Phoenix server，SQLite 落盘
- **不用 LangChain** —— agent 是裸 `client.chat.completions.create` + 手写 loop
- **统一接口** —— 走 `OPENAI_BASE_URL`，OpenAI / 智谱 / DeepSeek / 火山 / 本地 vLLM 都能跑
- **完整 trace** —— 三层 span：`agent.run`（手埋）→ LLM（自动 instrument）→ `tool.*`（手埋）

---

## 文件结构

```
phoenix_native_demo/
├── README.md                (本文件)
├── requirements.txt         (依赖, 比 phoenix_demo 多了 instrumentation-openai)
├── agent.py                 (裸 OpenAI SDK + 手写 agent loop, 含手埋 span)
├── 00_launch_phoenix.py     (终端 1 跑, 长跑保持 server)
├── 01_tracing.py            (基础 + 带 metadata + 多步 tool)
├── 04_dataset.py            (上传评估集, 共用 common/sample_dataset.py)
├── 02_evaluation.py         (跑评估)
└── 03_prompt_management.py  (推/拉/渲染 prompt → 直接喂 OpenAI SDK)
```

---

## 0. 装依赖

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r phoenix_native_demo\requirements.txt
```

如果之前在合集 venv 里装过 `arize-phoenix*`，这里只需要补一个：

```powershell
pip install openinference-instrumentation-openai
```

---

## 1. 启动 Phoenix server（**终端 1，保持运行**）

```powershell
python phoenix_native_demo\00_launch_phoenix.py
```

输出：
```
  Phoenix server  : http://localhost:6006/
  数据落盘       : ~/.phoenix/
  保持此窗口运行 -- 按 Ctrl+C 关闭 server.
```

**端口冲突**：如果之前 docker 起过 Phoenix，先停掉：
```powershell
docker compose -f phoenix_demo\docker-compose.yml stop
```

---

## 2. 跑 demo（**终端 2**）

```powershell
$env:PYTHONIOENCODING="utf-8"; chcp 65001 | Out-Null; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
.\.venv\Scripts\Activate.ps1

python phoenix_native_demo\01_tracing.py
python phoenix_native_demo\04_dataset.py
python phoenix_native_demo\02_evaluation.py
python phoenix_native_demo\03_prompt_management.py
```

打开 http://localhost:6006 看：
- **Projects > native-demo** —— trace（含 `agent.run` 根 span，下挂 LLM / tool span）
- **Datasets** —— 上传的 7 条
- **Datasets > agent-cs-eval-v1 > Experiments > native-baseline-...** —— 评估
- **Prompts > cs-agent-native-system** —— prompt 版本

---

## 关键技术点

### A. Phoenix server 的两种部署对比

| 方式            | 命令                                      | 数据落盘            | 适用                       |
| --------------- | ----------------------------------------- | ------------------- | -------------------------- |
| docker          | `docker compose ... up -d`                | docker volume       | 团队共享 / 长期生产         |
| **launch_app**  | **`px.launch_app()` 内嵌 Python 进程**    | **`~/.phoenix/`**   | **个人调试 / CI / 演示**    |

`launch_app` 用 SQLite，单进程，无配置。它与启动它的 Python 进程绑定 —— 进程退出 server 也退。所以本 demo 用 `00_launch_phoenix.py` 长期保留进程。

### B. OpenAI SDK 自动 instrument 原理

```python
from openinference.instrumentation.openai import OpenAIInstrumentor
OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
```

执行后，包内 monkey-patch 了 `openai.OpenAI.chat.completions.create` 等方法，每次调用自动产生 span，含：

- `llm.model_name`
- `llm.prompts` / `llm.invocation_parameters`
- `llm.token_count.{prompt, completion, total}`
- `output.value`
- tool_calls 的结构化记录

这些字段是 **OpenInference Semantic Conventions** 的标准字段，Phoenix UI 据此渲染 LLM 调用的特有视图。

### C. 手动埋 tool span

`agent.py` 里：

```python
from opentelemetry import trace
_tracer = trace.get_tracer("phoenix_native_demo.agent")

with _tracer.start_as_current_span("agent.run") as agent_span:
    agent_span.set_attribute("input.value", question)
    # agent loop, LLM 调用是 OpenAIInstrumentor 自动产生的 span
    with _tracer.start_as_current_span(f"tool.{name}") as tool_span:
        tool_span.set_attribute("tool.name", name)
        tool_span.set_attribute("tool.arguments", args)
        result = TOOLS_REGISTRY[name](**parsed_args)
        tool_span.set_attribute("tool.result", result)
    agent_span.set_attribute("output.value", final_answer)
```

Phoenix UI 上能看到 `agent.run` 是根 span，下面挂着 LLM spans 和 tool spans，嵌套结构清晰。

### D. 切换 LLM 网关 —— 只改 `.env`

```env
# 默认: 智谱
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
OPENAI_MODEL=glm-4-flash

# 改为 DeepSeek:
# OPENAI_BASE_URL=https://api.deepseek.com/v1
# OPENAI_MODEL=deepseek-chat

# 改为本地 vLLM:
# OPENAI_BASE_URL=http://localhost:8000/v1
# OPENAI_MODEL=your-model-name

# 改为 OpenAI 官方:
# OPENAI_BASE_URL=https://api.openai.com/v1
# OPENAI_MODEL=gpt-4o-mini
```

`agent.py` 代码不动，trace 字段也不动。

---

## 和 `phoenix_demo/` 的区别

| 维度              | `phoenix_demo/`                                | `phoenix_native_demo/` (本目录)         |
| ----------------- | ---------------------------------------------- | --------------------------------------- |
| 启动方式          | docker compose                                 | `px.launch_app()` 内嵌进程              |
| Agent 框架        | LangGraph StateGraph                           | 裸 OpenAI SDK + 手写 loop               |
| LLM instrument    | `LangChainInstrumentor` (auto_instrument=True) | `OpenAIInstrumentor` 手动 instrument    |
| Tool span         | LangGraph 自动产生                             | OpenTelemetry `start_span` 手埋          |
| Prompt 模板渲染   | 经过 LangChain `ChatPromptTemplate` 适配       | `prompt.format()` 直出 OpenAI messages  |
| 依赖体积          | 重（含 langchain / langgraph 全家桶）           | 轻（只要 openai + phoenix + openinference） |
| 学习曲线          | 中（要懂 LangGraph）                           | 低（只要懂 OpenAI SDK）                   |

业务场景在选型时，看你团队 agent 实现是基于框架还是裸 SDK，直接选对应的 demo 路径。

---

## 已知警告（无害）

- `Overriding of current TracerProvider is not allowed` —— `01_tracing.py` 和 `02_evaluation.py` 都调了 `register()`，依次跑会出现，但不影响 trace
- `prompt :prod tag not found` —— 首次运行 `03_prompt_management.py` 预期，demo 注释里说明
