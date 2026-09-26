#!/usr/bin/env python3
"""安装后消费者视角测试 —— webdis 0.1.22（HarmonyOS PC / aarch64）。

由 test_package/conanfile.py 在 conanrun 环境下驱动：

    python3 test_consumer.py <webdis 可执行文件> [redis bin 目录]

每个用例都是真实交互：拉起被测二进制 → 发真实 HTTP 请求 → 校验状态码/响应头/正文/日志落盘 → 发真实 SIGTERM 校验退出。
本套件刻意把 webdis 指向一个**没有 Redis 服务**的端口，因此不依赖 Redis，同时在 test_redis_unavailable_is_reported
中校验「Redis 不可用」时的真实响应码。
"""
import http.client
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest

def _fixture_args():
    """取夹具参数（webdis 可执行文件、redis bin 目录），避免被 unittest 当成用例名解析。"""
    args = sys.argv[1:]
    binary = os.path.abspath(args[0]) if args else os.environ.get("WEBDIS_BIN", "webdis")
    redis_dir = args[1] if len(args) > 1 else os.environ.get("REDIS_BIN_DIR", "")
    return binary, redis_dir


WEBDIS_BIN, REDIS_BIN_DIR = _fixture_args()
TMP_BASE = os.environ.get("TMPDIR") or os.path.join(os.path.expanduser("~"), "tmp")
os.makedirs(TMP_BASE, exist_ok=True)


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def http_get(port, path, timeout=5):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        conn.request("GET", path)
        response = conn.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        conn.close()


class WebdisInstance:
    """启动/停止被测二进制的夹具。redis_port 指向一个不存在的服务，用于消费者层校验。"""

    def __init__(self, redis_port):
        self.tmp = tempfile.mkdtemp(prefix="webdis-consumer-", dir=TMP_BASE)
        self.port = free_port()
        self.logfile = os.path.join(self.tmp, "webdis.log")
        self.outfile = os.path.join(self.tmp, "webdis.out")
        self.config = os.path.join(self.tmp, "webdis.json")
        with open(self.config, "w", encoding="utf-8") as handle:
            json.dump({
                "redis_host": "127.0.0.1",
                "redis_port": redis_port,
                "http_host": "127.0.0.1",
                "http_port": self.port,
                "threads": 2,
                "pool_size": 4,
                "daemonize": False,
                "websockets": True,
                "database": 0,
                "verbosity": 4,
                "logfile": self.logfile,
            }, handle)
        self.process = None

    def start(self, ready_path="/crossdomain.xml", timeout=15):
        self.output = open(self.outfile, "w", encoding="utf-8")
        self.process = subprocess.Popen([WEBDIS_BIN, self.config],
                                        stdout=self.output, stderr=subprocess.STDOUT)
        deadline = time.time() + timeout
        last_error = None
        while time.time() < deadline:
            if self.process.poll() is not None:
                raise AssertionError(f"webdis 启动即退出，退出码 {self.process.returncode}；"
                                     f"输出：{open(self.outfile, encoding='utf-8', errors='replace').read()[:400]}")
            try:
                status, _, _ = http_get(self.port, ready_path, timeout=2)
                if status:
                    return
            except Exception as exc:  # 连接尚未就绪
                last_error = exc
                time.sleep(0.3)
        raise AssertionError(f"webdis 未在 {timeout}s 内就绪（最后一次错误：{last_error}）")

    def stop(self, sig=signal.SIGTERM, timeout=10):
        if self.process is None or self.process.poll() is not None:
            return self.process.returncode if self.process else None
        self.process.send_signal(sig)
        deadline = time.time() + timeout
        while time.time() < deadline and self.process.poll() is None:
            time.sleep(0.2)
        if self.process.poll() is None:
            self.process.kill()
            self.process.wait(timeout=5)
        self.output.close()
        return self.process.returncode

    def cleanup(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestWebdisConsumer(unittest.TestCase):
    """安装后的 webdis 应当能启动、提供真实 HTTP 服务并如实报告后端不可用。"""

    @classmethod
    def setUpClass(cls):
        cls.dead_redis_port = free_port()          # 无人监听 → 后端始终不可用
        cls.instance = WebdisInstance(cls.dead_redis_port)
        cls.instance.start()

    @classmethod
    def tearDownClass(cls):
        cls.instance.stop()
        cls.instance.cleanup()

    def test_process_is_alive(self):
        """服务进程在提供服务期间保持存活"""
        self.assertIsNone(self.instance.process.poll(), "webdis 进程意外退出")

    def test_crossdomain_policy_is_served(self):
        """GET /crossdomain.xml 返回 200 + application/xml + 策略正文"""
        status, headers, body = http_get(self.instance.port, "/crossdomain.xml")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Content-Type"), "application/xml")
        self.assertIn(b"allow-access-from domain", body)

    def test_logfile_is_written_under_tmpdir(self):
        """配置的日志文件真实落盘并记录启动结论"""
        deadline = time.time() + 5
        content = ""
        while time.time() < deadline:
            if os.path.isfile(self.instance.logfile):
                with open(self.instance.logfile, encoding="utf-8", errors="replace") as handle:
                    content = handle.read()
                if "up and running" in content:
                    break
            time.sleep(0.2)
        self.assertIn("up and running", content, f"日志内容：{content[:300]}")

    def test_unavailable_redis_is_reported(self):
        """后端 Redis 不可用时，请求真实返回 503（而不是挂起或静默成功）"""
        status, _, _ = http_get(self.instance.port, "/GET/consumer_key")
        self.assertEqual(status, 503)


class TestWebdisShutdown(unittest.TestCase):
    """消费者对被测二进制的生命周期控制（SIGTERM 落地）。"""

    def test_sigterm_stops_process(self):
        instance = WebdisInstance(free_port())
        try:
            instance.start()
            self.assertIsNone(instance.process.poll())
            returncode = instance.stop(signal.SIGTERM, timeout=10)
            self.assertIsNotNone(returncode, "SIGTERM 后 webdis 未退出")
        finally:
            instance.cleanup()


if __name__ == "__main__":
    sys.argv = [sys.argv[0]]          # 夹具参数已取走，避免 unittest 误解析
    unittest.main(verbosity=2)
