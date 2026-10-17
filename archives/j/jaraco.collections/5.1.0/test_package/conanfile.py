import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies[self.tested_reference_str].package_folder
            # 运行期依赖 more-itertools 的 site-packages 也要在路径上
            # （jaraco.text / jaraco.functools 都 import more_itertools）
            mi = self.dependencies["more-itertools"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "check_collections.py")
            self.run(f'{sys.executable} "{test_script}" "{pkg}" "{mi}"',
                     env="conanrun")
