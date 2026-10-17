import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # R33: 编译器从 conan conf 取，不裸用 shell $CC
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        dep = self.dependencies["apriltag"].cpp_info
        inc = " ".join("-I" + p for p in dep.includedirs)
        libdir = dep.libdirs[0]
        # 消费者真用公开 API：头在 include/apriltag（includedirs 已指过去）
        self.run(
            f"{cc} test_apriltag.c -o test_apriltag {inc} "
            f"-L{libdir} -lapriltag -lm -lpthread -Wl,-rpath,{libdir}"
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        self.run("./test_apriltag", env="conanrun")
