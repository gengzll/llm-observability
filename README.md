# LLM Agent 可观测平台选型对比

对 **LangSmith / Langfuse / Phoenix / Opik / MLflow** 五款主流 LLM 观测 + 评估平台做的实战对比仓库。

主 demo 基于**同一个 LangGraph 客服 Agent**（`common/sample_agent.py`），覆盖 Tracing / Evaluation / Prompt 管理 / Dataset 四类能力，方便横向比较 DX 和能力边界。**另外补充了两个「裸 OpenAI SDK + 手写 agent loop」的方案**（`phoenix_native_demo/` 和 `mlflow_demo/`），给不用 LangChain 的团队直接可用。

> 想直接「动手跑」？看 [RUNNING.md](RUNNING.md) —— 24 个 demo（5 家 × 4 类能力，含 native SDK 版）全跑通的实测命令清单，可直接复制粘贴，含 10+ 条踩坑亲测解决方案。

---

## 0. TL;DR — 一句话选型

| 场景                                                                | 推荐         |
| ------------------------------------------------------------------- | ------------ |
| 已用 LangChain/LangGraph，团队接受 SaaS，不在意厂商绑定             | **LangSmith** |
| 要自托管、要数据合规、要 OSS、希望 UI/DX 都现代                     | **Langfuse**  |
| 已有 OTel 栈（Grafana / Datadog / Tempo 等），希望厂商无关          | **Phoenix**   |
| 评估是第一优先级，要丰富内置 metric 库 + pytest CI                  | **Opik**      |
| **已用 MLflow / Databricks 生态，想 LLM + 传统 ML 一个 UI 全管**       | **MLflow**    |

---

## 1. 为什么需要 LLM 可观测平台

传统 APM（SkyWalking / Pinpoint / 阿里云 ARMS 等）是为**确定性的 RPC 调用**设计的，看到一个 LLM agent 系统会束手无策。LLM 应用相比传统服务有三个根本性的新难题，对应着新工具的必要性：

### 1.1 LLM Agent 系统的三个新难题

**① 不确定性输出**：同样的输入，模型每次输出可能不同。无法用传统单元测试覆盖，必须有「评估集 + 自动评分」的 benchmark 体系才能判断一次代码改动是变好了还是变差了。

**② 调用链复杂**：一个 agent 一次响应可能涉及 N 次 LLM 调用、M 次 Tool 调用、状态机分支跳转。传统 trace 工具只能看到 HTTP 调用，看不到 prompt 内容、token 消耗、模型名、tool 参数这些 LLM 语义字段。

**③ Prompt 是核心资产**：prompt 改一个字效果可能天差地别，必须像代码一样版本化；但调 prompt 的人往往是 PM / 产品经理而不是工程师，需要 UI 而不是 git。

### 1.2 这四类能力对应解决了什么

| 能力              | 没有它会怎样                                            | 有了它能做到                                             |
| ----------------- | ------------------------------------------------------ | -------------------------------------------------------- |
| **Tracing**       | 用户反馈"答案不对"，工程师无从下手调查                  | 一秒还原现场：完整 LLM/Tool 调用链 + 各层输入输出 + token/cost |
| **Evaluation**    | 改了 prompt 不敢上线（不知道是变好还是变坏）             | 跑一遍评估集对比基线分数；CI 里自动 gate                  |
| **Prompt 管理**   | prompt 散落在代码里；PM 改要发版；改坏了不知道是哪版    | UI 编辑 → 版本化 → 灰度 → 一键回滚；trace 关联具体 prompt 版本 |
| **Dataset 管理**  | 评估集靠几条 print，没法系统迭代                         | 生产 trace → 一键加入评估集 → 人工标注 → 形成数据飞轮     |

简单说：**Tracing 解决"出了问题怎么查"，Evaluation 解决"敢不敢改"，Prompt 管理解决"谁能改、怎么回滚"，Dataset 解决"评估集从哪来"**。少哪一个，整个 LLM 系统就少一条腿。

---

## 2. 技术背景：OpenTelemetry 与 OpenInference

这一章只是为了讲清楚 4 个框架对比里反复出现的「OTel」「OpenInference」是什么。**它讲的是行业通用标准，不是本项目的架构**（本项目架构见第 3 章）。

如果贵公司已经有可观测基建，理解这一节会直接影响选型权重。

### 2.1 OpenTelemetry (OTel)

CNCF 下的可观测性事实标准，统一了 Traces / Metrics / Logs 的协议（OTLP）和 SDK。**核心理念是「埋点一次，后端随便换」**，让团队不被任何观测厂商绑定。

通用 OTel 栈（**示意图，与本项目无关，仅用于理解概念**）：

```
  业务应用 (任何语言)
      │  OTel SDK 埋点, 走 OTLP 协议
      ▼
  OTel Collector  ───► Tempo / Jaeger     ───► Trace 查询
                  ├──► Prometheus / Mimir ───► Metrics
                  ├──► Loki / Elastic     ───► Logs
                  └──► Grafana 等         ───► 统一可视化
```

怎么判断贵公司**到底有没有** OTel 栈？看微服务的 trace/metrics/logs 是用什么看的：

- **OTel 兼容**：Grafana 系（Tempo + Loki + Mimir）、Datadog、Honeycomb、Dynatrace、New Relic、SigNoz、阿里云 ARMS、腾讯云 APM、华为云 APM
- **半兼容**：SkyWalking（自己有协议，但有 OTel bridge）、Jaeger（原生 OTLP）
- **没有**：只用日志 + 控制台 print

### 2.2 OpenInference

**OTel 在 LLM 场景的语义约定**（Semantic Conventions），由 Arize 主导维护，目前是 LLM trace 的事实标准。

OTel 本身只规定通用 trace 协议，没说 LLM 调用要记哪些字段。OpenInference 补足这层，规定 span 上要带 `llm.model_name` / `llm.prompts` / `llm.token_count.total` / `tool.name` / `retrieval.documents` 这些约定字段，让不同框架埋的 LLM trace 能被同一个后端统一解析。

### 2.3 四个框架的 OTel 兼容性

| 框架      | trace 协议                    | 能否复用已有 OTel 栈                                       |
| --------- | ----------------------------- | --------------------------------------------------------- |
| LangSmith | 私有                          | 否 — trace 只能进 LangSmith 自家后端                       |
| Langfuse  | OTel (v3+ SDK)                | 是 — 可双发：Langfuse + Tempo/Grafana                     |
| Phoenix   | **OTel + OpenInference 原生** | 是 — trace 是标准 OTLP，直接进 Grafana/Jaeger/Honeycomb   |
| Opik      | 私有                          | 否 — 需要独立维护一套观测后端                              |
| MLflow    | 私有 + OTel exporter (v3+)    | 部分 — 需配 OTel exporter，主要走 mlflow 自家协议           |

### 2.4 这点对选型的影响

- **已有 OTel 栈** → 强烈倾向 Phoenix 或 Langfuse；LLM trace 能和微服务 trace 在同一 UI 串起来端到端排障，运维成本接近 0
- **完全没有 OTel 基建** → 这条不构成差异，看其他维度
- **未来打算上 OTel** → Phoenix / Langfuse 是「面向未来」的安全选择

---

## 3. 本项目架构与仓库结构

### 3.1 本项目实际架构

```
                       ┌──────────────────────────────────────┐
                       │   common/sample_agent.py             │
                       │   LangGraph StateGraph (5 demo 共用) │
                       │                                      │
                       │   ┌─────┐    ┌──────┐    ┌─────┐    │
                       │   │ LLM │──→ │ Tool │──→ │ LLM │... │
                       │   └─────┘    └──────┘    └─────┘    │
                       └──┬────────┬────────┬────────┬────────┬──┘
                          │        │        │        │        │
       env vars (无侵入)   CallbackHandler  OTel auto-  OpikTracer  langchain.autolog()
                          │   (1 行)   instrument  (1 行)     (1 行)
                          ▼        ▼        ▼        ▼        ▼
                 ┌────────────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐
                 │ LangSmith  │ │Langfuse│ │Phoenix│ │ Opik  │ │ MLflow│
                 │ SaaS only  │ │ :3000 │ │ :6006 │ │ :5173 │ │ :5000 │
                 │  (云端)    │ │(docker)│ │(docker)│ │(docker)│ │(server)│
                 └────────────┘ └───────┘ └───────┘ └───────┘ └───────┘

   另外两个「不用 LangChain」的路径（裸 OpenAI SDK + 手写 loop）:
        phoenix_native_demo/  →  Phoenix (launch_app 内嵌, no docker)
        mlflow_demo/          →  MLflow  (agent_native.py + @mlflow.trace)
```

**设计原则**：5 家共用同一个 LangGraph agent 和同一份评估集（`common/sample_dataset.py`），保证 demo 跑出的 trace、评分、cost 可以直接横向对比，差异只来自框架本身而非业务代码。另外的 `phoenix_native_demo/` 和 `mlflow_demo/` 覆盖「不用 LangChain 的团队」，用裸 OpenAI SDK 手写 agent loop。

### 3.2 仓库目录

```
llm-observability/
├── README.md                       ← 本文件（选型对比）
├── RUNNING.md                       ← 实操运行手册（24 个 demo 跑通版）
├── .env.example                    ← 所有 env 变量
├── requirements.txt                ← 合集装齐
├── common/
│   ├── sample_agent.py             ← LangGraph 客服 Agent (统一基线)
│   └── sample_dataset.py           ← 评估集 (统一基线)
├── langsmith_demo/                 ← SaaS only, 无 docker-compose
│   ├── 01_tracing.py / 02_evaluation.py / 03_prompt_management.py / 04_dataset.py
│   └── README.md
├── langfuse_demo/                  ← docker-compose 自托管
├── phoenix_demo/                   ← docker-compose 自托管
├── phoenix_native_demo/             ← 裸 OpenAI SDK + launch_app (不要 docker, 不要 LangChain)
├── opik_demo/                      ← 官方 .\opik.ps1 脚本自托管
└── mlflow_demo/                     ← mlflow server 一句话起, 含 native + langgraph 两版 agent
```

---

## 4. 快速开始

```powershell
# 0) Python 环境
python -m venv .venv
.venv\Scripts\Activate.ps1

# 1) 装依赖 (一次装齐, 也可只装单家)
pip install -r requirements.txt

# 2) 填环境变量
copy .env.example .env

# 3) 起本地服务 (LangSmith 跳过, 只用 SaaS)
cd langfuse_demo && docker compose up -d          # Langfuse  :3000
cd phoenix_demo  && docker compose up -d          # Phoenix   :6006
# Opik:  git clone https://github.com/comet-ml/opik && cd opik && .\opik.ps1   # :5173
# MLflow: python mlflow_demo/00_launch_mlflow.py                                # :5000

# 4) 跑某家的 4 个 demo (以 Langfuse 为例)
python langfuse_demo/01_tracing.py
python langfuse_demo/04_dataset.py
python langfuse_demo/02_evaluation.py
python langfuse_demo/03_prompt_management.py
```

> **详细的一步步实操**（每家怎么起 / 跑 / 看 / 关，含 10+ 条踩坑）见 [RUNNING.md](RUNNING.md)。

---

## 5. 核心能力对比（代码 + 表格）

按 4 类能力，每类先并排看**最精简的接入代码**，再看**能力对照表**。完整可跑版本在每家 `XX_demo/0X_*.py` 里。

### 5.1 Tracing — 让 agent 调用链可见

**LangSmith** — 0 行代码，只设环境变量
```python
# LANGSMITH_TRACING=true 后, LangGraph 自动上报
agent.invoke({"messages": [("user", q)]})
```

**Langfuse** — 1 行 callback
```python
from langfuse.langchain import CallbackHandler
agent.invoke({"messages": [...]}, config={"callbacks": [CallbackHandler()]})
```

**Phoenix** — 1 行 register
```python
from phoenix.otel import register
register(project_name="demo", auto_instrument=True)   # 全局一次
agent.invoke({"messages": [...]})
```

**Opik** — 1 行 callback（带 LangGraph 拓扑可视化）
```python
from opik.integrations.langchain import OpikTracer
tracer = OpikTracer(graph=agent.get_graph(xray=True))
agent.invoke({"messages": [...]}, config={"callbacks": [tracer]})
```

**MLflow** — 1 行 autolog（LangGraph 版）；或裸 SDK 用装饰器
```python
# LangGraph 版
import mlflow; mlflow.langchain.autolog()
agent.invoke({"messages": [...]})

# 裸 SDK 版
import mlflow; mlflow.openai.autolog()
@mlflow.trace(name="agent.run", span_type=mlflow.entities.SpanType.AGENT)
def run_agent(question): ...
```

| 维度              | LangSmith         | Langfuse           | Phoenix                 | Opik                       | MLflow                       |
| ----------------- | ----------------- | ------------------ | ----------------------- | -------------------------- | ---------------------------- |
| 接入代码量         | 0 行              | 1 行               | 1 行                    | 1 行                       | 1 行 (autolog)                |
| 嵌套 span 自动捕获 | 是                | 是                 | 是                      | 是                         | 是                            |
| Token / Cost      | 是                | 是                 | 是                      | 是                         | 是                            |
| LangGraph 拓扑图   | 是                | 部分               | 部分                    | **是 (xray 节点/边可视化)** | 部分 (LangChain autolog 展开) |
| 底层协议           | 私有              | OTel               | OTel + OpenInference     | 私有                       | 私有 + OTel exporter (v3+)   |

### 5.2 Evaluation — 跑数据集打分

**LangSmith** — `client.evaluate(target, data, evaluators)`
```python
client.evaluate(target_fn, data="dataset-name", evaluators=[my_eval], max_concurrency=4)
```

**Langfuse** — 遍历 `dataset.items` + `item.run()`
```python
for item in dataset.items:
    with item.run(run_name="exp-1") as span:
        out = agent_run(item.input)
        span.score_trace(name="correctness", value=judge(out, item.expected_output))
```

**Phoenix** — `client.experiments.run_experiment`
```python
client.experiments.run_experiment(dataset=ds, task=task_fn, evaluators=[eval_fn])
```

**Opik** — `evaluate(experiment_name, dataset, task, scoring_metrics)`
```python
from opik.evaluation import evaluate
evaluate(experiment_name="exp-1", dataset=ds, task=task_fn,
         scoring_metrics=[Hallucination(), CorrectnessMetric()])
```

**MLflow** — 手动 loop + `log_metric`（也支持高级 `mlflow.evaluate`）
```python
with mlflow.start_run(run_name="baseline"):
    for i, ex in enumerate(dataset):
        out = run_agent(ex["input"])
        mlflow.log_metric("correctness", judge(out, ex["expected"]), step=i)
```

| 维度              | LangSmith                  | Langfuse                | Phoenix                              | Opik                                                   | MLflow                                          |
| ----------------- | -------------------------- | ----------------------- | ------------------------------------ | ------------------------------------------------------ | ----------------------------------------------- |
| 内置 metric 库     | 配套包 `openevals`          | 较少，多需手写           | `phoenix.evals` (RAG/Embedding 强项)  | **最丰富**: Hallucination/G-Eval/AnswerRelevance/Moderation 开箱即用 | `mlflow.metrics.genai.*` (JSON mode 依赖, 国内网关不友好) |
| 自定义 metric     | 函数返回 dict                | 函数 + `score_trace`     | 函数 / `ClassificationEvaluator` 子类  | 继承 `BaseMetric` 类                                   | 手动 `log_metric` 或 `make_metric()`             |
| 并行执行           | `max_concurrency`           | 手动循环                 | 默认并行                              | 默认并行                                                | `mlflow.evaluate` 支持                          |
| pytest 集成        | 间接                        | 间接                     | 有 examples                          | **官方 `opik.integrations.pytest`**                    | 间接                                            |
| 生产 trace 自动评分| 是 (Online evaluator)       | 是 (Server-side rules)   | 部分                                  | 是 (Online rules)                                      | 需要自己拼                                       |
| 实验 side-by-side  | 是                          | 是                       | 是                                   | 是                                                    | **传统强项** (跨模型/参数对比 UI)                  |

### 5.3 Prompt 管理 — 版本化 + 协作

**LangSmith** — push LangChain 对象
```python
client.push_prompt("cs-system", object=ChatPromptTemplate.from_messages([...]))
prompt = client.pull_prompt("cs-system:prod")   # 按 tag 拉
```

**Langfuse** — Mustache 模板 + labels
```python
langfuse.create_prompt(name="cs-system", type="chat", prompt=[...], labels=["production"])
p = langfuse.get_prompt("cs-system")            # 默认拉 production label
```

**Phoenix** — provider-agnostic
```python
client.prompts.create(name="cs-system", version=PromptVersion([...], model_name="..."))
p = client.prompts.get(prompt_identifier="cs-system", tag="prod")
```

**Opik** — 构造即推送
```python
opik.Prompt(name="cs-system", prompt="...{{var}}...")   # 自动创建/版本化
p = client.get_prompt(name="cs-system", commit="abc123")
```

**MLflow** — `mlflow.genai.register_prompt` / `load_prompt`（3.14+ namespace）
```python
mlflow.genai.register_prompt(name="cs-system", template="...{{var}}...",
                              commit_message="v1", tags={"env": "dev"})
p = mlflow.genai.load_prompt("prompts:/cs-system@production")   # 按 alias
```

| 维度          | LangSmith           | Langfuse                              | Phoenix                       | Opik                  | MLflow                        |
| ------------- | ------------------- | ------------------------------------- | ----------------------------- | --------------------- | ----------------------------- |
| 模板语法       | LangChain `{var}`    | Mustache `{{var}}` (可转 LangChain)   | Mustache `{{var}}`             | Mustache `{{var}}`     | Mustache `{{var}}`             |
| 版本机制       | commit hash + tag    | version + labels (production/staging) | version + tag                 | commit hash           | version + alias               |
| UI 直接编辑    | 是                  | 是                                    | 是                             | 是                     | 是                             |
| Playground 试跑| 是                  | 是                                    | 是                             | 是                     | 是                             |
| trace 关联版本 | 是                  | 是 (`langfuse_prompt` metadata)        | 是                             | 是                     | 是                             |

### 5.4 Dataset — 评估集管理 + 数据飞轮

**LangSmith**
```python
ds = client.create_dataset("agent-eval-v1")
client.create_examples(dataset_id=ds.id, examples=[{"inputs":..., "outputs":...}])
```

**Langfuse**
```python
langfuse.create_dataset(name="agent-eval-v1")
langfuse.create_dataset_item(dataset_name="agent-eval-v1", input=..., expected_output=...)
```

**Phoenix**
```python
client.datasets.create_dataset(name="agent-eval-v1", inputs=[...], outputs=[...])
```

**Opik**
```python
ds = client.get_or_create_dataset(name="agent-eval-v1")
ds.insert(items=[{"input":..., "expected":...}])
```

**MLflow** — `mlflow.data.from_pandas` + 绑到 run
```python
dataset = mlflow.data.from_pandas(df, source="in-memory", name="agent-eval-v1")
with mlflow.start_run():
    mlflow.log_input(dataset, context="eval")   # dataset 主要绑到 run 而非独立
```

| 维度                  | LangSmith           | Langfuse             | Phoenix          | Opik              | MLflow                      |
| --------------------- | ------------------- | -------------------- | ---------------- | ----------------- | --------------------------- |
| 创建 API              | 两步 (dataset+examples) | 两步               | 一步              | 一步              | 一步 (`from_pandas`)          |
| Dataset 独立性         | 一等公民             | 一等公民              | 一等公民          | 一等公民           | **主要绑到 run** (Datasets 页较弱) |
| 从生产 trace 加数据   | 是 (UI 操作)         | 是 (UI 操作)         | 是 (UI 操作)      | 是 (UI 操作)      | 手动 (需自己写 pipeline)      |
| 标注 / 人工反馈队列    | 是                  | 是                   | 较弱              | 是                | 较弱                          |
| Dataset 版本化         | 是                  | 通过 metadata        | 是                | 是                | 通过 run tag                  |

---

## 6. 综合维度对比

### 6.1 项目基本面

| 维度           | LangSmith         | Langfuse              | Phoenix                       | Opik              | MLflow             |
| -------------- | ----------------- | --------------------- | ----------------------------- | ----------------- | ------------------ |
| 官网           | [smith.langchain.com](https://smith.langchain.com/) | [langfuse.com](https://langfuse.com/) | [phoenix.arize.com](https://phoenix.arize.com/) | [comet.com/opik](https://www.comet.com/site/products/opik/) | [mlflow.org](https://mlflow.org/) |
| GitHub 仓库 (star ★) | [langchain-ai/langsmith-sdk](https://github.com/langchain-ai/langsmith-sdk) — **907 ★**（仅 SDK，平台闭源） | [langfuse/langfuse](https://github.com/langfuse/langfuse) — **28.2k ★** | [Arize-ai/phoenix](https://github.com/Arize-ai/phoenix) — **9.9k ★** | [comet-ml/opik](https://github.com/comet-ml/opik) — **19.4k ★** | [mlflow/mlflow](https://github.com/mlflow/mlflow) — **27k ★** |
| 开发方         | LangChain Inc.    | Langfuse GmbH (DE)    | Arize AI                      | Comet ML          | Databricks (LF AI) |
| 开源协议       | 闭源 (SaaS only)  | MIT (主仓) + EE       | Elastic v2 (OSS-friendly)     | Apache 2.0        | Apache 2.0         |
| 自托管         | 仅企业版          | docker-compose 一键   | 单容器一键 (最轻)             | 官方安装脚本      | `mlflow server` 一行 |
| 自托管所需服务  | 无                | Postgres+ClickHouse+Redis+MinIO | SQLite (默认) / Postgres | MySQL+ClickHouse+Redis+前后端 | SQLite (默认) / Postgres / MySQL |
| 默认 UI 端口   | -                 | 3000                  | 6006                          | 5173              | 5000               |
| 主要付费形态   | SaaS 订阅         | Cloud + EE license    | Arize AX 商用版               | Comet Cloud       | Databricks Cloud    |
| 与 OTel 生态   | 不兼容            | v3+ 原生 OTel         | 完全 OTel (OpenInference)      | 不兼容            | 部分 (v3+ exporter) |

> Star 数为 2026-05-29 / 2026-07-12 GitHub API 实时查询。LangSmith 平台本身闭源，列出的仓库是其 Python SDK；其他 4 家都是真实的平台主仓。MLflow 27k ★ 是 5 家里最高的，但它是**通用 ML 平台**（比其他 4 家早 5 年，历史累积），LLM tracing 只是它一部分能力。社区热度对比时，需扣除"完整平台 vs 单 SDK / LLM-only 平台"这一差异。

### 6.2 各家优缺点

#### LangSmith
- **优势**：和 LangGraph 同源，0 代码接入；评估/Prompt/Dataset 闭环最早做出来，UI 最成熟；文档质量最高
- **劣势**：闭源 + SaaS only；自托管要买企业版（价格不公开）；协议私有数据导不出；国内访问要走代理；seat × trace 量双重计费规模大了贵
- **适合**：纯云、中小规模、已 all-in LangChain 的团队；快速验证期项目

#### Langfuse
- **优势**：MIT 开源 + 完整功能可自托管（个别 SSO/RBAC 是 EE 协议）；v3 SDK 基于 OTel；UI/UX 最现代；中文社区活跃
- **劣势**：自托管栈较重（8+ GB 内存起步）；评估能力 4 家里最薄（无内置 metric 库）；LangGraph 拓扑可视化弱
- **适合**：要数据自主、合规要求高、把可观测当**长期基建**的团队

#### Arize Phoenix
- **优势**：唯一原生 OTel；自托管最轻；`phoenix.evals` 在 RAG/Embedding 评估上有传统优势
- **劣势**：Prompt 管理是后补功能；标注队列弱；文档分散在多处难找；企业级权限要走 Arize AX 商用版
- **适合**：已有 OTel 栈、做 RAG/Embedding 调优、要厂商无关的团队

#### Opik
- **优势**：内置 LLM-as-judge metric 最丰富；pytest 集成最佳；LangGraph 有 xray 拓扑可视化；Comet ML 同源的实验对比经验
- **劣势**：协议私有；UI 最年轻，breaking change 较多；自托管栈较重；国内访问 Comet 镜像偶尔慢
- **适合**：把**离线评估和回归测试**当核心需求的团队（RAG、生产前必跑 eval 的项目）

#### MLflow
- **优势**：**5 家里生态最成熟**（27k ★，5 年历史，Databricks + Linux Foundation AI 支持）；Apache 2.0 完全开源；同一 UI 里 LLM tracing + 传统 sklearn / xgboost 一起管；`mlflow server` 一句话起（比 Langfuse / Opik 都轻）；prompt registry 3.14 支持完整的 version + alias
- **劣势**：**LLM-specific 视图不如专用平台精细**（token / cost / tool call 显示较通用）；trace 是 3.x 引入的新能力（相对 tracking 的 5 年成熟度还在追赶）；Windows 上 `mlflow evaluate` 的 judge 依赖 OpenAI JSON mode，智谱等国内网关不友好（需手写 metric）；协议私有（3.x 有 OTel exporter 但需要额外配）
- **适合**：Databricks 生态 / 已经用 MLflow 管 ML 的团队 / ML + LLM 混合项目 / 不想额外养专用 LLM 观测平台的团队

### 6.3 决策矩阵（按贵团队权重重新打分）

| 维度（权重）              | LangSmith | Langfuse | Phoenix | Opik | MLflow |
| ------------------------- | --------- | -------- | ------- | ---- | ------ |
| 数据可自托管 (×3)         | 1         | 5        | 5       | 5    | 5      |
| LangGraph 接入丝滑度 (×3) | 5         | 4        | 4       | 4    | 4      |
| 评估能力 (×2)             | 4         | 3        | 4       | 5    | 4      |
| Prompt 管理 (×2)          | 5         | 5        | 4       | 4    | 4      |
| OTel 生态兼容 (×1)        | 1         | 4        | 5       | 1    | 3      |
| 运维成本 (×1, 越低越高分) | 5         | 3        | 5       | 3    | 4      |
| 长期开源/中立 (×1)        | 1         | 5        | 5       | 5    | 5      |
| **加权总分（示例）**      | **38**    | **48**   | **52**  | **48** | **51** |

数字是示例，**请按你们公司实际情况重新打分**——比如「合规」「国内网络」这些维度可以加上，权重也按业务重要度调。

---

## 7. 迁移成本 + 踩坑 + 评估方法论

### 7.1 迁移成本估算

| 现状 → 目标             | 成本                                       |
| ----------------------- | ----------------------------------------- |
| 裸 LangChain → LangSmith | 极低 (改环境变量)                          |
| 裸 LangChain → MLflow   | 极低 (`mlflow.langchain.autolog()` 一行)   |
| LangSmith ↔ Langfuse    | 中 (改 callback, prompt 括号 `{}` ↔ `{{}}`)|
| LangSmith ↔ Phoenix     | 中 (改 register, prompt 改 mustache, eval API 重写) |
| LangSmith ↔ Opik        | 中 (改 callback, eval metric 重写)         |
| LangSmith ↔ MLflow      | 中 (autolog 一行, eval 重写, prompt 改 mustache) |
| Langfuse ↔ Phoenix      | 低 (都是 OTel, trace 可双发并存)            |
| Phoenix → 其他          | 低 (trace 是标准 OTLP, 可同时保留)          |
| MLflow → LLM-native 平台 | 中 (LangChain autolog 通用, 但 evaluation / prompt API 是 MLflow 私有需重写) |

### 7.2 团队最常踩的坑

1. **LangSmith 默认上报全部 input/output** 含敏感字段。生产前必须配 `LANGSMITH_HIDE_INPUTS` / `OUTPUTS` 或做字段脱敏。
2. **Langfuse v3 docker-compose 比 v2 复杂得多**（多了 ClickHouse + MinIO）。v2 升级需要走 migration script。
3. **Phoenix `register()` 只能调一次**。notebook 反复 import 会触发 OTel provider already set 警告。
4. **Opik 国内访问 Comet 镜像偶尔慢**，建议提前 pull / 配国内镜像源。
5. **secret key 永远不要在浏览器侧暴露**——5 家都一样。
6. **MLflow `--default-artifact-root` 必须带 URI scheme**（Windows 特别容易踩）：裸 `C:\...` 路径会导致 trace 上报失败（`Could not find a registered artifact repository`）。用 `mlflow-artifacts:/` + `--serve-artifacts` 让 server 代理最稳。
7. **MLflow 3.14+ 的 prompt API 迁移到 `mlflow.genai` namespace**（`mlflow.genai.register_prompt` / `.load_prompt`）。老 API 现在有 `FutureWarning`，未来会移除。

### 7.3 评估方法论（与选哪家无关）

- **dataset 是核心资产**，应该和代码一起 git 管理（4 家都支持导出 JSON）
- **eval 必须自动化**：作为 CI step（Opik 的 pytest 集成最直接，其他 3 家也都能在 pipeline 里跑 evaluate）
- **LLM-as-judge 不可全信**：judge 自身的偏差要小批量人工 spot-check
- **生产 trace 反哺数据集**：设触发器，低分 / 用户负反馈的 trace 自动加入待标注队列，形成数据飞轮

---

## 8. 进一步阅读

- LangSmith: https://docs.langchain.com/langsmith
- Langfuse: https://langfuse.com/docs
- Arize Phoenix: https://arize.com/docs/phoenix
- Opik: https://www.comet.com/docs/opik
- MLflow: https://mlflow.org/docs/latest/index.html
- MLflow LLM Tracing (v3+ 新能力): https://mlflow.org/docs/latest/llms/tracing/index.html
- OpenInference SemConv (Phoenix 底座): https://github.com/Arize-ai/openinference
