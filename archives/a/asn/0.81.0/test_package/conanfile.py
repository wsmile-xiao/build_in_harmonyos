#!/usr/bin/env python3
"""Conan test_package for asn 0.81.0 — Bash script test.

Verifies that the asn command is installed and functional.
Runs test.sh which checks script existence, syntax, version, and usage output.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class AsnTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # Find bash for executing the test (OHOS may not have bash in default PATH).
            # 优先级: PATH 查找 → CONFIG_SHELL。
            # 注意: SHELL 环境变量不保证指向 bash（可能是 sh/zsh/dash），
            # 因此不作为回退，避免用非 bash 解释器执行 test.sh 导致语法错误。
            bash_path = shutil.which("bash") or os.environ.get("CONFIG_SHELL")
            if not bash_path:
                raise Exception("bash not found in PATH or CONFIG_SHELL")
            # Run test.sh smoke test (source file for CI L0c compliance)
            self.run(
                f'cd "{self.source_folder}" && '
                f'"{bash_path}" test.sh',
                env="conanrun"
            )
