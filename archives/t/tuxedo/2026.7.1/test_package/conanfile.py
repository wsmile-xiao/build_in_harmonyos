#!/usr/bin/env python3
"""Conan consumer test for tuxedo 2026.7.1 (Rust application package).

实质验证（R34）：直接执行打包产出的 `tuxedo` 二进制，覆盖
  - `--version` 输出版本号
  - `--help` 输出帮助文本
  - todo.txt CLI 子命令 add/list/done（带 TODO_FILE 指向临时文件），
    验证 headless 读写路径真实工作。
测试脚本输出 HMBS_TEST_PACKAGE_RESULT 断言计数，失败即退出码非 0。
"""

import os
import shlex
import subprocess
import sys
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class TuxedoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["tuxedo"].package_folder
        exe = os.path.join(package_folder, "bin", "tuxedo")
        if not os.path.isfile(exe):
            raise AssertionError(f"Missing tuxedo executable: {exe}")

        if not can_run(self):
            self.output.info("Cross-building: verified package layout only.")
            return

        script = os.path.join(self.source_folder, "test_tuxedo.sh")
        result = self.run(
            f'bash {shlex.quote(script)} {shlex.quote(exe)}',
            env="conanrun",
            ignore_errors=True,
        )
        if result != 0:
            raise AssertionError(
                f"tuxedo test_package failed (rc={result})"
            )

    def export_sources(self):
        self.copy("test_tuxedo.sh")
