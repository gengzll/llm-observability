# Langfuse Demo

完全开源、可商用（MIT 协议主仓 + 部分企业功能 EE 协议），Python SDK v3 已转向 OpenTelemetry 底座。

## 本地起服务

```powershell
# 在 langfuse_demo/ 目录下
docker compose up -d

# 等 2-3 分钟, 直到 langfuse-web 容器日志显示 "Ready"
# 浏览器打开 http://localhost:3000
# 用 docker-compose.yml 里 LANGFUSE_INIT_USER_EMAIL / PASSWORD 登录
# (admin@local.test / ChangeMe123!)
```

进入 UI 后：

1. 进入 `demo-org / demo-project`（compose 已经自动建好）
2. **Settings > API Keys > Create new API keys**，复制 public key + secret key
3. 写到根目录的 `.env`：
   ```
   LANGFUSE_HOST=http://localhost:3000
   LANGFUSE_PUBLIC_KEY=pk-lf-xxx
   LANGFUSE_SECRET_KEY=sk-lf-xxx
   OPENAI_API_KEY=sk-xxx
   ```

> 注意：上面的 docker-compose 是一个**裁剪过的最小版**（足够跑 demo）。生产部署请用官方仓库的完整 compose：https://github.com/langfuse/langfuse/blob/main/docker-compose.yml

## 安装 + 跑 demo

```powershell
pip install -r requirements.txt

python 01_tracing.py            # 链路追踪
python 04_dataset.py            # 先建 dataset
python 02_evaluation.py         # 再跑评估
python 03_prompt_management.py  # Prompt 版本管理
```

## 关键 API 速查

| 能力          | API                                                            |
| ------------- | -------------------------------------------------------------- |
| LangGraph 集成 | `from langfuse.langchain import CallbackHandler`              |
| 手动 trace     | `@observe(name="...", as_type="span")` 装饰任意函数             |
| 评估          | `dataset.items` 循环 + `item.run()` 上下文 + `span.score_trace()` |
| Dataset       | `langfuse.create_dataset_item(dataset_name, input, expected_output)` |
| Prompt 推送    | `langfuse.create_prompt(name, prompt, labels=["production"])`  |
| Prompt 拉取    | `langfuse.get_prompt(name, label="production")`                |

## 集成 LangGraph 的姿势

需要写一行：在 `graph.invoke(...)` 时 `config={"callbacks": [CallbackHandler()]}`。CallbackHandler 内部基于 OTel SDK，所以 trace 在底层是标准 OTLP span，可以另接 Tempo / Jaeger 等通用后端（这是相对其他三家的差异点）。
