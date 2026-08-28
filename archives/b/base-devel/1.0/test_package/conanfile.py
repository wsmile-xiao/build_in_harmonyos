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
            # base-devel 是元包——依赖 gcc/autoconf/automake 的 bin 目录
            # 传给 test 脚本检查（执行命令的 PATH 传递不可靠实测）
            bins = []
            for dep_name, dep in self.dependencies.items():
                b = os.path.join(dep.package_folder, "bin")
                if os.path.isdir(b):
                    bins.append(b)
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_base_devel.py")
            self.run(f'{sys.executable} "{test_script}" '
                     f'"{os.pathsep.join(bins)}"', env="conanrun")
