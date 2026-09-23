import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class BtiTestConan(ConanFile):
    """test_package for bti 034 — 真实执行被测包安装的 bin/bti。

    实际断言在 test.sh（POSIX sh）里，见该文件顶部说明。
    """
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        bti = os.path.join(self.dependencies["bti"].package_folder,
                           "bin", "bti")
        script = os.path.join(self.source_folder, "test.sh")
        self.run('/bin/sh "{}" "{}"'.format(script, bti), env="conanrun")
