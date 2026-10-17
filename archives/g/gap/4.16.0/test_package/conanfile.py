import os
import shutil
import sys

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    """GAP 的可用性只有**把系统跑起来**才验得了：库能链接不代表 GAP root 与包装齐了。
    断言逻辑在 test.py 里（可脱离 conan 独立跑 `python3 test.py <包根>`）。"""
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
        libdirs = []
        for _ref, _d in self.dependencies.items():
            base = getattr(_d, "package_folder", None) or ""
            for p in (_d.cpp_info.libdirs or []):
                libdirs.append(p if os.path.isabs(p) else os.path.join(base, p))
        ldpath = os.pathsep.join(dict.fromkeys(libdirs))
        self.run('LD_LIBRARY_PATH="%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "%s" "%s" "%s"'
                 % (ldpath, py, script, dep.package_folder), env="conanrun")
