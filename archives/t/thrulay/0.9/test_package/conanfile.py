#!/usr/bin/env python3
"""test_package — thrulay 0.9（Autotools；库 + CLI 双消费者 e2e）

上游 0.9 不随发布包提供任何测试（configure.ac 无 AC_CONFIG_TESTDIR，Makefile.am
无 check_PROGRAMS/TESTS，`make check` 报 "Nothing to be done"），故本包自带两层
**真实消费者测试**，两层都直接使用打包产物：

1) test_lib_consumer.c —— 库 API 消费者（链接 include/thrulay/*.h + lib/libthrulay.a）
   同进程 fork 出服务端（thrulay_server_init → _listen → _start），父进程用
   thrulay_client_options_init → _init → _start → _report_final → _exit 完成一次
   完整 TCP 测量，并把客户端上报的实测报告解析为断言（吞吐量 > 0、有采样区间行、
   服务端子进程正常退出）。

2) test_cli_e2e.py —— 命令行消费者（bin/thrulay + bin/thrulayd）
   版本/帮助冒烟 + 真实 loopback 测量（起 thrulayd -d，客户端连测量 2s），
   解析报告汇总行断言吞吐量 > 0。

环境约束（E002 / E525）：
  * OHOS 目标机 /tmp 只读，编译中间文件必须落到显式 TMPDIR；
  * 编译/链接子进程**不注入** conan 依赖库目录到 LD_LIBRARY_PATH —— 该目录会
    顶掉 SDK lld 自带的运行库（DT_NEEDED libxml2.so.16），导致 lld 启动即挂
    （clang: unable to execute command: No such file or directory）。本包
    libthrulay 静态链接、无 conan 依赖，运行期也无需注入。
"""

import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment

# OHOS SDK clang：与 ci/conan/profiles/ohos-aarch64 的
# tools.build:compiler_executables 一致，作为 conf 读不到时的兜底绝对路径。
OHOS_SDK_CLANG = "/data/service/hnp/bin/clang"


class ThrulayTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # ───────────────────────── 环境探测 ─────────────────────────

    def _c_compiler(self):
        """定位消费者用例的 C 编译器（profile conf → OHOS SDK 兜底 → CC/cc/gcc）。"""
        exes = {}
        try:
            exes = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:  # conf 跨上下文不可读时退化为路径探测
            pass
        tried = []
        for cand in (exes.get("c"), OHOS_SDK_CLANG, os.environ.get("CC"),
                     "clang", "cc", "gcc"):
            if not cand:
                continue
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
            found = shutil.which(cand)
            if found:
                return found
            tried.append(cand)
        raise ConanException(f"e2e: no usable C compiler (tried: {', '.join(tried)})")

    def _writable_tmpdir(self):
        """返回可写的临时目录（鸿蒙目标机 /tmp 只读，E002）。"""
        cand = os.environ.get("TMPDIR")
        if cand and os.path.isdir(cand) and os.access(cand, os.W_OK):
            return cand
        fallback = os.path.join(self.build_folder, "build", "tmp")
        os.makedirs(fallback, exist_ok=True)
        return fallback

    # ───────────────────────── 编译消费者 ─────────────────────────

    def build(self):
        dep = self.dependencies[self.tested_reference_str]
        pkg = dep.package_folder
        info = dep.cpp_info.aggregated_components()

        cc = self._c_compiler()
        tmpdir = self._writable_tmpdir()
        work = os.path.join(self.build_folder, "build")
        os.makedirs(work, exist_ok=True)
        bin_path = os.path.join(work, "test_lib_consumer")

        cmd = [cc, "-std=gnu99",
               os.path.join(self.source_folder, "test_lib_consumer.c"),
               "-o", bin_path]
        for inc in info.includedirs:
            cmd += ["-I", inc]
        for libdir in info.libdirs:
            cmd += ["-L", libdir]
        for lib in (info.libs or ["thrulay"]):
            cmd.append(f"-l{lib}")
        cmd.append("-lm")  # libthrulay 的速率换算使用 libm

        self.output.info("compiling lib consumer: " + " ".join(cmd))
        # 编译/链接环境只注入 TMPDIR（见模块 docstring：绝不注入依赖库目录）
        build_env = Environment()
        build_env.define("TMPDIR", tmpdir)
        with build_env.vars(self).apply():
            subprocess.run(cmd, check=True)

    # ───────────────────────── 运行消费者 ─────────────────────────

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        pkg = dep.package_folder
        tmpdir = self._writable_tmpdir()

        # ---- [1/4] 产物契约 ----
        expect = [
            os.path.join(pkg, "bin", "thrulay"),
            # 上游 Makefile.am 把 thrulayd 装到 $(bindir)（实测 conan create 日志：
            # install -c 'thrulayd' '<pkg>/bin/thrulayd'），故与 thrulay 同目录
            os.path.join(pkg, "bin", "thrulayd"),
            os.path.join(pkg, "lib", "libthrulay.a"),
            os.path.join(pkg, "include", "thrulay", "client.h"),
            os.path.join(pkg, "include", "thrulay", "server.h"),
        ]
        missing = [p for p in expect if not os.path.isfile(p)]
        assert not missing, f"打包产物缺失: {missing}"
        for exe in (expect[0], expect[1]):
            assert os.access(exe, os.X_OK), f"可执行文件无执行权限: {exe}"
        self.output.info(f"产物契约通过（{len(expect)} 项）")

        # 端口按 PID 派生，避免并行 CI worker 互相抢占
        base = 53900 + (os.getpid() % 90)
        run_env = Environment()
        run_env.define("TMPDIR", tmpdir)

        # ---- [2/4] 库 API 消费者（真实测量 + 报告解析） ----
        lib_bin = os.path.join(self.build_folder, "build", "test_lib_consumer")
        with run_env.vars(self).apply():
            self.run(f'"{lib_bin}" "{os.path.join(tmpdir, "t_lib_consumer.log")}" {base}')

        # ---- [3/4] CLI 消费者（版本冒烟 + loopback 真实测量） ----
        script = os.path.join(self.source_folder, "test_cli_e2e.py")
        with run_env.vars(self).apply():
            self.run(f'"{sys.executable}" "{script}" "{pkg}" {base + 1}')

        # ---- [4/4] ----
        self.output.info("thrulay 消费者 e2e 全部通过（库 API + CLI 两层）")
