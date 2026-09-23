import os
import shutil
import sys

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    """gengen 产的是"生成器类源码"，必须真跑一遍 生成→编译→执行 断言闭环。"""
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv", "VirtualBuildEnv"
    exports_sources = "test.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：跳过运行")
            return
        dep = self.dependencies[self.tested_reference_str.split("/")[0]]
        script = os.path.join(self.source_folder, "test.py")
        py = sys.executable or shutil.which("python3") or "/data/service/hnp/bin/python3"
        self.run('"%s" "%s" "%s"' % (py, script, os.path.join(dep.package_folder, "bin", "gengen")),
                 env="conanrun")
