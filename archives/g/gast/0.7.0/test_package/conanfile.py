import os

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["gast"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_gast.py")
            # 沙箱 PATH 无 python3——绝对路径（同 packaging 教训）
            import sys
            py = "/data/service/hnp/bin/python3" \
                if os.path.isfile("/data/service/hnp/bin/python3") \
                else sys.executable
            self.run(f'{py} "{test_script}" "{pkg}"', env="conanrun")
