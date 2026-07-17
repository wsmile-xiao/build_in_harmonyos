#!/usr/bin/env python3
"""Conan recipe — libcap 2.69 (Makefile)"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibcapConan(ConanFile):
    name = "libcap"
    version = "2.69"
    description = "Linux capability library for POSIX.1e capabilities"
    license = "GPL-2.0"
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

        cc = "clang"
        ar = "llvm-ar"
        ranlib = "llvm-ranlib"

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        if compilers:
            cc = compilers.get("c", cc)

        shared = "yes" if self.options.shared else "no"

        # Propagate build_type to Makefile CFLAGS (review P2: Debug vs Release optimization)
        if self.settings.build_type == "Debug":
            cflags = "-g -O0"
        else:
            cflags = "-O2"

        src = self.source_folder
        self.run(f"make -C {os.path.join(src, 'libcap')} CC={cc} AR={ar} RANLIB={ranlib} CFLAGS='{cflags}' GOLANG=no PAM_CAP=no SHARED={shared} -j1")

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        # Headers: capability.h from libcap/include/sys/
        copy(self, "capability.h",
             os.path.join(src, "libcap", "include", "sys"),
             os.path.join(pkg, "include", "sys"))
        # psx_syscall.h from psx/ (avoid broken symlink in libcap/include/sys/)
        copy(self, "psx_syscall.h",
             os.path.join(src, "psx"),
             os.path.join(pkg, "include", "sys"))
        # Static libraries from libcap/
        copy(self, "libcap.a",
             os.path.join(src, "libcap"),
             os.path.join(pkg, "lib"))
        copy(self, "libpsx.a",
             os.path.join(src, "libcap"),
             os.path.join(pkg, "lib"))
        if self.options.shared:
            copy(self, "libcap.so*",
                 os.path.join(src, "libcap"),
                 os.path.join(pkg, "lib"))
            copy(self, "libpsx.so*",
                 os.path.join(src, "libcap"),
                 os.path.join(pkg, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["cap", "psx"]
        self.cpp_info.system_libs = ["pthread"]
