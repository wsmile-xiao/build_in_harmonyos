import os
import shutil
import sys

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    """tachyon 是**纯命令行工具包**（无库无头），test_package 不编译 C 探针，
    而是让 `test.py` 渲染一张图并对产物做字节级断言（见该文件的模块注释）。

    断言逻辑单独放在 `test.py` 里：它能脱离 conan 独立跑
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
        py = sys.executable or shutil.which("python3") or "/data/service/hnp/bin/python3"

        # **必须显式给 LD_LIBRARY_PATH**：本包只是个可执行文件，DT_NEEDED 写着
        # libpng16.so.16 而包里不带 rpath（rpath 该由最终消费方决定：wheel 会把
        # libpng 内嵌进 <dist>.libs 并指 $ORIGIN/../../）。设备默认搜索路径里没有
        # 这个库，不给路径时报的不是 "Error loading shared library" 而是一串
        # `png_set_IHDR: symbol not found` —— 措辞看着像版本不对，其实是**没找到**。实撞。
        libdirs = []
        for _ref, _d in self.dependencies.items():
            base = getattr(_d, "package_folder", None) or ""
            for p in (_d.cpp_info.libdirs or []):
                libdirs.append(p if os.path.isabs(p) else os.path.join(base, p))
        ldpath = os.pathsep.join(dict.fromkeys(libdirs))
        self.run('LD_LIBRARY_PATH="%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "%s" "%s" "%s"'
                 % (ldpath, py, script, bindir), env="conanrun")
