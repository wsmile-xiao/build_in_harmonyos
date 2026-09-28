import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        libdir = self.dependencies["libomptarget-rtl-amdgpu"].cpp_info.libdirs[0]
        so = os.path.join(libdir, "libomptarget.rtl.amdgpu.so")
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test.c -o test_probe -DTARGET_SO='\"{so}\"' -ldl")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
