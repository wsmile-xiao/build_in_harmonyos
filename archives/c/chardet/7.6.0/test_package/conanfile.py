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
            python_exe = sys.executable
            py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
            # PYTHONPATH 注入所有依赖的 site-packages（chardet 零依赖——
            # 遍历 dependencies 通用——同 mbstrdecoder 先例）
            sites = []
            for _dep in self.dependencies.values():
                _site = os.path.join(_dep.package_folder, "lib", py_ver,
                                     "site-packages")
                if os.path.isdir(_site):
                    sites.append(_site)
            site_path = os.pathsep.join(sites)
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_chardet.py")
            # cd 到无源码目录（无 chardet 源码干扰——同 mbstrdecoder 先例）
            self.run(f'cd /data/storage/el2/base/cache && '
                     f'PYTHONPATH="{site_path}" {python_exe} "{test_script}"',
                     env="conanrun")
