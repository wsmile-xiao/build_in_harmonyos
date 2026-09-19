#!/usr/bin/env python3
"""Conan recipe — hash 0.0.1 (clibs, string-keyed pointer hash table over khash).

Upstream (https://github.com/clibs/hash) ships hash.c/hash.h/khash.h with a
Makefile that only has a `test` target (-DTEST_HASH). There is no library
build or install rule, so this recipe compiles hash.c directly into a static
library with the Conan toolchain (R33: never rely on ambient ${CC}/${AR}) and
packages the public headers (hash.h + khash.h).
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class HashConan(ConanFile):
    name = "hash"
    version = "0.0.1"
    description = "C hash implementation based on khash (string-keyed pointer hash table)"
    license = "MIT"
    homepage = "https://github.com/clibs/hash"
    url = "https://github.com/clibs/hash"
    topics = ("hash", "khash", "container", "c")

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    # 上游无共享库构建规则，仅产静态库（库体极小的 clib 风格包）
    options = {"shared": [False]}
    default_options = {"shared": False}

    def configure(self):
        # 纯 C 库不依赖 os.version；OHOS profile 可能未定义该值导致包 Invalid
        if hasattr(self.settings, "os") and hasattr(self.settings.os, "version"):
            self.settings.rm_safe("os.version")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: 从 Conan conf 取工具链，绝不依赖 shell 环境变量（worker 上为空）
        compiler_exe = self.conf.get("tools.build:compiler_executables") or {}
        cc = compiler_exe.get("c", "clang")
        ar = compiler_exe.get("ar", "ar")

        build_type = str(self.settings.build_type)
        opt = "-O2" if build_type == "Release" else "-O0"
        src = self.source_folder
        # 上游 C99 inline 定义经 -std=c99 成为外部定义，可正常链接（已实测 T 符号）
        self.run(f"{cc} -std=c99 -fPIC {opt} -c hash.c -o hash.o", cwd=src)
        self.run(f"{ar} rcs libhash.a hash.o", cwd=src)

    def package(self):
        src = self.source_folder
        copy(self, "hash.h", src=src, dst=os.path.join(self.package_folder, "include"))
        copy(self, "khash.h", src=src, dst=os.path.join(self.package_folder, "include"))
        copy(self, "libhash.a", src=src, dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["hash"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "hash")
        self.cpp_info.set_property("cmake_target_name", "hash::hash")