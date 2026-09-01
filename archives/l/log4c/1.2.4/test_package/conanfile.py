import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["log4c"].cpp_info
        # Collect include dirs from all dependencies (log4c headers use <log4c/...> paths).
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libdirs = " ".join("-L" + p for p in dep.libdirs)
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test_log4c.c -o test_log4c {inc} {libdirs} -llog4c")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: skip runtime test")
            return
        self.run("./test_log4c", env="conanrun")
