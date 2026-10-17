import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # R33: 编译器从 conan conf 取，不裸用 shell $CXX
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        dep = self.dependencies["darts-clone"].cpp_info
        inc = " ".join("-I" + p for p in dep.includedirs)
        self.run(f"{cxx} -std=c++11 test_darts.cpp -o test_darts {inc}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        self.run("./test_darts", env="conanrun")
