#!/usr/bin/env python3
"""Conan recipe — crossline 1.0 (pure C readline/libedit replacement library).

Upstream jcwangxp/Crossline ships a single crossline.c + crossline.h with no
build system (compile instructions are plain compiler invocations, see README
"Build and Test"). This recipe uses a custom build: compile crossline.c into a
static (default) or shared library, install the public header.

The library is self-contained (pure C, only libc/libm/POSIX termios etc.),
no third-party dependencies.
"""
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout
import os


class CrosslineConan(ConanFile):
    name = "crossline"
    version = "1.0"
    description = "A small, self-contained, cross-platform readline and libedit replacement (pure C)"
    license = "MIT"
    homepage = "https://github.com/jcwangxp/Crossline"
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
        cflags = "-fPIC -O2 -Wall" if not self.settings.build_type == "Debug" else "-fPIC -g -Wall"
        src, bld = self.source_folder, self.build_folder
        self.run(f"cd {src} && {c_compiler} {cflags} -c crossline.c -o {bld}/crossline.o")
        if self.options.shared:
            self.run(f"cd {src} && {c_compiler} {cflags} -shared crossline.c -o {bld}/libcrossline.so")
        else:
            self.run(f"llvm-ar rcs {bld}/libcrossline.a {bld}/crossline.o")

    def package(self):
        copy(self, "crossline.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if self.options.shared:
            copy(self, "libcrossline.so", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libcrossline.a", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["crossline"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]