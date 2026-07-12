# MLflow demo — 老牌 ML 平台加 LLM tracing

给「**已经用 Databricks / MLflow 管 ML 实验**」的团队：想把 LLM agent 一起纳入现有的 tracking / registry / experimentation 体系，**不额外再养一个专用 LLM 观测平台**。

特点：

- **不用 docker** —— `mlflow server` 本地 SQLite 一句话起
- **两种 agent 都示范** —— 裸 OpenAI SDK (`agent_native.py`) + LangGraph (`agent_langgraph.py`)
- **complete stack** —— Tracing / Evaluation / Prompt Registry / Dataset 全套 MLflow-native API
- **一个 UI 全管** —— 同一 MLflow UI 里 LLM tracing 和传统 sklearn / xgboost 实验并列

---

## 文件结构

```
mlflow_demo/
├── README.md
├── requirements.txt
├── agent_native.py          (裸 OpenAI SDK + @mlflow.trace + mlflow.start_span 手埋)
├── agent_langgraph.py       (复用 common/sample_agent.py, 靠 mlflow.langchain.autolog())
├── 00_launch_mlflow.py      (启动 mlflow server, 长跑保持)
├── 01_tracing.py            (两种 agent 都跑一遍, 分别 log 到不同 experiment)
├── 04_dataset.py            (upload dataset)
├── 02_evaluation.py         (跑评估 + log_metric + log_artifact)
└── 03_prompt_management.py  (register_prompt / load_prompt / alias)
```

---

## 0. 装依赖

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r mlflow_demo\requirements.txt
```

---

## 1. 启动 MLflow server（**终端 1，保持运行**）

```powershell
python mlflow_demo\00_launch_mlflow.py
```

输出：
```
  MLflow tracking : http://localhost:5000/
  Backend        : sqlite:///C:\Users\<you>\.mlflow\mlflow.db
  Artifact root  : C:\Users\<you>\.mlflow\artifacts
  保持此窗口运行 -- 按 Ctrl+C 关闭 server.
```

**端口冲突**：如果 5000 被别的服务占（比如 Docker Desktop 有时候用 5000），改 `00_launch_mlflow.py` 里 `--port 5000` 为其他端口，同时更新其他 demo 里的 `MLFLOW_TRACKING_URI`。

---

## 2. 跑 demo（**终端 2**）

```powershell
$env:PYTHONIOENCODING="utf-8"; chcp 65001 | Out-Null; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
.\.venv\Scripts\Activate.ps1

python mlflow_demo\01_tracing.py
python mlflow_demo\04_dataset.py
python mlflow_demo\02_evaluation.py
python mlflow_demo\03_prompt_management.py
```

打开 http://localhost:5000 看：

| UI 路径                                                  | 内容                                                          |
| -------------------------------------------------------- | ------------------------------------------------------------- |
| Experiments > **mlflow-native-demo**                     | 裸 SDK 版的 trace（`agent.run > LLM > tool.*` 嵌套）           |
| Experiments > **mlflow-langgraph-demo**                  | LangGraph 版的 trace（LangGraph 每个 node 自动展开的 span）     |
| Experiments > **mlflow-eval-demo** > baseline-glm-4-flash | 评估 run，含 correctness / length_ok metric + eval_results.csv artifact |
| Experiments > **mlflow-dataset-demo** > dataset-upload   | 数据集 log_input 记录 + CSV artifact                            |
| **Prompts** (顶部导航)                                    | `cs-agent-mlflow-system` v1，可 Edit / Playground / Set alias  |

---

## 关键 API 速查

| 能力              | MLflow API                                                                 |
| ----------------- | -------------------------------------------------------------------------- |
| 自动 instrument   | `mlflow.openai.autolog()` / `mlflow.langchain.autolog()`                    |
| 手埋 span         | `@mlflow.trace(name, span_type)` / `mlflow.start_span(name, span_type)`     |
| 评估              | 手动 loop + `mlflow.log_metric(name, value, step=i)` + `log_artifact()`     |
| 高级评估          | `mlflow.evaluate(model, data, extra_metrics)`（对智谱等兼容网关不友好，慎用）  |
| Prompt 推送       | `mlflow.register_prompt(name, template, commit_message, tags)`             |
| Prompt 拉取       | `mlflow.load_prompt(name)` / `load_prompt(f"prompts:/{name}@production")`   |
| Dataset           | `mlflow.data.from_pandas(df, name)` + `mlflow.log_input(dataset)`           |

---

## 和其他 4 家的差异 & 定位

| 维度              | Phoenix / Langfuse / Opik                     | MLflow                                                   |
| ----------------- | --------------------------------------------- | -------------------------------------------------------- |
| 定位              | **LLM-native 观测平台**                        | **传统 ML 平台加 LLM 功能**                                |
| Dataset 模型      | 一等公民，独立 UI，evaluation 遍历             | 主要绑到 run 上（也有 Datasets 页）                        |
| Evaluation UI     | Experiments 视图对比多次 run，score 表格化      | Runs 对比表 + metric 图表                                  |
| Prompt Registry   | 一等公民，UI Playground + 版本管理             | 一等公民，UI Playground + 版本 + alias                    |
| LLM-specific 视图 | 精细（token / cost / tool call 结构化）         | 通用（span 树 + metadata），LLM 字段和传统 metric 混一起  |
| 传统 ML 集成      | ❌ 只做 LLM                                    | ✅ 同一 UI 里 sklearn / xgboost / LLM 全管                 |
| 团队 buy-in       | 需要引入新平台                                 | 现有 MLflow 用户 0 学习成本                                |

**适合**：Databricks 生态、ML + LLM 混合项目、已经在用 MLflow 的团队。

**不适合**：纯 LLM 团队（用 Phoenix / Langfuse 的 LLM-specific 视图更好用）。

---

## 已知警告（无害）

- Prompt demo 拉 `@production` alias 报 not found —— 首次运行预期，注释里说明
- 首次 `mlflow.openai.autolog()` 后如果 openai 版本比 mlflow 支持的新，会打一行 compatibility warning，通常无害
