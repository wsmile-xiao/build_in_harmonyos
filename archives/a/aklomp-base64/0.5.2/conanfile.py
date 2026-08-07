#!/usr/bin/env python3
"""Conan recipe — aklomp-base64 0.5.2 (Makefile).

Fast Base64 stream encoder/decoder in C99 with optional SIMD codecs.
Pure libc, no external dependencies. Static library only.
"""
from conan import ConanFile
from conan.tools.files import get, copy
from conan.errors import ConanInvalidConfiguration

from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class Base64Conan(ConanFile):
    name = "aklomp-base64"
    version = "0.5.2"
    package_type = "library"

    description = "Fast Base64 stream encoder/decoder (C99, libc-only)"
    homepage = "https://github.com/aklomp/base64"
    license = "BSD-2-Clause"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}


    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        # R26: 静态库（Makefile 只出 .a），shared=True 无效
        if self.options.shared:
            raise ConanInvalidConfiguration("aklomp-base64 is static-only (R26)")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # 上游 Makefile：make lib/libbase64.o 产出单个自包含对象文件。
        # OHOS 无 cc，必须显式 CC=clang；仅 aarch64 开启 NEON64
        # （原生 SIMD，让 test_base64 跑 NEON64 codec 测试组而非全 skip）。
        neon_cflags = "-march=armv8-a" if str(self.settings.arch).startswith("armv8") else ""
        make_cmd = "make lib/libbase64.o CC=clang"
        if neon_cflags:
            make_cmd += f" NEON64_CFLAGS={neon_cflags}"
        self.run(make_cmd, cwd=self.source_folder)
        # 单对象文件打包为静态库 libbase64.a
        self.run("ar rcs libbase64.a lib/libbase64.o", cwd=self.source_folder)
        # 上游 test/ 目录测试编译验证（test_base64 + benchmark）。
        # 注：OHOS CI 沙箱禁止执行 build 目录二进制（Operation not permitted），
        # 运行时验证在真机 PTY 完成，通过率见 PR_DESCRIPTION。
        test_cmd = "make -C test test_base64 benchmark CC=clang"
        if neon_cflags:
            test_cmd += f" NEON64_CFLAGS={neon_cflags}"
        self.run(test_cmd, cwd=self.source_folder)

    def package(self):
        copy(self, "libbase64.a", src=self.source_folder, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "include/libbase64.h", src=self.source_folder, dst=self.package_folder)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "aklomp-base64")
        self.cpp_info.set_property("cmake_target_name", "aklomp-base64::aklomp-base64")
        self.cpp_info.libs = ["base64"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
