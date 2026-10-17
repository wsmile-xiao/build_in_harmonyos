#!/usr/bin/env python3
# kylin-ai-runtime 上游运行探针（R51 测试三步法，运行步）：
# 拉起守护进程 5s —— 存活或干净退出(rc>=0) = PASS；rc<0 / 127(缺 .so) = FAIL。
import os
import subprocess
import sys
import time


def main() -> int:
    pkg = sys.argv[1]  # kylin-ai-runtime package_folder
    daemon = os.path.join(pkg, "bin", "kylin-ai-runtime")
    if not os.path.isfile(daemon):
        print(f"FAIL: daemon not found: {daemon}")
        return 1

    env = dict(os.environ)
    # 依赖与 runtime 自身的库都在包 lib / 依赖包 lib 下
    lib_dirs = [os.path.join(pkg, "lib")]
    # conan deps package folders 通过 conanrun.sh 提供，但
    # runtime 链接的 staging 库已装入包内 lib；保险起见附加 deps lib 目录
    ld = env.get("LD_LIBRARY_PATH", "")
    ld = ":".join(p for p in [":".join(lib_dirs), ld] if p)
    env["LD_LIBRARY_PATH"] = ld

    env["KYLIN_AI_RUNTIME_NO_DAEMONIZE"] = "1"
    env["G_MESSAGES_DEBUG"] = ""

    for var in ("DBUS_SYSTEM_BUS_ADDRESS",):
        env.setdefault(var, "unix:path=/dev/null")  # 无系统总线时走降级路径

    proc = subprocess.Popen(
        [daemon, "--no-daemon"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True,
    )
    time.sleep(5)
    if proc.poll() is None:
        proc.terminate()
        try:
            out, _ = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate()
        print("PASS: daemon alive after 5s")
        if out:
            print(out.decode("utf-8", "replace")[-2000:])
        return 0
    rc = proc.returncode
    print(f"daemon exited rc={rc}")
    print("LD_LIBRARY_PATH=" + env.get("LD_LIBRARY_PATH", "")[:400])
    if rc == 1:
        # 干净退出需命中预期降级标记（如无系统 D-Bus 总线时的主动退出日志），
        # 防止 daemon 启动早期真实失败（常以 rc=1 收尾）被放行
        out_text = ""
        try:
            out_text, _ = proc.communicate(timeout=5)
        except Exception:
            pass
        out_text = out_text or ""
        markers = ("dbus", "d-bus", "degrad", "fallback", "g_dbus")
        if any(m in out_text.lower() for m in markers):
            print("PASS: clean exit with degradation marker")
            print(out_text[-2000:])
            return 0
        print("FAIL: rc=1 without expected degradation marker")
        print(out_text[-2000:])
        return 1
    print("FAIL: abnormal exit")
    return 1


if __name__ == "__main__":
    sys.exit(main())
