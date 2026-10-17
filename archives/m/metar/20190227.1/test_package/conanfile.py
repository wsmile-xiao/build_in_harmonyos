#!/usr/bin/env python3
"""Conan test_package — metar 20190227.1 (CLI tool, 全离线可判)."""

import os

from conan import ConanFile


class MetarTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS 的 /system/bin/sh (mksh) 不能执行 ELF 派生的子进程链，用 profile 里
        # CONFIG_SHELL 指向的 bash 包一层（同 archives/d/dirb/2.22/test_package）。
        # VirtualRunEnv 负责把 metar 与依赖 libcurl.so 放进 PATH/LD_LIBRARY_PATH。
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} test.sh", env="conanrun")
