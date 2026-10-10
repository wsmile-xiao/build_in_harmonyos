import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["liblksctp"].cpp_info
        incs = " ".join("-I" + p for p in dep.includedirs)
        libdir = dep.libdirs[0]
        cc = os.environ.get("CC", "clang")
        # 直接链接 libsctp（-lsctp）：既验头闭包，也验 SONAME 与符号导出。
        self.run(f"{cc} test.c -o test_probe {incs} -L{libdir} -lsctp")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
