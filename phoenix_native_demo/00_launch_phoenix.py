"""启动 Phoenix 本地 server (不要 docker).

实现方式: subprocess 调 `arize-phoenix serve` CLI.

为什么不用 `px.launch_app()`:
    - launch_app 是 Jupyter notebook 用的轻量启动器
    - 内部 thread_server.py 写死了 5 秒启动 timeout
    - Windows 上 SQLite migration 经常 >5s, 必超时

为什么要 sandbox / WASM 跳过技巧:
    - Phoenix server 启动时会同步 prefetch 一个 CPython WASM sandbox binary
      (用于安全沙箱执行用户代码), 下载源在 GitHub Release
    - 国内访问超时, 30 秒后 fail-soft 才放行 → "Waiting for application startup"
      看似永远卡住, 实际是在等下载超时
    - 解决: 设 PHOENIX_WASM_BINARY_PATH 指向一个 dummy 文件 → 代码看到 path 存在
      就直接 return, 跳过下载. 配合 PHOENIX_ALLOWED_SANDBOX_PROVIDERS=NONE
      禁用 sandbox runtime 使用 (我们 demo 不需要)
"""

import os
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# 落盘目录
# ---------------------------------------------------------------------------
working_dir = Path.home() / ".phoenix"
working_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("PHOENIX_WORKING_DIR", str(working_dir))


# ---------------------------------------------------------------------------
# WASM binary 跳过下载 (国内必须)
# ---------------------------------------------------------------------------
# 1. dummy 文件指向 working_dir 下一个固定路径; 不必有正确 WASM 内容, 但必须
#    非空 (Phoenix validate_env_wasm_binary_path 拒绝 0-byte 文件)
dummy_wasm = working_dir / "dummy.wasm"
if not dummy_wasm.exists() or dummy_wasm.stat().st_size == 0:
    dummy_wasm.write_bytes(b"placeholder")

# 2. 告诉 Phoenix 用这个 path 作为 WASM binary, 跳过 GitHub 下载
os.environ.setdefault("PHOENIX_WASM_BINARY_PATH", str(dummy_wasm))

# 3. 同时禁用所有 sandbox providers (虽然 dummy 不会真被读, 但 belt-and-suspenders)
os.environ.setdefault("PHOENIX_ALLOWED_SANDBOX_PROVIDERS", "NONE")


def main() -> int:
    print()
    print(f"  Phoenix server     : http://localhost:6006/")
    print(f"  数据落盘          : {working_dir}")
    print(f"  WASM binary path  : {dummy_wasm} (dummy, 仅为跳过下载)")
    print(f"  Sandbox providers : NONE (禁用)")
    print()
    print("  保持此窗口运行 -- 按 Ctrl+C 关闭 server (数据会保留).")
    print()

    # 找 venv 内的 arize-phoenix CLI
    venv_scripts = Path(sys.executable).parent
    cli = venv_scripts / "arize-phoenix.exe"
    if not cli.exists():
        cli_unix = venv_scripts / "arize-phoenix"  # Linux/Mac fallback
        cli = cli_unix if cli_unix.exists() else cli

    try:
        proc = subprocess.Popen(
            [str(cli), "serve"],
            env=os.environ,
        )
        return proc.wait()
    except KeyboardInterrupt:
        print("\n关闭 Phoenix server. 数据已保留, 下次启动会自动加载.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
