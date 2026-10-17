#!/usr/bin/env python3
"""Conan test_package — vzlogger 0.8.9 (application smoke test).

vzlogger is a command-line daemon; the L1 consumer check runs the installed
binary and asserts version/help output via verify_vzlogger.py (R34 真实内容
断言)。守护进程本身为长运行，完整 -c 运行由上游单元测试覆盖（避免 CI 挂起）。
"""
import os

from conan import ConanFile


class VzloggerTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "verify_vzlogger.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(self.dependencies["vzlogger"].package_folder, "bin")
        vzlogger = os.path.join(bin_dir, "vzlogger")
        # 冒烟断言：--version 含 0.8.9、--help 含协议列表头
        # env="conanrun" 注入依赖库的 LD_LIBRARY_PATH，否则 verify_vzlogger.py
        # 的 subprocess 找不到 vzlogger 动态依赖（CI 实测退出码 127）
        self.run(f"python3 verify_vzlogger.py {vzlogger}", env="conanrun")
