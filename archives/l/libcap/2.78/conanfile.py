#!/usr/bin/env python3
"""Conan recipe for the C libraries in libcap 2.78."""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibcapConan(ConanFile):
    name = "libcap"
    version = "2.78"
    description = "Linux capability library for POSIX.1e capabilities"
    license = "BSD-3-Clause OR GPL-2.0-only"
    homepage = "https://sites.google.com/site/fullycapable/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        shared = "yes" if self.options.shared else "no"
        cflags = "-g -O0" if self.settings.build_type == "Debug" else "-O2"
        args = (
            f"CC={cc} AR=llvm-ar RANLIB=llvm-ranlib CFLAGS='{cflags}' "
            f"GOLANG=no PAM_CAP=no SHARED={shared} prefix={self.package_folder}"
        )
        self.run(f"make -C {self.source_folder} {args} -j1")
        self.run(f"make -C {self.source_folder} {args} -j1 test")

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        copy(self, "capability.h", os.path.join(src, "libcap", "include", "sys"),
             os.path.join(pkg, "include", "sys"))
        copy(self, "psx_syscall.h", os.path.join(src, "psx"),
             os.path.join(pkg, "include", "sys"))
        copy(self, "libcap.a", os.path.join(src, "libcap"), os.path.join(pkg, "lib"))
        copy(self, "libpsx.a", os.path.join(src, "libcap"), os.path.join(pkg, "lib"))
        copy(self, "libcap.so*", os.path.join(src, "libcap"), os.path.join(pkg, "lib"))
        copy(self, "libpsx.so*", os.path.join(src, "libcap"), os.path.join(pkg, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["cap", "psx"]
        self.cpp_info.system_libs = ["pthread"]
