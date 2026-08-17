import os
import shutil
import sys

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    """Maxima 的可用性有两层，必须都验：命令行能算，且 maxima.fas 真的能被 ECL 加载
    （后者是 passagemath-ecl/-maxima 的实际用法）。断言在 test.py 里。"""
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
        ecl = self.dependencies["ecl"]
        script = os.path.join(self.source_folder, "test.py")
        py = sys.executable or shutil.which("python3") or "/data/service/hnp/bin/python3"
        libdirs = []
        for _ref, _d in self.dependencies.items():
            base = getattr(_d, "package_folder", None) or ""
            for p in (_d.cpp_info.libdirs or []):
                libdirs.append(p if os.path.isabs(p) else os.path.join(base, p))
        ldpath = os.pathsep.join(dict.fromkeys(libdirs))
        self.run('LD_LIBRARY_PATH="%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "%s" "%s" "%s" "%s"'
                 % (ldpath, py, script, dep.package_folder, ecl.package_folder), env="conanrun")
