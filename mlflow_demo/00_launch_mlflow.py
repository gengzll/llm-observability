"""启动 MLflow tracking server (本地 SQLite, 不要 docker).

用法:
    终端 1:  python mlflow_demo\\00_launch_mlflow.py
            # 保持窗口运行, Ctrl+C 退出

    终端 2:  python mlflow_demo\\01_tracing.py
            # 其他 demo 通过 MLFLOW_TRACKING_URI=http://localhost:5000 连过来

数据落盘:
    - ~/.mlflow/mlflow.db       (SQLite backend, 存 run / experiment / metric)
    - ~/.mlflow/artifacts/       (log_artifact 上传的文件)
"""

import os
import subprocess
import sys
from pathlib import Path


working_dir = Path.home() / ".mlflow"
working_dir.mkdir(parents=True, exist_ok=True)
artifacts_dir = working_dir / "artifacts"
artifacts_dir.mkdir(parents=True, exist_ok=True)

backend_uri = f"sqlite:///{working_dir / 'mlflow.db'}"
# artifact root 必须带 URI scheme, client 才认.
# 用 mlflow-artifacts:/ + --serve-artifacts 让 server 代理 artifact 上传,
# client 走 HTTP 不直接访问 file system, 最稳.
artifact_root = "mlflow-artifacts:/"
artifacts_destination = f"file:///{artifacts_dir.as_posix()}"


def main() -> int:
    print()
    print(f"  MLflow tracking : http://localhost:5000/")
    print(f"  Backend        : {backend_uri}")
    print(f"  Artifact root  : {artifact_root} (server proxied)")
    print(f"  Artifacts dest : {artifacts_destination}")
    print()
    print("  保持此窗口运行 -- 按 Ctrl+C 关闭 server (数据会保留).")
    print()

    venv_scripts = Path(sys.executable).parent
    cli = venv_scripts / "mlflow.exe"
    if not cli.exists():
        cli = venv_scripts / "mlflow"  # Linux/Mac

    try:
        return subprocess.Popen(
            [
                str(cli),
                "server",
                "--host", "127.0.0.1",
                "--port", "5000",
                "--backend-store-uri", backend_uri,
                "--default-artifact-root", artifact_root,
                "--artifacts-destination", artifacts_destination,
                "--serve-artifacts",
            ],
            env=os.environ,
        ).wait()
    except KeyboardInterrupt:
        print("\n关闭 MLflow server. 数据已保留, 下次启动会自动加载.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
