import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["ballerburg"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_ballerburg.py")
            # L0d 门禁：test() 必须有 self.run()（纯 os 检查不算——
            # 'test() method has no self.run() call' 实测 #6625）——
            # self.run 运行 test_ballerburg.py（传 BALLERBURG_PACKAGE）
            self.run(
                f'BALLERBURG_PACKAGE="{pkg}" '
                f'{sys.executable} "{test_script}"',
                env="conanrun")
