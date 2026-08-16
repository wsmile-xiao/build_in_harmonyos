import os
import shutil
import sys

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    """palp 是**纯命令行工具包**（无库无头），故 test_package 不编译 C 探针，
    而是让 `test.py` 直接跑真程序、拿上游测试套里的期望值对账。

    断言逻辑单独放在 `test.py` 里（不塞进本文件）：它可以脱离 conan 独立跑
    `python3 test.py <bin目录>`，排查时不用先起一遍 conan create。
    """
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
        bindir = os.path.join(dep.package_folder, "bin")
        script = os.path.join(self.source_folder, "test.py")
        # 绝对路径调 python：这份 musl 上的 exec 不做 PATH 查找，裸名会 ENOENT
        py = sys.executable or shutil.which("python3") or "/data/service/hnp/bin/python3"
        self.run('"%s" "%s" "%s"' % (py, script, bindir), env="conanrun")
