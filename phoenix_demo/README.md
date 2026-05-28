# Arize Phoenix Demo

Arize 开源的 OSS 观测平台。底座是 **OpenInference**（OTel 在 LLM 场景的语义约定，目前在 OTel 社区已被广泛认可），与厂商无关，是 4 个框架里唯一原生 OTel 的方案。

## 本地起服务

```powershell
# 在 phoenix_demo/ 目录下
docker compose up -d

# 几秒就 Ready, 浏览器打开 http://localhost:6006
# 默认不开认证, 直接进 UI
```

写到根目录的 `.env`：

```
PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006
OPENAI_API_KEY=sk-xxx
```

## 安装 + 跑 demo

```powershell
pip install -r requirements.txt

python 01_tracing.py            # 链路追踪
python 04_dataset.py            # 先建 dataset
python 02_evaluation.py         # 跑评估 (Experiment)
python 03_prompt_management.py  # Prompt 版本管理
```

## 关键 API 速查

| 能力          | API                                                                  |
| ------------- | -------------------------------------------------------------------- |
| 全局 register  | `from phoenix.otel import register; register(project_name, auto_instrument=True)` |
| LangChain 集成 | `LangChainInstrumentor().instrument(tracer_provider=...)` (auto_instrument 已包含) |
| 评估 Experiment | `client.experiments.run_experiment(dataset, task, evaluators)`    |
| Dataset       | `client.datasets.create_dataset(name, inputs, outputs)`              |
| Prompt 推送    | `client.prompts.create(name, version=PromptVersion(...))`            |
| Prompt 拉取    | `client.prompts.get(prompt_identifier=name, tag="prod")`             |

## 集成 LangGraph 的姿势

`register(auto_instrument=True)` 一行搞定。底层是 OTel SDK，意味着：
- 同样的 trace 数据可以**同时**发到 Phoenix + Tempo / Jaeger / Honeycomb（fan-out exporter）
- 想给非 LangChain 代码补埋点，直接用 `opentelemetry.trace.get_tracer(__name__).start_as_current_span(...)`，不需要 Phoenix 专属的装饰器

代价：评估和 Prompt API 是 Phoenix 私有的，不像 trace 那样可移植。
