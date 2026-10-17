import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # typepy 是 dataproperty 的依赖——test_package 也 requires（否则
        # self.dependencies["typepy"] 为 None——R34 的 PYTHONPATH 失败实测）
        self.requires("typepy/2.0.0")

    def test(self):
        if can_run(self):
            pkg = self.dependencies["dataproperty"].package_folder
            # dataproperty 依赖 typepy/mbstrdecoder/chardet——遍历依赖的
            # site-packages 全加 PYTHONPATH（逐个加易漏——实测 mbstrdecoder 缺）
            py_paths = [os.path.join(pkg, "lib", "python3")]
            for dep_name, dep in self.dependencies.items():
                for sp in ("lib/python3.12/site-packages",
                           "lib/python3/site-packages", "lib/python3"):
                    p = os.path.join(dep.package_folder, sp)
                    if os.path.isdir(p):
                        py_paths.append(p)
                        break
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_dataproperty.py")
            self.run(
                f'PYTHONPATH="{os.pathsep.join(py_paths)}" '
                f'{sys.executable} "{test_script}" "{pkg}"',
                env="conanrun")
