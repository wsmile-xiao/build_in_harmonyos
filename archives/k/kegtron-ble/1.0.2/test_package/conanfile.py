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
            pkg = self.dependencies["kegtron-ble"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_kegtron_ble.py")
            # 沙箱 PATH 无 python3——绝对路径（同 packaging/rich 教训）
            self.run(f'{sys.executable} "{test_script}" "{pkg}"',
                     env="conanrun")
