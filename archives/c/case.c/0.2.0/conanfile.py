#!/usr/bin/env python3
"""Conan recipe — case.c 0.2.0 (Makefile project).

case.c 是纯 Makefile 的 C 库（MIT）：src/case.h + src/case.c。
上游 Makefile 只有 `test` 目标（无 configure、无 install 目标），
因此 build() 直接编译静态库并手动安装头文件与库文件。

要点：
- R33: 编译器从 Conan conf 获取，禁止裸用 ${CC}/${CFLAGS}（CI worker 上为空）
- R9: 用 -j1 保证可复现构建
- OHOS profile 已提供 aarch64 clang toolchain（os=OHOS, arch=armv8）
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CaseCConan(ConanFile):
    name = "case.c"
    version = "0.2.0"
    description = "case.c — string case conversion (lower/upper/camel) in C, MIT licensed"
    license = "MIT"
    homepage = "https://github.com/stephenmathieson/case.c"
    url = "https://github.com/stephenmathieson/case.c"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        # 纯 Makefile 项目：in-source 构建
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: 编译器从 Conan conf 获取（dict 形式，conan 2.29.1 兼容）
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        ranlib = compilers.get("ranlib", "llvm-ranlib") if compilers else "llvm-ranlib"
        # 编译静态库 libcase.a（含上游 13 个独立用例测试，随后执行）
        self.run(
            f"{cc} -std=c99 -O2 -c src/case.c -o case.o"
        )
        self.run(
            f"{ar} rcs libcase.a case.o"
        )
        if ranlib:
            self.run(f"{ranlib} libcase.a")
        # 构建并运行上游测试（补丁后 13 个独立用例全部注册）
        self.run(
            f"{cc} -std=c99 test.c src/case.c -o test_case"
        )
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        self.run(f"{bash} -c './test_case'", env="conanrun")

    def package(self):
        # 手动安装：头文件 + 静态库
        copy(self, "case.h", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "include"))
        copy(self, "libcase.a", self.source_folder,
             os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["case"]