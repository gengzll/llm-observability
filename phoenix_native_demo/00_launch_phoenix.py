"""启动 Phoenix 本地 server (内嵌进程, 不要 docker).

用法:
    终端 1:  python phoenix_native_demo\\00_launch_phoenix.py
            # 保持此窗口运行, Ctrl+C 退出

    终端 2:  python phoenix_native_demo\\01_tracing.py
            # 其他 demo 通过 PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006 连过来

注意:
    - 占用 6006 端口. 如果之前用 docker 起过 Phoenix, 先停:
      `docker compose -f phoenix_demo\\docker-compose.yml stop`
    - server 数据落盘到 ~/.phoenix/, 进程退出后数据保留, 下次启动还能看
"""

import time

import phoenix as px


if __name__ == "__main__":
    # launch_app(): 启动后台线程跑 server, 用 SQLite 落盘到 ~/.phoenix/
    session = px.launch_app()

    print()
    print(f"  Phoenix server  : {session.url}")
    print(f"  数据落盘       : ~/.phoenix/")
    print(f"  其他 demo     : 已自动通过 PHOENIX_COLLECTOR_ENDPOINT 环境变量连过来")
    print()
    print("  保持此窗口运行 -- 按 Ctrl+C 关闭 server (数据会保留).")
    print()

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n关闭 Phoenix server. 数据已保留在 ~/.phoenix/, 下次启动会自动加载.")
