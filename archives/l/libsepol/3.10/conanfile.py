#!/usr/bin/env python3
"""Conan recipe for libsepol 3.10 on HarmonyOS PC.

libsepol is a plain Makefile project (no autotools/CMake/meson).
The SELinuxProject monorepo archive contains both libselinux and libsepol.
Only libsepol targets are built here; this is a standalone Conan package
consumed by libselinux and other SELinux-related packages.

R33: Never use ${CC} or ${CFLAGS} in self.run() — they are empty on CI workers.
     Get compiler from Conan: self.conf.get("tools.build:compiler_executables:c", ...)
"""

import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibsepolConan(ConanFile):
    name = "libsepol"
    version = "3.10"
    description = "SELinux binary policy manipulation library"
    license = "LGPL-2.1"
    homepage = "https://github.com/SELinuxProject/selinux"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "clang")

        # libsepol uses -Werror by default; strip it to avoid build failures
        # on OHOS Clang 15 with newer warning flags.
        cflags = "-O2 -fPIC -D_GNU_SOURCE -I. -I../include"

        # Build libsepol (static library only for now)
        self.run(
            f"make -C {self.source_folder}/libsepol -j1 CC={cc} "
            f"CFLAGS='{cflags}' "
            f"DISABLE_SHARED=y "
            f"all",
        )

    def package(self):
        # Install headers from libsepol/include/ preserving tree structure
        src_include = os.path.join(self.source_folder, "libsepol", "include")
        for root, dirs, files in os.walk(src_include):
            for f in files:
                if f.endswith(".h"):
                    rel_dir = os.path.relpath(root, src_include)
                    dst_dir = os.path.join(self.package_folder, "include", rel_dir)
                    os.makedirs(dst_dir, exist_ok=True)
                    copy(self, f, root, dst_dir)

        # Install static library
        src_lib = os.path.join(self.source_folder, "libsepol", "src")
        copy(self, "libsepol.a", src_lib, os.path.join(self.package_folder, "lib"))

        # Install pkg-config file
        copy(self, "libsepol.pc", src_lib, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["sepol"]
        self.cpp_info.set_property("pkg_config_name", "libsepol")