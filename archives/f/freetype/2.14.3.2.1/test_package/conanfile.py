import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["freetype"].cpp_info
        # freetype 头装在 include/freetype2/（ft2build.h + freetype/*.h）
        incs = ["-I" + p for p in dep.includedirs]
        libdir = dep.libdirs[0]
        cc = os.environ.get("CC", "clang")
        # 真实链接 libfreetype.so（非 dlopen 空壳），rpath 兜底运行期查找
        self.run(f"{cc} test.c -o test_probe {' '.join(incs)} "
                 f"-L{libdir} -lfreetype -Wl,-rpath,{libdir}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        dep = self.dependencies["freetype"].cpp_info
        libdir = dep.libdirs[0]
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # 显式 LD_LIBRARY_PATH，与 rpath 双保险
        self.run(f"{bash} -c 'LD_LIBRARY_PATH=\"{libdir}\":$LD_LIBRARY_PATH ./test_probe'",
                 env="conanrun")
