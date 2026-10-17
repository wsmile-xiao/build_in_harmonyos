import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 直接编译+链接（非 dlopen）：既 #include <lapacke.h>（依赖包 include/），
        # 又链接 liblapacke64/liblapack64/libblas64 + 随包 flang 运行时归档
        # （依赖包 lib/）。CI 的 L1e 破坏性反向验证会把这两个目录整个移走
        # 再重跑，两处都真实依赖才不会被判假测试。
        # 宏口径取自 cpp_info.defines（LAPACK_ILP64/HAVE_LAPACK_CONFIG_H），
        # 与库内一致——否则 lapack_int 退回 int32，测试自身就会失败。
        dep = self.dependencies["lapacke64"].cpp_info
        inc = " ".join("-I" + p for p in dep.includedirs)
        defs = " ".join("-D" + d for d in dep.defines)
        libdir = dep.libdirs[0]
        cc = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict).get("c", "/data/service/hnp/bin/clang")
        self.run("{cc} test.c -o test_probe {defs} {inc} -L{ld} -Wl,-rpath-link,{ld} "
                 "-llapacke64 -llapack64 -lblas64 -lFortranRuntime -lFortranDecimal -lm"
                 .format(cc=cc, defs=defs, inc=inc, ld=libdir))

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        self.run("./test_probe", cwd=self.build_folder)
