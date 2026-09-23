#!/usr/bin/env python3
"""Conan recipe — cobs-c 0.4 (pure C library, no autotools build system).

cobs-c 0.4 官方源码无 configure/make（仅 cobs.c/cobsr.c + 头文件 + 测试），
采用自定义编译：直接编译两个 C 源文件为静态库，安装头文件。
"""
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.build import cross_building
import os


class CobscConan(ConanFile):
    name = "cobs-c"
    version = "0.4"
    description = "Consistent Overhead Byte Stuffing (COBS) encoder/decoder in C"
    license = "MIT"
    homepage = "https://github.com/cmcqueen/cobs-c"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        c_compiler = self.conf.get("tools.build:compiler_executables", default={}).get("c") \
            or "clang"
        cflags = "-fPIC -O2" if not self.settings.build_type == "Debug" else "-fPIC -g"
        src, bld = self.source_folder, self.build_folder
        self.run(f"cd {src} && {c_compiler} {cflags} -c cobs.c -o {bld}/cobs.o")
        self.run(f"cd {src} && {c_compiler} {cflags} -c cobsr.c -o {bld}/cobsr.o")
        self.run(f"llvm-ar rcs {bld}/libcobs.a {bld}/cobs.o {bld}/cobsr.o")

    def package(self):
        copy(self, "cobs.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "cobsr.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "libcobs.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["cobs"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
