"""启动 Phoenix 本地 server (不要 docker).

实现方式: subprocess 调用 `arize-phoenix serve` CLI.

为什么不用 `px.launch_app()`:
    - launch_app 是 Jupyter notebook 用的轻量启动器
    - 内部 thread_server.py 把启动 timeout 写死为 5 秒 (HARDCODE)
    - Windows 上首次启动 (SQLite migration + uvicorn boot) 经常 >5s, 必超时
    - 报错: "RuntimeError: server took too long to start"

首次启动注意:
    - Phoenix 启动时会下载一个 ~26 MB 的 CPython WASM binary
      (用于安全沙箱执行用户代码), 下载源在 GitHub Release.
    - 国内访问 github.com 慢, 首次启动可能要 1-3 分钟.
    - 下载完后缓存到 PHOENIX_WORKING_DIR/wasm/, 后续启动秒起.
    - 完全用不到 sandbox 且不想等下载, 可设这两个环境变量跳过:
        PHOENIX_WASM_BINARY_PATH=<任何非空文件的绝对路径>
        PHOENIX_ALLOWED_SANDBOX_PROVIDERS=NONE
"""

import os
import subprocess
import sys
from pathlib import Path


# 数据落盘目录 (SQLite + WASM 缓存); 默认 ~/.phoenix/
working_dir = Path.home() / ".phoenix"
working_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("PHOENIX_WORKING_DIR", str(working_dir))


def main() -> int:
    print()
    print(f"  Phoenix server  : http://localhost:6006/")
    print(f"  数据落盘       : {working_dir}")
    print()
    print("  首次启动会从 GitHub 下载约 26 MB WASM binary,")
    print("  国内网络可能慢 1-3 分钟; 之后缓存到 ~/.phoenix/wasm/, 秒起.")
    print()
    print("  保持此窗口运行 -- 按 Ctrl+C 关闭 server.")
    print()

    # 找 venv 内的 arize-phoenix CLI (跨平台)
    venv_scripts = Path(sys.executable).parent
    cli = venv_scripts / "arize-phoenix.exe"
    if not cli.exists():
        cli = venv_scripts / "arize-phoenix"  # Linux/Mac

    try:
        return subprocess.Popen([str(cli), "serve"], env=os.environ).wait()
    except KeyboardInterrupt:
        print("\n关闭 Phoenix server. 数据已保留, 下次启动会自动加载.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
