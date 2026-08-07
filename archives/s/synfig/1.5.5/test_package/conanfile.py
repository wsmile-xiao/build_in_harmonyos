# test_package/conanfile.py — synfig 1.5.5 (CLI tool)
# Conan L1 测试：在 conanrun 环境下运行 test.sh，真实执行 bin/synfig（R34）。
import os

from conan import ConanFile


class SynfigTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) 无法执行 ELF 二进制，用 bash 包装执行。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
