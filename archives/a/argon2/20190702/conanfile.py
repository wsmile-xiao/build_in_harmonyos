#!/usr/bin/env python3
"""Conan recipe for argon2 — PHC winner password hashing library.

Build system: Makefile (raw make, no configure)
OHOS notes: KERNEL_NAME=Linux needed because uname -s returns "OHOS" not "Linux"
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Argon2Conan(ConanFile):
    name = "argon2"
    version = "20190702"
    description = "PHC winner password hashing library (Argon2i/Argon2d/Argon2id)"
    license = "CC0-1.0 / Apache-2.0"
    homepage = "https://github.com/P-H-C/phc-winner-argon2"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, not shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        # KERNEL_NAME=Linux: OHOS uname returns "OHOS" which the Makefile
        # does not recognize; setting to Linux enables the Linux code path
        # (shared lib with -soname, -lrt -ldl linkage).
        # LIBRARY_REL=lib: library install subdirectory name.
        # R9: -j1 only (OHOS mkfifo not supported).
        self.run(f"make -C {self.source_folder} CC={cc} KERNEL_NAME=Linux LIBRARY_REL=lib -j1")

    def package(self):
        copy(self, "argon2.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        if self.options.shared:
            copy(self, "libargon2.so*", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libargon2.a", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "lib"))
        # CLI tool (self-contained, no library dependency)
        copy(self, "argon2", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["argon2"]
        # Package includes both library and CLI tool
        self.cpp_info.bindirs = ["bin"]
        # Static lib needs rt (clock_gettime) and dl (dlopen);
        # shared lib already links them internally.
        if not self.options.shared and self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["rt", "dl"]
