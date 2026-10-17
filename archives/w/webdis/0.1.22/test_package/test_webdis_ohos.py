#!/usr/bin/env python3
"""HarmonyOS 平台专项测试 —— webdis 0.1.22（HarmonyOS PC / aarch64）。

由 test_package/conanfile.py 在 conanrun 环境下驱动：

    python3 test_webdis_ohos.py <webdis 可执行文件> [redis bin 目录]

两层内容，全部是真实执行而非桩：
  1. TestPlatformContract     —— 直接检查被测产物本身：ELF 形态、动态加载器、链接面、栈保护、是否泄漏宿主构建路径；
  2. TestRedisEndToEnd        —— 拉起真实 redis-server 与 webdis，用真实 HTTP / WebSocket / 流式订阅交互校验行为，
                                 包括上游 CI 未覆盖的 WebSocket 命令往返与 pub/sub 推流。

上游 CI（.github/workflows/build.yml）只在 Ubuntu + redis sidecar 上跑 python 用例，既不验证安装后二进制能否启动，
也不覆盖 HarmonyOS 平台契约，这两层正是本文件的目的。
"""
import base64
import http.client
import json
import os
import re
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import threading
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
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
HOST_BUILD_PATH_RE = re.compile(rb"/storage/|/home/|/Users/")


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def http_get(port, path, timeout=8):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        conn.request("GET", path)
        response = conn.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        conn.close()


def recv_exact(sock, count):
    data = b""
    while len(data) < count:
        chunk = sock.recv(count - len(data))
        if not chunk:
            raise AssertionError("WebSocket 连接在对端关闭前未收到完整数据")
        data += chunk
    return data


def ws_handshake(port, path="/.json", timeout=10):
    """真实完成一次 WebSocket 升级握手，并校验 Sec-WebSocket-Accept。"""
    import hashlib
    sock = socket.create_connection(("127.0.0.1", port), timeout=timeout)
    key = base64.b64encode(os.urandom(16)).decode()
    sock.sendall((
        f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nUpgrade: websocket\r\n"
        f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
    ).encode())
    head = b""
    while b"\r\n\r\n" not in head:
        head += sock.recv(1)
    expected = base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest()).decode()
    return sock, head, expected


def ws_send_text(sock, text):
    """按 RFC6455 发送一个带掩码的文本帧（客户端帧必须掩码）。"""
    payload = text.encode()
    mask = os.urandom(4)
    header = bytearray([0x81])
    if len(payload) < 126:
        header.append(0x80 | len(payload))
    elif len(payload) < 65536:
        header.append(0x80 | 126)
        header += struct.pack(">H", len(payload))
    else:
        header.append(0x80 | 127)
        header += struct.pack(">Q", len(payload))
    header += mask
    sock.sendall(bytes(header) + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))


def ws_recv_text(sock):
    """读取一个服务端文本帧（服务端帧不带掩码）。"""
    first = recv_exact(sock, 2)
    length = first[1] & 0x7F
    if length == 126:
        length = struct.unpack(">H", recv_exact(sock, 2))[0]
    elif length == 127:
        length = struct.unpack(">Q", recv_exact(sock, 8))[0]
    return recv_exact(sock, length).decode()


class TestPlatformContract(unittest.TestCase):
    """被测产物本身的 HarmonyOS 平台契约。"""

    @classmethod
    def setUpClass(cls):
        cls.readelf = shutil.which("readelf")
        cls.strings = shutil.which("strings")

    def _require(self, tool):
        if not tool:
            self.skipTest("本环境缺少 readelf/strings，无法校验 ELF 形态")

    def _readelf(self, *args):
        self._require(self.readelf)
        result = subprocess.run([self.readelf, *args, WEBDIS_BIN],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"readelf 失败：{result.stderr}")
        return result.stdout

    def test_elf_machine_is_aarch64(self):
        """产物是 AArch64 ELF64"""
        header = self._readelf("-h")
        self.assertIn("Class:", header)
        self.assertRegex(header, r"Class:\s+ELF64")
        self.assertRegex(header, r"Machine:\s+AArch64")

    def test_elf_is_position_independent(self):
        """产物是 PIE（ET_DYN）"""
        self.assertRegex(self._readelf("-h"), r"Type:\s+DYN .*Position-Independent Executable")

    def test_dynamic_loader_is_musl(self):
        """动态加载器是 OHOS 的 musl 加载器"""
        program = self._readelf("-lW")
        match = re.search(r"Requesting program interpreter: (\S+)\]", program)
        self.assertIsNotNone(match, "未找到 program interpreter")
        self.assertEqual(match.group(1), "/lib/ld-musl-aarch64.so.1")

    def test_no_glibc_linkage(self):
        """动态依赖里没有 glibc（libc.so.6 / ld-linux）"""
        dynamic = self._readelf("-d")
        self.assertNotIn("libc.so.6", dynamic)
        self.assertNotIn("ld-linux", dynamic)
        self.assertIn("[libc.so]", dynamic)

    def test_stack_is_non_executable(self):
        """GNU_STACK 为 RW（不可执行栈）"""
        program = self._readelf("-lW")
        stack = next((line.split() for line in program.splitlines()
                      if line.strip().startswith("GNU_STACK")), None)
        self.assertIsNotNone(stack, "未找到 GNU_STACK 段")
        self.assertEqual(stack[6], "RW")

    def test_no_host_build_path_in_binary(self):
        """二进制内不残留宿主构建路径（否则无法在目标机部署）"""
        if not self.strings:
            self.skipTest("本环境缺少 strings")
        result = subprocess.run([self.strings, WEBDIS_BIN], capture_output=True)
        leaked = HOST_BUILD_PATH_RE.findall(result.stdout)
        self.assertEqual(leaked, [], f"发现宿主构建路径残留：{set(leaked)}")


class TestRedisEndToEnd(unittest.TestCase):
    """拉起真实 redis-server + webdis 的端到端行为。"""

    @classmethod
    def setUpClass(cls):
        if REDIS_BIN_DIR:
            os.environ["PATH"] = REDIS_BIN_DIR + os.pathsep + os.environ.get("PATH", "")
        cls.redis_server = shutil.which("redis-server")
        if not cls.redis_server:
            raise unittest.SkipTest("未找到 redis-server，跳过端到端层")

        cls.tmp = tempfile.mkdtemp(prefix="webdis-ohos-", dir=TMP_BASE)
        cls.redis_port = free_port()
        cls.http_port = free_port()
        cls.redis_log = open(os.path.join(cls.tmp, "redis.log"), "w", encoding="utf-8")
        cls.redis_proc = subprocess.Popen([
            cls.redis_server, "--port", str(cls.redis_port), "--bind", "127.0.0.1",
            "--dir", cls.tmp, "--save", "", "--appendonly", "no", "--daemonize", "no",
        ], stdout=cls.redis_log, stderr=subprocess.STDOUT)
        cls._wait_redis()

        cls.logfile = os.path.join(cls.tmp, "webdis.log")
        cls.config = os.path.join(cls.tmp, "webdis.json")
        with open(cls.config, "w", encoding="utf-8") as handle:
            json.dump({
                "redis_host": "127.0.0.1",
                "redis_port": cls.redis_port,
                "http_host": "127.0.0.1",
                "http_port": cls.http_port,
                "threads": 4,
                "pool_size": 8,
                "daemonize": False,
                "websockets": True,
                "database": 0,
                "acl": [
                    {"disabled": ["DEBUG"]},
                    {"http_basic_auth": "user:password", "enabled": ["DEBUG"]},
                ],
                "verbosity": 6,
                "logfile": cls.logfile,
            }, handle)
        cls.webdis_out = open(os.path.join(cls.tmp, "webdis.out"), "w", encoding="utf-8")
        cls.webdis_proc = subprocess.Popen([WEBDIS_BIN, cls.config],
                                           stdout=cls.webdis_out, stderr=subprocess.STDOUT)
        cls._wait_webdis()

    @classmethod
    def _wait_redis(cls, timeout=20):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if cls.redis_proc.poll() is not None:
                raise AssertionError("redis-server 启动即退出")
            try:
                with socket.create_connection(("127.0.0.1", cls.redis_port), timeout=2) as sock:
                    sock.sendall(b"*1\r\n$4\r\nPING\r\n")
                    if sock.recv(64).startswith(b"+PONG"):
                        return
            except Exception:
                time.sleep(0.3)
        raise AssertionError("redis-server 未在预期时间内就绪")

    @classmethod
    def _wait_webdis(cls, timeout=20):
        """等待 webdis 就绪；HTTP 层就绪后还要等 Redis 连接池建立（首个请求可能返回 503）。"""
        deadline = time.time() + timeout
        last = None
        while time.time() < deadline:
            if cls.webdis_proc.poll() is not None:
                raise AssertionError("webdis 启动即退出")
            try:
                status, _, _ = http_get(cls.http_port, "/GET/__warmup", timeout=3)
                if status == 200:
                    return
                last = f"warmup 返回 {status}"
            except Exception as exc:
                last = exc
            time.sleep(0.3)
        raise AssertionError(f"webdis 未在预期时间内就绪（{last}）")

    @classmethod
    def tearDownClass(cls):
        for proc in (getattr(cls, "webdis_proc", None), getattr(cls, "redis_proc", None)):
            if proc is None:
                continue
            if proc.poll() is None:
                proc.send_signal(signal.SIGTERM)
                try:
                    proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    proc.kill()
        for handle in (getattr(cls, "webdis_out", None), getattr(cls, "redis_log", None)):
            if handle:
                handle.close()
        shutil.rmtree(getattr(cls, "tmp", ""), ignore_errors=True)

    # ── 基础读写 ──────────────────────────────────────────────────────
    def test_set_returns_ok(self):
        """HTTP SET 返回 {"SET":[true,"OK"]}"""
        status, headers, body = http_get(self.http_port, "/SET/ohos_key/hello")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Content-Type"), "application/json")
        self.assertEqual(json.loads(body), {"SET": [True, "OK"]})

    def test_get_returns_stored_value(self):
        """HTTP GET 取回刚写入的值"""
        http_get(self.http_port, "/SET/ohos_key/hello")
        _, _, body = http_get(self.http_port, "/GET/ohos_key")
        self.assertEqual(json.loads(body), {"GET": "hello"})

    def test_incr_returns_integer(self):
        """HTTP INCR 返回 JSON 整数"""
        http_get(self.http_port, "/DEL/ohos_counter")
        _, _, body = http_get(self.http_port, "/INCR/ohos_counter")
        self.assertEqual(json.loads(body), {"INCR": 1})

    def test_raw_format(self):
        """raw 输出格式返回 Redis 原始协议文本"""
        http_get(self.http_port, "/SET/ohos_raw/rv")
        _, headers, body = http_get(self.http_port, "/GET/ohos_raw.raw")
        self.assertEqual(headers.get("Content-Type"), "binary/octet-stream")
        self.assertEqual(body, b"$2\r\nrv\r\n")

    def test_msgpack_format(self):
        """MessagePack 输出格式返回真实 msgpack 字节流"""
        _, headers, body = http_get(self.http_port, "/SET/ohos_mp/v.msg")
        self.assertEqual(headers.get("Content-Type"), "application/x-msgpack")
        self.assertEqual(body, b"\x81\xa3SET\x92\xc3\xa2OK")   # {SET: [true, "OK"]}

    def test_redis_error_is_passed_through(self):
        """Redis 侧错误原样透传（HTTP 200 + ERR 文本）"""
        status, _, body = http_get(self.http_port, "/FOOBAR/x")
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertIn("FOOBAR", payload)
        self.assertIs(payload["FOOBAR"][0], False)
        self.assertIn("ERR unknown command", payload["FOOBAR"][1])

    def test_acl_blocks_disabled_command(self):
        """ACL 生效：匿名请求被禁用的 DEBUG 命令返回 403"""
        status, _, _ = http_get(self.http_port, "/DEBUG/sleep/0")
        self.assertEqual(status, 403)

    # ── 并发与通道 ────────────────────────────────────────────────────
    def test_parallel_requests_all_served(self):
        """20 个并发请求全部被真实服务（多线程事件循环 + 连接池）"""
        results = []
        lock = threading.Lock()

        def worker(index):
            try:
                status, _, body = http_get(self.http_port, f"/SET/ohos_par{index}/v{index}")
                with lock:
                    results.append((status, json.loads(body)))
            except Exception as exc:
                with lock:
                    results.append(("error", str(exc)))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        self.assertEqual(len(results), 20)
        self.assertEqual(results, [(200, {"SET": [True, "OK"]})] * 20)

    def test_websocket_command_roundtrip(self):
        """WebSocket 通道：真实握手 + 真实命令帧往返"""
        sock, head, expected_accept = ws_handshake(self.http_port, "/.json")
        try:
            self.assertIn(b"101 Switching Protocols", head)
            self.assertIn(f"Sec-WebSocket-Accept: {expected_accept}".encode(), head)
            ws_send_text(sock, json.dumps(["PING"]))
            self.assertEqual(json.loads(ws_recv_text(sock)), {"PING": [True, "PONG"]})
            ws_send_text(sock, json.dumps(["SET", "ohos_ws", "wsvalue"]))
            self.assertEqual(json.loads(ws_recv_text(sock)), {"SET": [True, "OK"]})
        finally:
            sock.close()

    def test_pubsub_subscribe_delivers_messages(self):
        """流式订阅：SUBSCRIBE 连接真实收到 PUBLISH 的消息"""
        channel = "ohos:channel"
        sock = socket.create_connection(("127.0.0.1", self.http_port), timeout=10)
        try:
            sock.sendall(f"GET /SUBSCRIBE/{channel} HTTP/1.0\r\n\r\n".encode())
            received = b""
            deadline = time.time() + 10
            while b'"subscribe"' not in received and time.time() < deadline:
                received += sock.recv(4096)
            self.assertIn(b'"subscribe"', received, f"未收到订阅确认：{received[:200]}")

            status, _, body = http_get(self.http_port, f"/PUBLISH/{channel}/payload-1")
            self.assertEqual(json.loads(body), {"PUBLISH": 1})

            deadline = time.time() + 10
            while b'"message"' not in received and time.time() < deadline:
                received += sock.recv(4096)
            self.assertIn(b'"message"', received, f"未收到推送消息：{received[:300]}")
            self.assertIn(b"payload-1", received)
        finally:
            sock.close()


if __name__ == "__main__":
    sys.argv = [sys.argv[0]]          # 夹具参数已取走，避免 unittest 误解析
    unittest.main(verbosity=2)
