import os
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["zlib"].cpp_info
        # R34/L1e：OHOS SDK sysroot 自带 zlib.h/libz.so，若不显式校验包内产物
        # 路径，CI 破坏性负测试（移走包产物后重跑 conan test）会 fallback 到
        # 系统库编译通过，误判为"假测试"。显式校验确保 test 真实依赖被测包。
        for p in dep.includedirs:
            if not os.path.isdir(p):
                raise ConanException(f"zlib package include dir missing: {p}")
        libdir = dep.libdirs[0]
        if not os.path.isdir(libdir):
            raise ConanException(f"zlib package lib dir missing: {libdir}")
        inc = " ".join("-I" + p for p in dep.includedirs)
        # R33: 编译器从 Conan conf 获取，与配方本体保持一致
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # 静态 libz.a：编译 + 静态链接 + 运行，验证 -fPIC 对象可用且符号完整。
        self.run(f"{cc} test.c -o test_probe {inc} -L{libdir} -lz")
        # 鸿蒙特有测试：libz.a 为 PIC，可被共享库吸收（非 PIC 会在此链接期报 R_AARCH64）。
        self.run(f"{cc} -shared -fPIC ohos_pic_probe.c -o libz_ohos_probe.so {inc} -L{libdir} -lz")
        # 鸿蒙特有测试：__OHOS__ / HarmonyOS 运行时 / 真实 API 往返 / PIC 探针 dlopen。
        self.run(f"{cc} test_ohos.c -o test_ohos {inc} -L{libdir} -lz -ldl")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
        self.run(f"{bash} -c './test_ohos ./libz_ohos_probe.so'", env="conanrun")
