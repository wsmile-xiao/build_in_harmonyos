#!/usr/bin/env python3
"""Test package — aiven-client 4.16.0 (R34 实质性测试).

Smoke tests covering the core public API of aiven-client:
- 模块导入 + __version__
- AivenClient 类存在
- argx.CommandLineTool 基础命令行机制
- pretty 表格格式化
- speller 拼写建议
- cli.AivenCLI 入口

不依赖 pytest — 使用 python3 -c for each test.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class AivenClientTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["aiven-client"]
        if not can_run(self):
            self.output.info("Cross-build context: packaged aiven-client verified; runtime test skipped")
            return
        bash = self._find_bash()
        self.run(f'"{bash}" test.sh', env="conanrun")

    def _find_bash(self):
        candidates = [
            os.environ.get("CONFIG_SHELL"),
            shutil.which("bash"),
            "/data/service/hnp/bin/bash",
            "/bin/bash",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise RuntimeError("bash executable is required to run the aiven-client test_package")
