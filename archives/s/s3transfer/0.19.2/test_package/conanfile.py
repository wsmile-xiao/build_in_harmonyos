import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # botocore 是 s3transfer 的依赖——test_package 也 requires（否则
        # self.dependencies["botocore"].package_folder 为 None——实测 TypeError）
        self.requires("botocore/1.43.78")

    def test(self):
        if can_run(self):
            pkg = self.dependencies["s3transfer"].package_folder
            # s3transfer 依赖 botocore 等——遍历依赖的 site-packages
            # 加 PYTHONPATH（import s3transfer 需 botocore）
            py_paths = [os.path.join(pkg, "lib", "python3")]
            for dep_name, dep in self.dependencies.items():
                if not dep.package_folder:
                    continue
                for sp in ("lib/python3.12/site-packages",
                           "lib/python3/site-packages", "lib/python3"):
                    p = os.path.join(dep.package_folder, sp)
                    if os.path.isdir(p):
                        py_paths.append(p)
                        break
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_s3transfer.py")
            self.run(
                f'PYTHONPATH="{os.pathsep.join(py_paths)}" '
                f'{sys.executable} "{test_script}" "{pkg}"',
                env="conanrun")
