# LLM Agent 可观测平台选型对比

对 **LangSmith / Langfuse / Phoenix / Opik** 四款主流 LLM 观测 + 评估平台做的实战对比仓库。

所有 demo 基于**同一个 LangGraph 客服 Agent**（`common/sample_agent.py`），覆盖 Tracing / Evaluation / Prompt 管理 / Dataset 四类能力，方便横向比较 DX 和能力边界。

---

## 0. TL;DR — 一句话选型

| 场景                                                                | 推荐         |
| ------------------------------------------------------------------- | ------------ |
| 已用 LangChain/LangGraph，团队接受 SaaS，不在意厂商绑定             | **LangSmith** |
| 要自托管、要数据合规、要 OSS、希望 UI/DX 都现代                     | **Langfuse**  |
| 已有 OTel 栈（Grafana / Datadog / Tempo 等），希望厂商无关          | **Phoenix**   |
| 评估是第一优先级，要丰富内置 metric 库 + pytest CI                  | **Opik**      |

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
                   │   LangGraph StateGraph (4 demo 共用) │
                   │                                      │
                   │   ┌─────┐    ┌──────┐    ┌─────┐    │
                   │   │ LLM │──→ │ Tool │──→ │ LLM │... │
                   │   └─────┘    └──────┘    └─────┘    │
                   └──┬──────────┬──────────┬─────────┬──┘
                      │          │          │         │
        env vars (无侵入)   CallbackHandler  OTel auto-  OpikTracer
                      │      (1 行)      instrument  (1 行)
                      │          │          │         │
                      ▼          ▼          ▼         ▼
              ┌────────────┐ ┌────────┐ ┌────────┐ ┌────────┐
              │ LangSmith  │ │Langfuse│ │Phoenix │ │ Opik   │
              │ SaaS only  │ │ :3000  │ │ :6006  │ │ :5173  │
              │  (云端)    │ │(docker)│ │(docker)│ │(docker)│
              └────────────┘ └────────┘ └────────┘ └────────┘
```

**设计原则**：4 家共用同一个 LangGraph agent 和同一份评估集（`common/sample_dataset.py`），保证 demo 跑出的 trace、评分、cost 可以直接横向对比，差异只来自框架本身而非业务代码。

### 3.2 仓库目录

```
llm-observability/
├── README.md                       ← 本文件
├── .env.example                    ← 4 个框架所有 env 变量
├── requirements.txt                ← 合集装齐
├── common/
│   ├── sample_agent.py             ← LangGraph 客服 Agent (统一基线)
│   └── sample_dataset.py           ← 评估集 (统一基线)
├── langsmith_demo/                 ← SaaS only, 无 docker-compose
│   ├── 01_tracing.py / 02_evaluation.py / 03_prompt_management.py / 04_dataset.py
│   └── README.md
├── langfuse_demo/                  ← docker-compose 自托管
├── phoenix_demo/                   ← docker-compose 自托管
└── opik_demo/                      ← 官方 .\opik.ps1 脚本自托管
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

# 3) 起本地服务 (LangSmith 跳过)
cd langfuse_demo && docker compose up -d
cd phoenix_demo  && docker compose up -d
# Opik: git clone https://github.com/comet-ml/opik && cd opik && .\opik.ps1

# 4) 跑某家的 4 个 demo
python langfuse_demo/01_tracing.py
python langfuse_demo/04_dataset.py
python langfuse_demo/02_evaluation.py
python langfuse_demo/03_prompt_management.py
```

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

| 维度              | LangSmith         | Langfuse           | Phoenix                 | Opik                       |
| ----------------- | ----------------- | ------------------ | ----------------------- | -------------------------- |
| 接入代码量         | 0 行              | 1 行               | 1 行                    | 1 行                       |
| 嵌套 span 自动捕获 | 是                | 是                 | 是                      | 是                         |
| Token / Cost      | 是                | 是                 | 是                      | 是                         |
| LangGraph 拓扑图   | 是                | 部分               | 部分                    | **是 (xray 节点/边可视化)** |
| 底层协议           | 私有              | OTel               | OTel + OpenInference     | 私有                       |

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

| 维度              | LangSmith                  | Langfuse                | Phoenix                              | Opik                                                   |
| ----------------- | -------------------------- | ----------------------- | ------------------------------------ | ------------------------------------------------------ |
| 内置 metric 库     | 配套包 `openevals`          | 较少，多需手写           | `phoenix.evals` (RAG/Embedding 强项)  | **最丰富**: Hallucination/G-Eval/AnswerRelevance/Moderation 开箱即用 |
| 自定义 metric     | 函数返回 dict                | 函数 + `score_trace`     | 函数 / `ClassificationEvaluator` 子类  | 继承 `BaseMetric` 类                                   |
| 并行执行           | `max_concurrency`           | 手动循环                 | 默认并行                              | 默认并行                                                |
| pytest 集成        | 间接                        | 间接                     | 有 examples                          | **官方 `opik.integrations.pytest`**                    |
| 生产 trace 自动评分| 是 (Online evaluator)       | 是 (Server-side rules)   | 部分                                  | 是 (Online rules)                                      |

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

| 维度          | LangSmith           | Langfuse                              | Phoenix                       | Opik                  |
| ------------- | ------------------- | ------------------------------------- | ----------------------------- | --------------------- |
| 模板语法       | LangChain `{var}`    | Mustache `{{var}}` (可转 LangChain)   | Mustache `{{var}}`             | Mustache `{{var}}`     |
| 版本机制       | commit hash + tag    | version + labels (production/staging) | version + tag                 | commit hash           |
| UI 直接编辑    | 是                  | 是                                    | 是                             | 是                     |
| Playground 试跑| 是                  | 是                                    | 是                             | 是                     |
| trace 关联版本 | 是                  | 是 (`langfuse_prompt` metadata)        | 是                             | 是                     |

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

| 维度                  | LangSmith           | Langfuse             | Phoenix          | Opik              |
| --------------------- | ------------------- | -------------------- | ---------------- | ----------------- |
| 创建 API              | 两步 (dataset+examples) | 两步               | 一步              | 一步              |
| 从生产 trace 加数据   | 是 (UI 操作)         | 是 (UI 操作)         | 是 (UI 操作)      | 是 (UI 操作)      |
| 标注 / 人工反馈队列    | 是                  | 是                   | 较弱              | 是                |
| Dataset 版本化         | 是                  | 通过 metadata        | 是                | 是                |

---

## 6. 综合维度对比

### 6.1 项目基本面

| 维度           | LangSmith         | Langfuse              | Phoenix                       | Opik              |
| -------------- | ----------------- | --------------------- | ----------------------------- | ----------------- |
| 开发方         | LangChain Inc.    | Langfuse GmbH (DE)    | Arize AI                      | Comet ML          |
| 开源协议       | 闭源 (SaaS only)  | MIT (主仓) + EE       | Elastic v2 (OSS-friendly)     | Apache 2.0        |
| 自托管         | 仅企业版          | docker-compose 一键   | 单容器一键 (最轻)             | 官方安装脚本      |
| 自托管所需服务  | 无                | Postgres+ClickHouse+Redis+MinIO | SQLite (默认) / Postgres | MySQL+ClickHouse+Redis+前后端 |
| 默认 UI 端口   | -                 | 3000                  | 6006                          | 5173              |
| 主要付费形态   | SaaS 订阅         | Cloud + EE license    | Arize AX 商用版               | Comet Cloud       |
| 与 OTel 生态   | 不兼容            | v3+ 原生 OTel         | 完全 OTel (OpenInference)      | 不兼容            |

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

### 6.3 决策矩阵（按贵团队权重重新打分）

| 维度（权重）              | LangSmith | Langfuse | Phoenix | Opik |
| ------------------------- | --------- | -------- | ------- | ---- |
| 数据可自托管 (×3)         | 1         | 5        | 5       | 5    |
| LangGraph 接入丝滑度 (×3) | 5         | 4        | 4       | 4    |
| 评估能力 (×2)             | 4         | 3        | 4       | 5    |
| Prompt 管理 (×2)          | 5         | 5        | 4       | 4    |
| OTel 生态兼容 (×1)        | 1         | 4        | 5       | 1    |
| 运维成本 (×1, 越低越高分) | 5         | 3        | 5       | 3    |
| 长期开源/中立 (×1)        | 1         | 5        | 5       | 5    |
| **加权总分（示例）**      | **38**    | **48**   | **52**  | **48** |

数字是示例，**请按你们公司实际情况重新打分**——比如「合规」「国内网络」这些维度可以加上，权重也按业务重要度调。

---

## 7. 迁移成本 + 踩坑 + 评估方法论

### 7.1 迁移成本估算

| 现状 → 目标             | 成本                                       |
| ----------------------- | ----------------------------------------- |
| 裸 LangChain → LangSmith | 极低 (改环境变量)                          |
| LangSmith ↔ Langfuse    | 中 (改 callback, prompt 括号 `{}` ↔ `{{}}`)|
| LangSmith ↔ Phoenix     | 中 (改 register, prompt 改 mustache, eval API 重写) |
| LangSmith ↔ Opik        | 中 (改 callback, eval metric 重写)         |
| Langfuse ↔ Phoenix      | 低 (都是 OTel, trace 可双发并存)            |
| Phoenix → 其他          | 低 (trace 是标准 OTLP, 可同时保留)          |

### 7.2 团队最常踩的坑

1. **LangSmith 默认上报全部 input/output** 含敏感字段。生产前必须配 `LANGSMITH_HIDE_INPUTS` / `OUTPUTS` 或做字段脱敏。
2. **Langfuse v3 docker-compose 比 v2 复杂得多**（多了 ClickHouse + MinIO）。v2 升级需要走 migration script。
3. **Phoenix `register()` 只能调一次**。notebook 反复 import 会触发 OTel provider already set 警告。
4. **Opik 国内访问 Comet 镜像偶尔慢**，建议提前 pull / 配国内镜像源。
5. **secret key 永远不要在浏览器侧暴露**——4 家都一样。

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
- OpenInference SemConv (Phoenix 底座): https://github.com/Arize-ai/openinference
