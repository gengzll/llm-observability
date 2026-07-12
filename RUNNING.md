# 运行说明 (Running Guide)

实测把 Phoenix / Langfuse / LangSmith / Opik 4 家 × 4 类 demo = 16 个文件**全部跑通**后整理的实操手册。所有命令都是 Windows PowerShell 实测有效的、可直接复制粘贴。

> 想看「为什么」「各家对比结论」，看 [README.md](README.md)。本文档只讲「怎么跑」。

---

## 目录

- [0. 一次性环境准备](#0-一次性环境准备)
- [1. Phoenix demo](#1-phoenix-demo)
- [2. Langfuse demo](#2-langfuse-demo)
- [3. LangSmith demo](#3-langsmith-demo)
- [4. Opik demo](#4-opik-demo)
- [5. MLflow demo](#5-mlflow-demo)
- [6. 端口 + 资源占用速查](#6-端口--资源占用速查)
- [7. 实战踩坑（亲测 10 条）](#7-实战踩坑亲测-10-条)
- [8. 常用诊断命令](#8-常用诊断命令)
- [9. 完全清理](#9-完全清理)

---

## 0. 一次性环境准备

### 0.1 前置软件

| 项                  | 版本要求         | 实测版本     |
| ------------------- | ---------------- | ------------ |
| Python              | ≥ 3.10           | 3.12.7       |
| Docker Desktop      | ≥ 24             | 29.5.2       |
| Docker Compose      | ≥ v2.20          | v5.1.4       |
| Windows             | 10 22H2 / 11     | -            |
| WSL2 后端           | 必开             | -            |

Docker Desktop 必须勾选 **Settings > General > Use the WSL 2 based engine**。

### 0.2 配 pip 镜像源（国内必须）

国内访问 pypi.org 极慢，不配会卡 5-15 分钟。**装依赖前必须做**：

```powershell
python -m pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/
python -m pip config set install.trusted-host pypi.tuna.tsinghua.edu.cn
```

清华挂的备用：`https://mirrors.aliyun.com/pypi/simple/` / `https://pypi.mirrors.ustc.edu.cn/simple/`

### 0.3 配 Docker 镜像源（国内必须）

打开 **Docker Desktop > Settings > Docker Engine**，合并进 JSON：

```json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
```

点 **Apply & Restart**。

### 0.4 建 venv + 装合集依赖

```powershell
cd D:\work\llm-observability
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

约 3-5 分钟，装齐 4 家所有依赖（~600MB）。验证：

```powershell
pip list | findstr /i "langgraph langchain langsmith langfuse phoenix opik openinference"
```

应该看到 `langchain` / `langgraph` / `langsmith` / `langfuse` / `arize-phoenix` / `opik` 等。

### 0.5 配 LLM Provider（智谱免费 + 兼容 OpenAI）

本仓库默认走**智谱 AI**（免费、国内通、兼容 OpenAI SDK）。复制 `.env.example` 为 `.env`：

```powershell
copy .env.example .env
```

编辑 `.env`，确保前 3 行：

```env
OPENAI_API_KEY=<填你的智谱 key>
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
OPENAI_MODEL=glm-4-flash
```

申请智谱 key：https://open.bigmodel.cn/usercenter/apikeys （5 分钟搞定）。

> 想换 DeepSeek / OpenAI 官方 / Ollama 本地：只改 `OPENAI_BASE_URL` 和 `OPENAI_MODEL` 即可，**4 家 demo 都自动复用**（agent 用 `langchain-openai` 的 `ChatOpenAI` 走 OpenAI 兼容协议）。

### 0.6 PowerShell 中文不乱码（每次新开窗口都要做）

Python 打印中文，PowerShell 默认 GBK 编码会乱码。**每条跑 demo 的命令开头都加**：

```powershell
$env:PYTHONIOENCODING="utf-8"
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

或者把这 3 行写到 PowerShell profile（`$PROFILE`）里，永久生效。

### 0.7 Sanity check：智谱 key + agent 能跑通

在跑任何 demo 之前，先验证最基础的链路 OK：

```powershell
.\.venv\Scripts\Activate.ps1
python common\sample_agent.py
```

应该输出（中文可能乱码，但能看到「订单」「电子产品」字样即说明 LangGraph 工作 + 智谱 key 工作）：

```
您的订单 A1001 已发货，预计 2 天送达。
电子产品支持 7 天无理由退货...
```

跑通了再开始下面 4 家。**没跑通**别往下，先排查智谱 key / 网络 / venv。

---

## 1. Phoenix demo

**最轻**（单容器 SQLite，500MB 内存）、**最快**（30s 起服务）、**最容易**（不要注册账号）。

### 1.1 拉镜像 + 起服务

```powershell
docker pull arizephoenix/phoenix:latest
docker compose -f phoenix_demo\docker-compose.yml up -d
```

等 30 秒。验证：

```powershell
docker ps --filter "name=phoenix"
# 应该看到 phoenix_demo-phoenix-1 Up X seconds, 端口 0.0.0.0:6006->6006 / 0.0.0.0:4317->4317
```

UI 入口：http://localhost:6006（无需登录）。

### 1.2 跑 4 个 demo（顺序很重要）

```powershell
# 每个新 PowerShell 窗口都先做：
$env:PYTHONIOENCODING="utf-8"; chcp 65001 | Out-Null; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
.\.venv\Scripts\Activate.ps1

# 1. Tracing (3 个 trace 上报)
python phoenix_demo\01_tracing.py

# 2. Dataset (必须在 evaluation 之前, 否则 evaluation 找不到 dataset)
python phoenix_demo\04_dataset.py

# 3. Evaluation (跑 7 task × 2 evaluator = 14 评估)
python phoenix_demo\02_evaluation.py

# 4. Prompt 管理 (push + pull + 渲染调 LLM)
python phoenix_demo\03_prompt_management.py
```

### 1.3 看 UI

打开 http://localhost:6006，左侧侧栏：

- **Projects** → `llm-obs-demo`：看 trace
- **Datasets** → `agent-cs-eval-v1`：看上传的 7 条
- **Datasets** → `agent-cs-eval-v1` → **Experiments**：看评估结果
- **Prompts** → `cs-agent-system`：看 prompt 版本

### 1.4 已知警告（无害）

- `Overriding of current TracerProvider is not allowed` — 一个 Python 进程里多次调 `register()`，提示但不报错
- `Attempting to instrument while already instrumented` — 同上
- prompt demo 拉 `:prod` tag 报 404 — demo 注释里已说明（首次跑没打过 tag）

### 1.5 关停

```powershell
docker compose -f phoenix_demo\docker-compose.yml stop
# 下次直接 start (不要 up, 否则可能重建 volume)
docker compose -f phoenix_demo\docker-compose.yml start
```

---

## 2. Langfuse demo

**最重**（6 容器 + 4-6GB 内存）、**最折腾**（initialization 多步），但 UI/UX 最现代。

### 2.1 拉镜像（6 个）

```powershell
docker compose -f langfuse_demo\docker-compose.yml pull
```

总计约 2.5GB。

### 2.2 起服务（2-3 分钟）

```powershell
docker compose -f langfuse_demo\docker-compose.yml up -d
```

容器启动顺序：postgres / clickhouse / redis / minio → langfuse-worker → langfuse-web。**等 web 容器 Up About a minute** 才算就绪：

```powershell
docker compose -f langfuse_demo\docker-compose.yml ps
```

### 2.3 ⚠ 必做：创建 MinIO bucket

Langfuse v3 用 MinIO 存事件原始 JSON。MinIO 启动时默认不会建 bucket，需要手动创建。**漏掉这步会导致 trace 上报失败（500 Internal Server Error）**：

```powershell
docker run --rm --network langfuse_demo_default --entrypoint /bin/sh minio/mc -c "mc alias set local http://minio:9000 minio miniosecret && mc mb -p local/langfuse && mc ls local/"
```

看到 `Bucket created successfully` 就 OK。

### 2.4 验证 init + 拿 keys

`docker-compose.yml` 里已经预设了 keys，不用进 UI 拿，直接确认 init 成功：

```powershell
$pk="pk-lf-1234567890abcdef1234567890abcdef"
$sk="sk-lf-1234567890abcdef1234567890abcdef"
$cred = [System.Convert]::ToBase64String([System.Text.Encoding]::ASCII.GetBytes("${pk}:${sk}"))
(Invoke-WebRequest -Uri "http://localhost:3000/api/public/projects" -Headers @{Authorization = "Basic $cred"}).Content
```

应该返回 `{"data":[{"id":"demo-project","name":"demo-project","organization":{"id":"demo-org",...}}]}`。

`.env` 里已经填好这两个预设 key，不用改。

### 2.5 跑 4 个 demo

```powershell
$env:PYTHONIOENCODING="utf-8"; chcp 65001 | Out-Null; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
.\.venv\Scripts\Activate.ps1

python langfuse_demo\01_tracing.py
python langfuse_demo\04_dataset.py
python langfuse_demo\02_evaluation.py
python langfuse_demo\03_prompt_management.py
```

### 2.6 看 UI

打开 http://localhost:3000，用 `admin@local.test` / `ChangeMe123!` 登录：

- **Traces**：看上报的 trace
- **Datasets > agent-cs-eval-v1 > Runs > baseline-glm-4-flash**：看评估结果
- **Prompts > cs-agent-system**：看 prompt v1 (production label)

### 2.7 已知警告（无害）

- `[WARN] This Redis server's default user does not require a password, but a password was supplied` — Redis 不强制密码但 SDK 提供了，无害
- prompt demo 拉 `staging` label 报 404 — demo 注释里已说明

### 2.8 关停

```powershell
docker compose -f langfuse_demo\docker-compose.yml stop
docker compose -f langfuse_demo\docker-compose.yml start
```

**`down -v` 会删 volume + 清空所有数据**，请谨慎。

---

## 3. LangSmith demo

**最简单**（不要 docker），但**国内需要代理**访问 smith.langchain.com。

### 3.1 注册账号 + 拿 key

1. 去 https://smith.langchain.com 注册（用 google / github 一键登录）
2. 右上角头像 > **Settings > API Keys > Create API key**
3. 复制 `lsv2_pt_xxx...` 形式的 key

### 3.2 填 .env

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt_xxx
LANGSMITH_PROJECT=llm-obs-demo
```

### 3.3 跑 4 个 demo

```powershell
$env:PYTHONIOENCODING="utf-8"; chcp 65001 | Out-Null; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
.\.venv\Scripts\Activate.ps1

python langsmith_demo\01_tracing.py
python langsmith_demo\04_dataset.py
python langsmith_demo\02_evaluation.py
python langsmith_demo\03_prompt_management.py
```

### 3.4 看 UI

打开 https://smith.langchain.com，左上角选你的 organization：

- **Tracing Projects > llm-obs-demo**：看 trace
- **Datasets & Testing > agent-cs-eval-v1**：看 dataset
- **Datasets > Experiments**：看评估
- **Prompts > cs-agent-system**：看 prompt

### 3.5 已知警告（无害）

- prompt demo 拉 `:prod` tag 报 404 — demo 注释里已说明

### 3.6 关停

不需要——纯 SaaS，无本地服务。

---

## 4. Opik demo

**最折腾的启动**（需要 clone opik 源码），但**评估能力最强 + 输出最直观**（带 ASCII 摘要框）。

### 4.1 下载 Opik 源码

```powershell
cd D:\work\llm-observability
git clone https://github.com/comet-ml/opik.git opik_demo\opik-main
```

或者下载 https://github.com/comet-ml/opik/archive/refs/heads/main.zip 解压到 `opik_demo\opik-main\`。

### 4.2 拉镜像（4 个 Opik 自家 + 5 个依赖）

```powershell
docker pull ghcr.io/comet-ml/opik/opik-backend:latest
docker pull ghcr.io/comet-ml/opik/opik-frontend:latest
docker pull ghcr.io/comet-ml/opik/opik-python-backend:latest
docker pull ghcr.io/comet-ml/opik/opik-sandbox-executor-python:latest
```

依赖镜像（mysql / clickhouse / redis / zookeeper / minio）docker compose 会自动拉。

### 4.3 起服务（必须 `--profile opik`）

```powershell
cd opik_demo\opik-main
docker compose -f deployment/docker-compose/docker-compose.yaml --profile opik up -d
cd D:\work\llm-observability
```

> ⚠ **不带 `--profile opik` 只会起 mysql/clickhouse/redis/zookeeper/minio，不会启动 backend/frontend/python-backend。** Opik 的 compose 给应用层服务都打了 `profiles: [opik]`。

等 2-3 分钟，Java backend 启动较慢。验证：

```powershell
docker ps --filter "name=opik" --format "table {{.Names}}`t{{.Status}}"
```

应该看到 `opik-backend-1`, `opik-frontend-1`, `opik-python-backend-1` 全部 `(healthy)`。

### 4.4 跑 4 个 demo

`.env` 里 `OPIK_URL_OVERRIDE=http://localhost:5173/api` 已经填好，直接跑：

```powershell
$env:PYTHONIOENCODING="utf-8"; chcp 65001 | Out-Null; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
.\.venv\Scripts\Activate.ps1

python opik_demo\01_tracing.py
python opik_demo\04_dataset.py
python opik_demo\02_evaluation.py
python opik_demo\03_prompt_management.py
```

### 4.5 看 UI

打开 http://localhost:5173（无需登录，本地模式）：

- **Projects > llm-obs-demo**：看 trace
- **Datasets > agent-cs-eval-v1**：看 dataset
- **Experiments**：看评估结果（命令行已经打印 ASCII summary）
- **Prompts > cs-agent-system**：看 prompt

### 4.6 已知警告（无害）

- `OPIK: No project name configured. Traces are being logged to "Default Project"` — eval/prompt demo 不强制指定 project，无害
- `OPIK: Failed to process CreateTraceBatchMessage. Error: [WinError 10054]` — 进程退出时空 flush 撞上 nginx idle close，trace 实际已上报
- `OPIK: opik.Prompt() is deprecated` — SDK 新版推荐 `client.create_prompt()`，老 API 仍可用
- `Prompt was found via workspace-wide search` — 同上，未来版本将要求显式指定 project

### 4.7 关停

```powershell
cd opik_demo\opik-main
docker compose -f deployment/docker-compose/docker-compose.yaml --profile opik stop
cd D:\work\llm-observability
```

---

## 5. MLflow demo

**跟 Phoenix native 一样不用 docker**（本地 `mlflow server` 一句话起），特别适合已经用 Databricks / MLflow 管 ML 实验的团队。

### 5.1 补装依赖

MLflow 不在合集 `requirements.txt` 里（要求较新版本），单独补装：

```powershell
.\.venv\Scripts\Activate.ps1
pip install "mlflow>=3.0.0" "pandas>=2.0.0"
```

### 5.2 起服务（**终端 1，保持运行**）

```powershell
python mlflow_demo\00_launch_mlflow.py
```

输出：
```
  MLflow tracking : http://localhost:5000/
  Backend        : sqlite:///C:\Users\<you>\.mlflow\mlflow.db
  Artifact root  : mlflow-artifacts:/ (server proxied)
  Artifacts dest : file:///C:/Users/<you>/.mlflow/artifacts
  保持此窗口运行 -- 按 Ctrl+C 关闭 server.
```

**端口冲突**：如果 5000 被别的服务占，改 `00_launch_mlflow.py` 里 `--port 5000` 为其他端口，同时其他 demo 跑前设 `$env:MLFLOW_TRACKING_URI="http://localhost:<新端口>"`。

### 5.3 跑 4 个 demo（**终端 2**）

```powershell
$env:PYTHONIOENCODING="utf-8"; chcp 65001 | Out-Null; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
.\.venv\Scripts\Activate.ps1

python mlflow_demo\01_tracing.py            # 3 native + 2 langgraph 两个 experiment
python mlflow_demo\04_dataset.py            # 7 条 dataset log 到 run
python mlflow_demo\02_evaluation.py         # 7 sample × 2 metric = 14 分, ~1-2 分钟
python mlflow_demo\03_prompt_management.py  # register_prompt / load_prompt (v1 / v2)
```

### 5.4 看 UI

打开 http://localhost:5000：

| 想看什么           | UI 路径                                                                |
| ------------------ | --------------------------------------------------------------------- |
| Trace 嵌套结构     | Experiments > **mlflow-native-demo** / **mlflow-langgraph-demo** > 点某个 run 打开右边 Trace tab |
| Dataset           | Experiments > **mlflow-dataset-demo** > dataset-upload > Datasets tab  |
| 评估分数 + 详细结果 | Experiments > **mlflow-eval-demo** > baseline-glm-4-flash > Metrics + Artifacts (`eval_results.csv`) |
| Prompt            | 顶部导航 **Prompts** > `cs-agent-mlflow-system` (Playground 能试跑)     |

### 5.5 已知警告（无害）

- `MLflow job execution requirements not met (does not support Windows system)` — MLflow 3.x 的 job 特性不支持 Windows；只跑 tracing/eval/prompt 不需要 job，忽略即可
- `The specified dataset source can be interpreted in multiple ways` — MLflow 会自动选 LocalArtifactDatasetSource
- Prompt 拉 `@production` alias 报 not found — 首次运行的预期行为
- `FutureWarning: mlflow.register_prompt ... moved to mlflow.genai namespace` — MLflow 3.14 迁移，本仓库已用新 API 避免这条

### 5.6 关停

终端 1 里 Ctrl+C，数据保留在 `~/.mlflow/mlflow.db` 和 `~/.mlflow/artifacts/`。下次 `python 00_launch_mlflow.py` 秒起（数据库和缓存都在）。

**清空重来**（换 model / 重跑基线时想清空历史）：

```powershell
# 先 Ctrl+C 停 server, 然后
Remove-Item -Force "$env:USERPROFILE\.mlflow\mlflow.db" -ErrorAction SilentlyContinue
```

Windows sandbox 有时会保护 `%USERPROFILE%` 下的删除，如果失败改用 bash：

```bash
rm -f "C:/Users/gengz/.mlflow/mlflow.db"
```

---

## 6. 端口 + 资源占用速查

| 服务                                    | 端口      | 内存 (运行时)  | 启动时长     |
| --------------------------------------- | --------- | -------------- | ------------ |
| Phoenix (单容器, SQLite)                | 6006 / 4317 | ~500 MB        | ~30 秒        |
| Langfuse (web)                          | 3000      | ~600 MB        | ~2 分钟       |
| Langfuse (worker)                       | -         | ~400 MB        | -            |
| Langfuse (postgres + clickhouse + redis + minio) | - | ~2.5 GB        | -            |
| Opik (frontend)                         | 5173      | ~100 MB        | ~5 秒         |
| Opik (backend, Java)                    | 内部 3003 | ~1.5 GB        | ~60 秒        |
| Opik (python-backend)                   | 内部 8000 | ~500 MB        | ~30 秒        |
| Opik (mysql + clickhouse + redis + zookeeper + minio) | - | ~2 GB | ~60 秒  |
| LangSmith                               | -         | 0 (云端)       | 0             |
| MLflow (server, SQLite + serve-artifacts) | 5000    | ~200 MB        | ~10 秒        |
| Phoenix native (launch_app 内嵌)         | 6006 / 4317 | ~500 MB      | ~30 秒 首启 (首次要下 26MB WASM), 之后秒起 |

**同时跑 Phoenix + Langfuse + Opik 总内存**：~ 8-10 GB。**建议机器 ≥ 16GB**，不用时 `docker compose stop` 关停省内存。

**只跑 MLflow / Phoenix native**：~ 500 MB - 1 GB 就够，笔记本无压力。

镜像磁盘占用：~ 9-10 GB（4 家全装）。MLflow / Phoenix native 不用镜像，只占 SQLite / WASM 缓存约 100 MB。

---

## 7. 实战踩坑（亲测 10 条）

按踩到的频率排：

### 7.1 国内 pip 不配镜像 → pip install 卡 10+ 分钟

**症状**：`pip install -r requirements.txt` 看不到任何进度，但 python 进程在跑。
**根因**：默认走 pypi.org，国内极慢。
**修复**：[0.2 节](#02-配-pip-镜像源国内必须)。

### 7.2 Langfuse 单机 ClickHouse 缺 `CLICKHOUSE_CLUSTER_ENABLED=false`

**症状**：langfuse-web 日志 `error: failed to open database: There is no Zookeeper configuration in server config`，反复 Restarting。
**根因**：Langfuse v3 默认假设 ClickHouse 是集群（`ON CLUSTER default` + `ReplicatedMergeTree`），需要 Zookeeper 协调；单机模式不存在 Zookeeper 配置。
**修复**：`langfuse-web` 和 `langfuse-worker` 的 environment 加 `CLICKHOUSE_CLUSTER_ENABLED: "false"`。本仓库 `langfuse_demo/docker-compose.yml` 已修。

### 7.3 Langfuse MinIO `langfuse` bucket 不存在

**症状**：trace 上报 500 Internal Server Error，worker 日志 `Failed to upload JSON to S3 ... The specified bucket does not exist`。
**根因**：MinIO 启动时不会自动建 bucket，Langfuse compose 也没加 init service。
**修复**：[2.3 节](#23--必做创建-minio-bucket) 的 `mc mb` 命令。

### 7.4 Langfuse INIT 必须 8 个全填

**症状**：`docker compose up` 起来后 UI 空空如也，没 demo-org / demo-project。
**根因**：Langfuse 检测 8 个 `LANGFUSE_INIT_*` 变量必须全填才执行初始化，缺一个**静默跳过**。
**修复**：本仓库 compose 已补全 `LANGFUSE_INIT_USER_NAME` / `LANGFUSE_INIT_ORG_NAME` / `LANGFUSE_INIT_PROJECT_NAME` / `LANGFUSE_INIT_PROJECT_PUBLIC_KEY` / `LANGFUSE_INIT_PROJECT_SECRET_KEY`。

### 7.5 Phoenix client v15+ 不兼容 v8 server

**症状**：`python phoenix_demo\04_dataset.py` 报 `KeyError: 'version_id'`。
**根因**：`arize-phoenix-client>=15.0` 期望 server 返回 `version_id` 字段，v8 server 没这个字段。
**修复**：compose 用 `arizephoenix/phoenix:latest`（v15+），别 pin 到 `version-8.0.0`。本仓库已修。

### 7.6 Opik 不带 `--profile opik` 只起底层

**症状**：`docker compose up -d` 看似成功，但只有 mysql/clickhouse/redis/zookeeper/minio，没 opik-backend/frontend/python-backend。
**根因**：Opik 给应用层服务打了 `profiles: [opik]` 标签，不带 profile 不启动。
**修复**：`docker compose -f deployment/docker-compose/docker-compose.yaml --profile opik up -d`。

### 7.7 智谱不支持 OpenAI JSON mode → openevals 失败

**症状**：LangSmith demo `02_evaluation.py` 评估器报 `OutputParserException('Invalid json output: Score: 4/5...')`。
**根因**：`openevals` 的 LLM-as-judge 依赖 OpenAI 的 structured output / JSON mode，智谱（DeepSeek 等）兼容网关不支持。
**修复**：不用 `openevals`，手写 LLM-as-judge prompt（"只输出一个数字"）。本仓库 `langsmith_demo/02_evaluation.py` 已改。

### 7.8 PowerShell 默认 GBK → Python 输出中文乱码

**症状**：`python xxx.py` 输出 `���Ķ��� A1001 �ѷ���` 这种乱码。
**根因**：Windows PowerShell 控制台默认 GBK，Python stdout 默认 locale 编码不一致。
**修复**：[0.6 节](#06-powershell-中文不乱码每次新开窗口都要做) 的 3 行命令。

### 7.9 MLflow `--default-artifact-root` 必须带 URI scheme

**症状**：`WARNING mlflow.tracing.export.mlflow_v3: Failed to send trace to MLflow backend: Could not find a registered artifact repository for: c:\Users\...\artifacts/1/traces/tr-...`。Agent 跑通，答案输出，但 trace 没入库。
**根因**：MLflow 3.x client 不接受裸 Windows 路径作 artifact repo，需要 URI scheme（`file:///`、`mlflow-artifacts:/` 等）。
**修复**：`mlflow server` 启动加 `--default-artifact-root mlflow-artifacts:/` + `--artifacts-destination file:///<abs-path>` + `--serve-artifacts` 让 server 代理 artifact 上传。本仓库 `mlflow_demo/00_launch_mlflow.py` 已配。

### 7.10 MLflow 3.14+ prompt API 迁移到 `mlflow.genai` namespace

**症状**：`FutureWarning: The mlflow.register_prompt API is moved to the mlflow.genai namespace.`
**根因**：MLflow 3.14 起把 prompt registry 从顶层 API 迁到 `mlflow.genai` 命名空间，老 API 仍能用但会 deprecated。
**修复**：改用 `mlflow.genai.register_prompt(...)` 和 `mlflow.genai.load_prompt(...)`，签名不变。本仓库 `mlflow_demo/03_prompt_management.py` 已改。

---

## 8. 常用诊断命令

### 看所有容器状态

```powershell
docker ps -a --format "table {{.Names}}`t{{.Status}}`t{{.Ports}}"
```

### 看某个容器的实时日志

```powershell
# 跟踪 (Ctrl+C 退出, 容器不会停)
docker logs -f langfuse_demo-langfuse-web-1

# 最后 50 行
docker logs --tail 50 langfuse_demo-langfuse-worker-1
```

### 看磁盘占用

```powershell
docker system df
```

### 查询服务是否真的能用

```powershell
# Phoenix
(Invoke-WebRequest "http://localhost:6006").StatusCode

# Langfuse (健康检查)
(Invoke-WebRequest "http://localhost:3000/api/public/health").Content

# Opik (frontend)
(Invoke-WebRequest "http://localhost:5173").StatusCode
```

### 进容器内部 shell

```powershell
docker exec -it langfuse_demo-langfuse-web-1 sh
docker exec -it opik-backend-1 sh
```

### 看 venv 已装包

```powershell
.\.venv\Scripts\Activate.ps1
pip list | findstr /i "langgraph langchain langsmith langfuse phoenix opik"
```

---

## 9. 完全清理

### 9.1 关停所有服务（保留数据）

```powershell
# docker 的 3 家
docker compose -f phoenix_demo\docker-compose.yml stop
docker compose -f langfuse_demo\docker-compose.yml stop
cd opik_demo\opik-main
docker compose -f deployment/docker-compose/docker-compose.yaml --profile opik stop
cd D:\work\llm-observability

# 非 docker 的两家: 各自终端 1 按 Ctrl+C
#   phoenix_native_demo/00_launch_phoenix.py
#   mlflow_demo/00_launch_mlflow.py
```

### 9.2 删容器 + 数据（不留任何痕迹）

```powershell
# Phoenix
docker compose -f phoenix_demo\docker-compose.yml down -v

# Langfuse
docker compose -f langfuse_demo\docker-compose.yml down -v

# Opik
cd opik_demo\opik-main
docker compose -f deployment/docker-compose/docker-compose.yaml --profile opik down -v
cd D:\work\llm-observability
```

### 9.3 删镜像（释放 ~10 GB）

```powershell
docker rmi arizephoenix/phoenix:latest
docker rmi langfuse/langfuse:3 langfuse/langfuse-worker:3
docker rmi ghcr.io/comet-ml/opik/opik-backend:latest ghcr.io/comet-ml/opik/opik-frontend:latest ghcr.io/comet-ml/opik/opik-python-backend:latest ghcr.io/comet-ml/opik/opik-sandbox-executor-python:latest
# 中间件镜像 (如果还要跑别的项目可以留)
docker rmi postgres:15 clickhouse/clickhouse-server:24 redis:7 minio/minio:latest mysql:8.4.2 zookeeper:3.9.4
```

或者一条命令清掉所有未使用镜像：

```powershell
docker system prune -a
```

### 9.4 删 venv

```powershell
Remove-Item -Recurse -Force .venv
```

### 9.5 删源码（如果不再需要）

```powershell
Remove-Item -Recurse -Force opik_demo\opik-main
```

### 9.6 清 MLflow / Phoenix native 数据（本地 SQLite）

```powershell
# MLflow (SQLite + artifacts)
Remove-Item -Force "$env:USERPROFILE\.mlflow\mlflow.db" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$env:USERPROFILE\.mlflow\artifacts\*" -ErrorAction SilentlyContinue

# Phoenix native (SQLite + WASM 缓存)
Remove-Item -Recurse -Force "$env:USERPROFILE\.phoenix" -ErrorAction SilentlyContinue
```

Windows sandbox 有时保护 `%USERPROFILE%` 下的删除；如果 PowerShell 报错，改用 bash：

```bash
rm -f "C:/Users/gengz/.mlflow/mlflow.db"
rm -rf "C:/Users/gengz/.phoenix"
```
