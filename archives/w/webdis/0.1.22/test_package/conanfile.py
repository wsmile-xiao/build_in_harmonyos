#!/usr/bin/env python3
"""Conan test_package — webdis 0.1.22 (HarmonyOS PC / aarch64).

由 `conan create` 触发，测试**真实执行**被测包（R34）：两套 python unittest 用例均在 conanrun 环境下
用 conan 自身的解释器运行，直接拉起 `bin/webdis` 二进制并在其上做真实交互：

  test_consumer.py     5 个用例 —— 安装后消费者视角：启动、/crossdomain.xml 契约、$TMPDIR 日志落盘、
                       Redis 不可用时的真实响应（503）、SIGTERM 生命周期
  test_webdis_ohos.py 16 个用例 —— HarmonyOS 平台契约（ELF64/AArch64/PIE、musl 加载器、无 glibc、
                       不可执行栈、无宿主构建路径）+ 真实 redis-server / WebSocket / 流式订阅端到端
"""
import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class WebdisTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # 端到端层需要真实 Redis：redis/6.2 与上游 CI 的 sidecar（redis:6.2.1-alpine）对应
        self.tool_requires("redis/6.2")

    def layout(self):
        basic_layout(self)

    def test(self):
        webdis_bin = os.path.join(
            self.dependencies["webdis"].package_folder, "bin", "webdis"
        )
        redis_dep = self.dependencies.build["redis"]
        bindirs = redis_dep.cpp_info.bindirs or ["bin"]
        redis_bin_dir = os.path.join(redis_dep.package_folder, bindirs[0])
        # 用运行 conan 的解释器，CI 环境必然存在
        python = sys.executable or "python3"
        for suite in ("test_consumer.py", "test_webdis_ohos.py"):
            self.run(
                f'"{python}" "{os.path.join(self.source_folder, suite)}" '
                f'"{webdis_bin}" "{redis_bin_dir}"',
                env="conanrun",
            )
