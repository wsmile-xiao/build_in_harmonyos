#!/usr/bin/env python3
"""Run dnsperf/resperf help, argument validation and error-path checks."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class DnsperfTestConan(ConanFile):
    # 该 OHOS 适配版 conan 不接受在 recipe settings 中显式声明 os.version
    # （由 profile 自动注入），与基线 afdko 4.0.1 test_package 保持一致
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        bindir = os.path.join(self.dependencies["dnsperf"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test_dnsperf.sh")
        # VirtualRunEnv 生成的 conanrun 环境提供依赖共享库的
        # LD_LIBRARY_PATH（运行时加载器默认路径找不到 conan cache 中的 .so）
        self.run(
            f'sh "{script}" "{bindir}"',
            env="conanrun",
        )
