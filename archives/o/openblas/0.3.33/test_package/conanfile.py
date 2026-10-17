import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 直接编译+链接（非 dlopen）：既 #include <cblas.h>/<lapacke.h>（依赖包的
        # include/），又链接 libopenblas（依赖包的 lib/）——CI 的 L1e 破坏性反向
        # 验证会把这两个目录整个移走再跑一次，两处都真实依赖才不会被判成假测试。
        dep = self.dependencies["openblas"].cpp_info
        inc = " ".join("-I" + p for p in dep.includedirs)
        libdir = dep.libdirs[0]
        cc = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict).get("c", "/data/service/hnp/bin/clang")
        self.run("{cc} test.c -o test_probe {inc} -L{ld} -Wl,-rpath-link,{ld} "
                 "-lopenblas -lm".format(cc=cc, inc=inc, ld=libdir))

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("{} -c './test_probe'".format(bash), env="conanrun")
