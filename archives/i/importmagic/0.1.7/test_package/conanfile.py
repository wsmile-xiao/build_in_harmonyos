import os
import sys
from conan import ConanFile


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # 获取包的 site-packages 路径
        dep = self.dependencies["importmagic"]
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_pkgs = os.path.join(dep.package_folder, "lib", py_ver, "site-packages")
        # 验证模块可导入
        self.run(
            f'{bash} -c "PYTHONPATH={site_pkgs}:$PYTHONPATH '
            f'python3 -c \'import importmagic; print(importmagic.__version__)\'"',
            env="conanrun",
        )
