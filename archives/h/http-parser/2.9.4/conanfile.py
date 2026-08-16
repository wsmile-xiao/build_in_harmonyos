#!/usr/bin/env python3
"""Conan recipe — http-parser 2.9.4 (nodejs/http-parser, Makefile 构建).

http-parser 是 Node.js 官方的 C HTTP 解析器：纯 Makefile、无 configure、
无外部依赖。`make package` 产出静态库 libhttp_parser.a，`make library`
产出共享库 libhttp_parser.so.2.9.4，`make test` 运行上游官方测试
（test_g strict + test_fast 两个二进制）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class HttpParserConan(ConanFile):
    name = "http-parser"
    version = "2.9.4"
    description = "HTTP request/response parser for C (nodejs/http-parser)"
    license = "MIT"
    homepage = "https://github.com/nodejs/http-parser"
    url = ""  # CI fills this

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
        self.folders.build = "."  # Makefile 在源码树内构建（无 configure）

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            self.fail("http-parser requires a POSIX host (Linux or OHOS)")
        apply_conandata_patches(self)
        # R33: 编译器/归档器从 Conan conf 获取，禁止裸用 shell 环境变量
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        # 静态对象加 -fPIC（CFLAGS_FAST_EXTRA），便于下游（restinio 等）链进共享库
        if self.options.shared:
            self.run(f"make -j1 CC={cc} AR={ar} CFLAGS_FAST_EXTRA=-fPIC library")
        else:
            self.run(f"make -j1 CC={cc} AR={ar} CFLAGS_FAST_EXTRA=-fPIC package")
        # 上游官方测试: make test → test_g(strict) + test_fast
        self.run(f"make -j1 CC={cc} AR={ar} CFLAGS_FAST_EXTRA=-fPIC test")

    def package(self):
        copy(self, "http_parser.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE-MIT", self.source_folder, os.path.join(self.package_folder, "licenses"))
        if self.options.shared:
            copy(self, "libhttp_parser.so*", self.source_folder, os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libhttp_parser.a", self.source_folder, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["http_parser"]
        self.cpp_info.set_property("pkg_config_name", "http-parser")
        self.cpp_info.set_property("cmake_file_name", "http_parser")
        self.cpp_info.set_property("cmake_target_name", "http_parser::http_parser")
