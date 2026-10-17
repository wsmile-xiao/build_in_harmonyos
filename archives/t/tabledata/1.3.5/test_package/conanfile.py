import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # tabledata 依赖 dataproperty/typepy——test_package 也显式 requires
        # （否则 self.dependencies["dataproperty"/"typepy"] 可能为 None——
        # R34 的 PYTHONPATH 失败实测，dataproperty 模板同法）
        self.requires("dataproperty/1.1.1")
        self.requires("typepy/2.0.0")

    def test(self):
        if can_run(self):
            pkg = self.dependencies["tabledata"].package_folder
            # tabledata 依赖 dataproperty/typepy/mbstrdecoder/chardet——
            # 遍历依赖的 site-packages 全加 PYTHONPATH（逐个加易漏——
            # 实测 mbstrdecoder/chardet 缺；package_folder 为 None 的依赖
            # （build/tool 依赖）跳过）
            py_paths = [os.path.join(pkg, "lib", "python3")]
            for dep_name, dep in self.dependencies.items():
                if dep.package_folder is None:
                    continue
                for sp in ("lib/python3.12/site-packages",
                           "lib/python3/site-packages", "lib/python3"):
                    p = os.path.join(dep.package_folder, sp)
                    if os.path.isdir(p):
                        py_paths.append(p)
                        break
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_tabledata.py")
            self.run(
                f'PYTHONPATH="{os.pathsep.join(py_paths)}" '
                f'{sys.executable} "{test_script}" "{pkg}"',
                env="conanrun")
