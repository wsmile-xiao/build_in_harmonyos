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
        # datatype99 自身 cpp_info.includedirs 不含传递依赖 metalang99 的
        # 头目录（CI #44038 实测 'metalang99.h' file not found）——遍历整个
        # 依赖图聚合 includedirs（datatype99 + metalang99）。
        incs = []
        for _, dep in self.dependencies.items():
            incs.extend("-I" + p for p in dep.cpp_info.includedirs)
        inc = " ".join(incs)
        self.run(f"{cc} -std=c99 test_datatype99.c -o test_datatype99 {inc}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译")
            return
        self.run("./test_datatype99", env="conanrun")
