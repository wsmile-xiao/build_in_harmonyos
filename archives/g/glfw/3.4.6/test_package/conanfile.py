import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["glfw"].cpp_info
        inc = " ".join("-I" + d for d in dep.includedirs)
        libdir = dep.libdirs[0]
        so = os.path.join(libdir, "libglfw.so")
        cc = os.environ.get("CC", "clang")
        # 链接 libglfw 使测试真正依赖被测包 (R34)，-Wl,--allow-shlib-undefined 容忍 bridge 循环依赖
        self.run(f"{cc} test.c -o test_probe {inc} -L{libdir} -lglfw -Wl,--allow-shlib-undefined -DTARGET_SO='\"{so}\"' -ldl")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
