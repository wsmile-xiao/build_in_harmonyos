#!/usr/bin/env python3
"""Run tt++ version check and the upstream validate self-test suite."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class TintinTestConan(ConanFile):
    # 该 OHOS 适配版 conan 不接受在 recipe settings 中显式声明 os.version
    # （由 profile 自动注入），与基线 afdko 4.0.1 test_package 保持一致
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        bindir = os.path.join(self.dependencies["tintin"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test_tintin.sh")
        # tt++ 静态链接 zlib/pcre2，无 conan cache .so 依赖，无需 conanrun
        # 环境；不传 env 参数，避免 conanbuild/conanrun shell wrapper 在
        # HMDFS 上的 getcwd 缺陷
        self.run(f'"/bin/sh" "{script}" "{bindir}"')
