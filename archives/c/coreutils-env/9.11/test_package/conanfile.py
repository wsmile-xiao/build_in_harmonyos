#!/usr/bin/env python3
"""test_package for coreutils-env — runs test.sh which invokes the env binary."""
import os

from conan import ConanFile


class CoreutilsEnvTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def configure(self):
        # OHOS profile 携带 os.version=6.0；本包不依赖其值，移除避免 Invalid ID
        self.settings.rm_safe("os.version")

    def test(self):
        # OHOS: use bash to wrap binary execution
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
