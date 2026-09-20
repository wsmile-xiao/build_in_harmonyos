import os
from conan import ConanFile
from conan.tools.build import cross_building


class LapackeTestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 直接编译+链接（非 dlopen）：既 #include <lapacke.h>（本包 include/），
        # 又链接本包 liblapacke.a 与依赖 lapack/3.12.1 的 liblapack/libblas/
        # Fortran 运行时静态库。CI 的 L1e 破坏性反向验证会把相关目录整个移走
        # 再跑一次，两处都真实依赖才不会被判成假测试。
        dep = self.dependencies["lapacke"].cpp_info
        lap = self.dependencies["lapack"].cpp_info
        inc = " ".join("-I" + p for p in dep.includedirs)
        libdirs = " ".join("-L" + p for p in list(dep.libdirs) + list(lap.libdirs))
        cc = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict).get("c", "/data/service/hnp/bin/clang")
        self.run("{cc} test.c -o test_probe {inc} {libdirs} "
                 "-llapacke -llapack -lblas -lFortranRuntime -lFortranDecimal -lm"
                 .format(cc=cc, inc=inc, libdirs=libdirs))

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("{} -c './test_probe'".format(bash), env="conanrun")
