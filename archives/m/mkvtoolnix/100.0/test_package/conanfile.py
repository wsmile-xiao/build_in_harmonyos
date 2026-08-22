import os

from conan import ConanFile


class MkvtoolnixTestConan(ConanFile):
    """test_package for mkvtoolnix — 运行 mkvmerge --version 验证可执行文件（R34）。"""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) 不能直接执行 ELF，用 bash 包装。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
