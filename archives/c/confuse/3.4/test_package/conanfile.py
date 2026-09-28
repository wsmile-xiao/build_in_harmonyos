import os
from conan import ConanFile
from conan.tools.build import cross_building


class ConfuseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        incs = []
        libdirs = []
        libs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
            libdirs += _d.cpp_info.libdirs
            libs += ["-l" + l for l in _d.cpp_info.libs]
        cc = os.environ.get("CC", "clang")
        link = " ".join(["-L" + p for p in libdirs] + libs
                        + ["-Wl,-rpath," + p for p in libdirs])
        self.run(f"{cc} test_confuse.c -o test_confuse {' '.join(sorted(set(incs)))} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_confuse'", env="conanrun")
