#!/usr/bin/env python3
"""Conan recipe for bytes 0.0.4 — clibs/bytes single-file C99 library (Makefile).

bytes 是纯 Makefile 项目：无 configure 脚本、无 make install 目标，
Makefile 只提供 `make test`（编译并运行 test.c）。因此配方使用自定义构建：
直接用 Conan conf 提供的编译器将 bytes.c 编译为静态库 libbytes.a，
并安装 bytes.h 头文件。上游 `make test` 作为测试入口在本配方外验证。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BytesConan(ConanFile):
    name = "bytes"
    version = "0.0.4"
    description = "bytes: byte string and number conversion utilities (clibs)"
    license = "MIT"
    homepage = "https://github.com/clibs/bytes"
    url = "https://github.com/clibs/bytes"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        ranlib = compilers.get("ranlib", "llvm-ranlib")
        # R33: 编译器来自 Conan conf，绝不依赖空 shell 环境变量
        self.run(f"{cc} -std=c99 -Wall -Wextra -fPIC -c bytes.c -o bytes.o")
        self.run(f"{ar} rcs libbytes.a bytes.o")
        self.run(f"{ranlib} libbytes.a")
        if self.options.shared:
            self.run(f"{cc} -std=c99 -shared -fPIC bytes.c -o libbytes.so")

    def package(self):
        copy(self, "bytes.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "libbytes.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            copy(self, "libbytes.so", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["bytes"]