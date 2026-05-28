# Opik Demo

Comet 开源的 LLM 观测 + 评估平台（Apache 2.0）。和 Comet ML 同源，评估能力（内置 metric 库 + G-Eval）相对最丰富。

## 本地起服务

Opik 推荐用官方安装脚本（内部封装了 docker compose）：

```powershell
# Windows
git clone https://github.com/comet-ml/opik.git
cd opik
.\opik.ps1
```

```bash
# Linux / macOS
git clone https://github.com/comet-ml/opik.git
cd opik
./opik.sh
```

脚本会自动拉镜像 → 启容器 → 健康检查 → 打开浏览器，访问 http://localhost:5173 。

> 本目录下的 `docker-compose.yml` 只是一个**提示文件**（提醒上面的脚本路径）。直接 `docker compose up` 不会启动 Opik 服务。

启动后配置 SDK：

```powershell
# 方式 1: 一次性配置 (写到 ~/.opik.config)
python -c "import opik; opik.configure(use_local=True)"

# 方式 2: 写到根目录的 .env (本仓库其他 demo 一致风格)
# OPIK_URL_OVERRIDE=http://localhost:5173/api
# OPIK_WORKSPACE=default
# OPENAI_API_KEY=sk-xxx
```

## 安装 + 跑 demo

```powershell
pip install -r requirements.txt

python 01_tracing.py            # 链路追踪
python 04_dataset.py            # 先建 dataset
python 02_evaluation.py         # 跑评估
python 03_prompt_management.py  # Prompt 版本管理
```

## 关键 API 速查

| 能力          | API                                                            |
| ------------- | -------------------------------------------------------------- |
| LangGraph 集成 | `OpikTracer(graph=app.get_graph(xray=True))` → callbacks       |
| 手动 trace     | `@track(name="...", project_name="...")` 装饰任意函数            |
| 评估          | `from opik.evaluation import evaluate; evaluate(experiment_name, dataset, task, scoring_metrics)` |
| 自定义 metric  | 继承 `opik.evaluation.metrics.base_metric.BaseMetric`           |
| Dataset       | `client.get_or_create_dataset(name); dataset.insert([...])`     |
| Prompt        | `opik.Prompt(name, prompt, metadata)` 构造即推送, `client.get_prompt(name, commit=...)` 拉取 |

## 集成 LangGraph 的姿势

`OpikTracer(graph=app.get_graph(xray=True))` 作为 callback 注入。`xray=True` 让 Opik 在 UI 里渲染 graph 拓扑图（节点 / 边 / 条件分支可视化），这是 4 个框架里唯一原生支持 LangGraph 拓扑可视化的。

## Opik 的差异化卖点

- **内置 metric 最多**: Hallucination / AnswerRelevance / ContextPrecision / G-Eval / Moderation 等 LLM-as-judge metric 直接可用，自己不用写 prompt
- **支持 pytest 集成**: `opik.integrations.pytest` 把评估写成单元测试，CI 里直接跑
- **rule-based monitoring**: 生产 trace 上自动跑 metric（生产 LLM 输出实时打分），其他三家需要自己拼
