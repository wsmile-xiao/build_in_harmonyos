import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["cairomm"].cpp_info
        # 头闭包自检：带上所有依赖的 include（cairomm 头会 #include <cairo.h>、<sigc++/...>）。
        incs = []
        libs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
            libs += ["-L" + d for d in _d.cpp_info.libdirs]
        inc = " ".join(incs)
        link = " ".join(libs)
        libdir = dep.libdirs[0]
        so = os.path.join(libdir, "libcairomm-1.16.so")
        cxx = os.environ.get("CXX", "clang++")
        # R03 首错修复：原命令缺 -L/-lcairomm-1.16 导致 ld.lld undefined symbol。
        self.run(f"{cxx} -std=c++17 test_cairomm.cpp -o test_probe {inc} {link} -lcairomm-1.16 -DTARGET_SO='\"{so}\"' -ldl")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
