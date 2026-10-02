#!/usr/bin/env python3
"""test_cli_e2e.py — thrulay 打包产物的命令行端到端消费者测试

用法: test_cli_e2e.py <package_folder> [port]

对**已安装的打包产物**做真实使用（与用户 `conan install` 后调用一致）：

  1. 产物契约   : bin/thrulay、bin/thrulayd 存在且可执行
  2. 版本冒烟   : thrulay -V / thrulayd -V → thrulay/2 与 0.9；-h → usage 与关键选项
  3. 真实测量   : 启动 thrulayd（-d 前台调试模式）→ 客户端 thrulay -p PORT -t 2 -i 1
                  127.0.0.1 完成一次完整 TCP 容量测量 → 退出码 0
  4. 报告解析   : 客户端报告含汇总行 "#(**)"，实测吞吐量 > 0；
                  服务端日志含 "listening on port"，进程可正常终止

SIGPIPE 规避：所有子进程输出重定向到文件（不使用管道），读侧不做 head-截断。
"""

import os
import re
import socket
import subprocess
import sys
import tempfile
import time

CHECKS = []
FAILED = []


def check(name, cond, detail=""):
    CHECKS.append(name)
    if cond:
        print(f"  [ok]   {name}" + (f" — {detail}" if detail else ""))
    else:
        FAILED.append(name)
        print(f"  [FAIL] {name}" + (f" — {detail}" if detail else ""))
    sys.stdout.flush()
    return bool(cond)


def run(cmd, env, timeout=60):
    """运行命令并把 stdout/stderr 落文件（避免管道 SIGPIPE）。"""
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "out")
        with open(out, "wb") as fp:
            try:
                rc = subprocess.call(cmd, stdout=fp, stderr=subprocess.STDOUT,
                                     env=env, timeout=timeout)
            except subprocess.TimeoutExpired:
                fp.close()
                with open(out, "rb") as rp:
                    return 124, rp.read().decode("utf-8", "replace")
        with open(out, "rb") as rp:
            return rc, rp.read().decode("utf-8", "replace")


def wait_listen(port, timeout=15.0):
    """等待服务端就绪（TCP connect 成功；thrulayd 常驻服务，探测连接无害）。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def parse_report(text):
    """返回 (汇总吞吐 Mb/s 或 None, 采样区间行数)。"""
    mbps = None
    intervals = 0
    for line in text.splitlines():
        if line.startswith("#(**)"):
            nums = re.findall(r"[-+]?\d+\.\d+", line)
            if len(nums) >= 3:
                mbps = float(nums[2])
        elif line.startswith(" (") or line.startswith("("):
            intervals += 1
    return mbps, intervals


def main():
    pkg = os.path.abspath(sys.argv[1])
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 53922

    client = os.path.join(pkg, "bin", "thrulay")
    server = os.path.join(pkg, "bin", "thrulayd")  # 上游装到 bindir，与 thrulay 同目录

    env = dict(os.environ)
    tmpdir = env.get("TMPDIR")
    if not tmpdir or not os.path.isdir(tmpdir) or not os.access(tmpdir, os.W_OK):
        tmpdir = tempfile.mkdtemp(prefix="thrulay-e2e-")
    env["TMPDIR"] = tmpdir

    print(f"thrulay CLI e2e — package={pkg} port={port} tmpdir={tmpdir}")

    # ---- [1/4] 产物契约 ----
    check("bin/thrulay present", os.path.isfile(client), client)
    check("bin/thrulayd present", os.path.isfile(server), server)
    check("bin/thrulay executable", os.access(client, os.X_OK))
    check("bin/thrulayd executable", os.access(server, os.X_OK))
    if FAILED:
        print(f"thrulay CLI e2e: {len(CHECKS) - len(FAILED)}/{len(CHECKS)} checks passed")
        return 1

    # ---- [2/4] 版本 / 帮助冒烟 ----
    rc, out = run([client, "-V"], env, timeout=30)
    check("thrulay -V exit 0", rc == 0, f"rc={rc}")
    check("thrulay -V reports thrulay/2", "thrulay/2" in out, out.strip()[:80])
    check("thrulay -V reports 0.9 release", "0.9" in out, out.strip()[:80])

    rc, out = run([server, "-V"], env, timeout=30)
    check("thrulayd -V exit 0", rc == 0, f"rc={rc}")
    check("thrulayd -V reports thrulay/2", "thrulay/2" in out, out.strip()[:80])

    rc, out = run([client, "-h"], env, timeout=30)
    check("thrulay -h prints usage", "sage" in out and "-t" in out and "-p" in out)

    # ---- [3/4] 真实 loopback 测量 ----
    srv_log = os.path.join(tmpdir, f"thrulayd-{port}.log")
    cli_log = os.path.join(tmpdir, f"thrulay-{port}.log")
    with open(srv_log, "wb") as srv_fp:
        proc = subprocess.Popen([server, "-d", "-p", str(port)], stdout=srv_fp,
                                stderr=subprocess.STDOUT, env=env)
        try:
            ready = wait_listen(port, timeout=15.0)
            check("thrulayd listening on port", ready, f"port={port}")
            rc, out = run([client, "-v", "-p", str(port), "-t", "2", "-i", "1", "127.0.0.1"],
                          env, timeout=90)
            with open(cli_log, "w") as fp:
                fp.write(out)
            check("thrulay client exit 0", rc == 0, f"rc={rc}")
            mbps, intervals = parse_report(out)
            check("client report has interval samples", intervals >= 1, f"{intervals} line(s)")
            check("measured TCP throughput > 0", mbps is not None and mbps > 0.0,
                  f"{mbps} Mb/s")
            check("loopback throughput plausible", mbps is not None and mbps > 1.0,
                  f"{mbps} Mb/s")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)

    # ---- [4/4] 服务端日志 ----
    with open(srv_log, "rb") as fp:
        srv_text = fp.read().decode("utf-8", "replace")
    check("server log shows listening", "listening on port" in srv_text,
          srv_text.strip().splitlines()[-1][:90] if srv_text.strip() else "(empty)")
    check("server log shows client connection", "127.0.0.1" in srv_text)

    total, failed = len(CHECKS), len(FAILED)
    print(f"thrulay CLI e2e: {total - failed}/{total} checks passed")
    if failed:
        print("failed checks: " + ", ".join(FAILED))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
