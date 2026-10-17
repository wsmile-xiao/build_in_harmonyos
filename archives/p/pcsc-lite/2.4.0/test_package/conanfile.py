import os
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["pcsc-lite"].cpp_info
        # R34/L1e：显式校验包内产物路径，确保 test 真实依赖被测包
        # （OHOS SDK sysroot 自带 winscard 相关头文件时，若不校验路径会误用系统头）
        inc = " ".join("-I" + p for p in dep.includedirs)
        if not any(os.path.isdir(p) for p in dep.includedirs):
            raise ConanException(f"pcsc-lite package include dir missing: {dep.includedirs}")
        libdir = dep.libdirs[0]
        if not os.path.isdir(libdir):
            raise ConanException(f"pcsc-lite package lib dir missing: {libdir}")
        # R33: 编译器从 Conan conf 获取
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # 调用被测包真实 API（SCardEstablishContext/SCardListReaders），链接 -lpcsclite
        self.run(f"{cc} test.c -o test_probe {inc} -L{libdir} -lpcsclite")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
