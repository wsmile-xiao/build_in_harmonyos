import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["tcl"].cpp_info
        inc = " ".join("-I" + d for d in dep.includedirs)
        libdir = dep.libdirs[0]
        so = os.path.join(libdir, "libtcl9.0.so")
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test.c -o test_probe {inc} -DTARGET_SO='\"{so}\"' -ldl")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        if False:
            self.output.info("skip_test_run：GUI/app 库只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
