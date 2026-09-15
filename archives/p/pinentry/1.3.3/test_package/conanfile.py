#!/usr/bin/env python3
"""Conan test_package — pinentry 1.3.3

两级验证：
  L1  C 探针（test_pinentry.c）：真实执行 bin/pinentry-curses、bin/pinentry-tty
      的 --version 并断言版本号（R34 反空壳）。
  L2  run_upstream_tests.py：驱动**上游真实对外接口**（gpg-agent 用的 Assuan 协议）
      做功能测试 —— 16 项断言（握手/GETINFO/错误处理/GETPIN/CONFIRM/MESSAGE），
      覆盖两个前端。

为什么 L2 不用 `make check`：pinentry 1.3.3 官方 tarball **不含 tests/ 目录**
（实测 tar 内 test 条目 0 条、SUBDIRS 无 tests、无 TESTS= 定义）→ `make check`
是 no-op。故改测上游真实接口。
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class PinentryTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # L1: 现场编译消费者探针
        test_src = os.path.join(self.source_folder, "test_pinentry.c")
        test_bin = os.path.join(self.build_folder, "test_pinentry")
        self.run(f'clang "{test_src}" -o "{test_bin}"')

    def test(self):
        if not can_run(self):
            return

        # L1: R34 —— 真实执行被测包的二进制
        test_bin = os.path.join(self.build_folder, "test_pinentry")
        self.run(f'"{test_bin}"', env="conanrun")

        # L2: 上游接口功能测试（Assuan 协议）
        # Conan 2 的 self.run() 不返回输出 → 重定向到文件后再读（不能用 devnull）
        script = os.path.join(self.source_folder, "run_upstream_tests.py")
        bin_dir = self.dependencies[self.tested_reference_str].cpp_info.bindirs[0]
        log = os.path.join(self.build_folder, "upstream_tests.log")
        self.run(f'python3 "{script}" --bindir "{bin_dir}" > "{log}" 2>&1',
                 env="conanrun")
        with open(log, encoding="utf-8", errors="replace") as f:
            result = f.read()
        # 即使断言失败，也应让日志可见（便于 CI 定位）
        self.output.info(result.strip()[-2000:])
        m = re.search(r"RESULT: passed=(\d+) failed=(\d+) skipped=(\d+)", result)
        if not m:
            raise ConanException("pinentry: 未取得上游接口测试汇总行")
        passed, failed, skipped = (int(m.group(i)) for i in (1, 2, 3))
        self.output.info(
            f"pinentry 上游接口测试: passed={passed} failed={failed} skipped={skipped}")
        # 绝不把"跑不了"当"通过"（R34）：失败即失败，跳过须可见
        if failed:
            raise ConanException(f"pinentry: 上游接口测试有 {failed} 项失败")
        if skipped:
            self.output.warning(
                f"pinentry: {skipped} 项因终端/terminfo 不可用而跳过（环境限制，未计为通过）")
        if passed == 0:
            raise ConanException("pinentry: 上游接口测试 0 项通过")

