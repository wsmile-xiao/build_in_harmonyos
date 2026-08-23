#!/usr/bin/env python3
"""Run bas55 version check, a sample BASIC program, and negative tests."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class Bas55TestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        bindir = os.path.join(self.dependencies["bas55"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test_bas55.sh")
        # bas55 仅依赖系统 libc（动态链接），无 conan cache .so 依赖，
        # 无需 conanrun 环境；不传 env 参数，避免 conanbuild/conanrun
        # shell wrapper 在 HMDFS 上的 getcwd 缺陷
        self.run(f'"/bin/sh" "{script}" "{bindir}"')
