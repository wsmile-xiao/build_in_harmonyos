import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # R33: 编译器从 conan conf 取
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        dep = self.dependencies["lbfgs"]
        inc = " ".join("-I" + p for p in dep.cpp_info.includedirs)
        # 直接链包内静态归档绝对路径（免 -L/-l 顺序问题）；system_libs=m → -lm
        lib = os.path.join(dep.package_folder, "lib", "liblbfgs.a")
        self.run(f"{cc} -O1 test_lbfgs.c {inc} {lib} -lm -o test_lbfgs")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译")
            return
        self.run("./test_lbfgs", env="conanrun")
