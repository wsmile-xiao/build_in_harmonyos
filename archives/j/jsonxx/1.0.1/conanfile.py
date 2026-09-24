#!/usr/bin/env python3
"""Conan recipe — jsonxx 1.0.1 (header + single source, plain Makefile).

jsonxx 是基于标准库的轻量 C++ JSON 解析/序列化库。上游 tarball 只有
test 程序用的 Makefile（无 configure / library / install 目标），因此
配方直接编译 jsonxx.cc 为静态库并安装头文件与库文件。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class JsonxxConan(ConanFile):
    name = "jsonxx"
    version = "1.0.1"
    description = "jsonxx — light-weight JSON parser, writer and reader in C++"
    license = "MIT"
    homepage = "https://github.com/hjiang/jsonxx"
    url = "https://github.com/hjiang/jsonxx"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"jsonxx supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler from Conan conf, never from bare shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict)
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"

        src = self.source_folder
        self.run(
            f"cd {src} && {cxx} -std=c++11 -O2 -fPIC -c jsonxx.cc -o jsonxx.o",
            env="conanbuild",
        )
        self.run(
            f"cd {src} && llvm-ar rcs libjsonxx.a jsonxx.o && llvm-ranlib libjsonxx.a",
            env="conanbuild",
        )

    def package(self):
        src = self.source_folder
        copy(self, "jsonxx.h", src, os.path.join(self.package_folder, "include"))
        copy(self, "libjsonxx.a", src, os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE", src, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["jsonxx"]