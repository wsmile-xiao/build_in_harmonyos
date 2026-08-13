import os

from conan import ConanFile


class RoswellTestConan(ConanFile):
    """test_package for roswell — 运行 ros 二进制验证可执行性与版本 (R34)。"""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: 用 bash 包装二进制执行（/system/bin/sh 可能无法可靠执行 ELF）。
        # ROSWELL_HOME 由 test.sh 内部设置（鸿蒙 getpwuid() 无条目需绝对路径）。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
