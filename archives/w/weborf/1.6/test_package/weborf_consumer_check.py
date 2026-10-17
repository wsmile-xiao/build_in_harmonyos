#!/usr/bin/env python3
"""weborf 消费者测试：以库/工具使用者身份真实运行被测二进制并断言其行为。

失败即以非零码退出（由 test_package/conanfile.py 的 self.run 转为构建失败）。
断言清单（7 条）：
  A1 bin/weborf 存在且可执行
  A2 --version 退出码 0
  A3 --version 输出含 "Weborf"
  A4 --help 退出码 0 且输出含 "Usage"
  A5 真实起 HTTP 服务后 GET /index.txt 返回 200
  A6 响应体与语料逐字节相等
  A7 缺失文件必须返回 404（防"起了服务但任何请求都成功"的假通过）
"""
import http.server
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request


def fail(msg):
    print("ASSERT-FAIL: %s" % msg)
    return 1


def main():
    if len(sys.argv) < 2:
        return fail("用法: weborf_consumer_check.py <weborf 可执行文件>")
    exe = sys.argv[1]
    if not (os.path.isfile(exe) and os.access(exe, os.X_OK)):
        return fail("A1 可执行文件缺失或不可执行: %s" % exe)
    print("A1 ok  被测二进制 %s" % exe)

    env = dict(os.environ)
    if not env.get("MAGIC"):
        # 静态 libmagic 需要显式数据文件；conan runenv 通常已注入，这里兜底探测
        print("     注: 环境未提供 MAGIC，--mime 相关行为不在本测试断言范围内")

    p = subprocess.run([exe, "--version"], capture_output=True, text=True,
                       env=env, timeout=60)
    if p.returncode != 0:
        return fail("A2 --version 退出码 %s (stderr=%r)" % (p.returncode, p.stderr[:120]))
    print("A2 ok  --version rc=0")
    if "Weborf" not in p.stdout:
        return fail("A3 --version 输出不含 Weborf: %r" % p.stdout[:120])
    print("A3 ok  --version 输出 %r" % p.stdout.strip().splitlines()[0])

    h = subprocess.run([exe, "--help"], capture_output=True, text=True, env=env, timeout=60)
    if h.returncode != 0 or "Usage" not in h.stdout:
        return fail("A4 --help 异常 rc=%s 前 80 字=%r" % (h.returncode, h.stdout[:80]))
    print("A4 ok  --help 含 Usage")

    docroot = tempfile.mkdtemp(prefix="weborf-consumer-")
    token = "weborf consumer probe\n"
    with open(os.path.join(docroot, "index.txt"), "w", encoding="utf-8") as fh:
        fh.write(token)

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()

    proc = subprocess.Popen([exe, "-b", docroot, "-p", str(port)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    try:
        base = "http://127.0.0.1:%d" % port
        status = body = None
        for _ in range(60):
            time.sleep(0.25)
            try:
                with urllib.request.urlopen(base + "/index.txt", timeout=5) as r:
                    status, body = r.status, r.read()
                break
            except (urllib.error.URLError, ConnectionError, OSError):
                if proc.poll() is not None:
                    return fail("A5 服务进程提前退出 rc=%s" % proc.returncode)
                continue
        if status is None:
            return fail("A5 服务未在 127.0.0.1:%d 应答（超时）" % port)
        if status != 200:
            return fail("A5 GET /index.txt 状态码 %s" % status)
        print("A5 ok  GET /index.txt -> 200")
        if body.decode("utf-8") != token:
            return fail("A6 响应体与语料不一致: %r" % body[:80])
        print("A6 ok  响应体逐字节一致（%d 字节）" % len(body))
        try:
            urllib.request.urlopen(base + "/no-such-file-hw2", timeout=5)
            return fail("A7 缺失文件居然返回了成功")
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                return fail("A7 缺失文件状态码 %s（期望 404）" % exc.code)
            print("A7 ok  缺失文件 -> 404")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=20)
        import shutil
        shutil.rmtree(docroot, ignore_errors=True)

    print("ALL 7 ASSERTIONS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
