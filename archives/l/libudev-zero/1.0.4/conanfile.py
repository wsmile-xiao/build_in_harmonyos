#!/usr/bin/env python3
"""Conan recipe for libudev-zero 1.0.4 — zero-dependency libudev implementation.

libudev-zero is a drop-in replacement for systemd's libudev, providing
device event monitoring without systemd dependency. Uses pure Makefile.

Key adaptation:
  - R26: libudev is a system-name library → static-only (no shared .so)
  - R9:  Use make -j1
  - R33: Get compiler from Conan conf, not shell env vars
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibudevZeroConan(ConanFile):
    name = "libudev-zero"
    version = "1.0.4"
    description = "Zero-dependency libudev implementation for device event monitoring"
    license = "ISC"
    homepage = "https://github.com/illiliti/libudev-zero"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    # R26: libudev is a system-name library → always static
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

        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        # tools.build:compiler_executables is stored as a dict in the profile.
        compiler_executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compiler_executables.get("c", "clang")
        ar = "llvm-ar"
        ranlib = "llvm-ranlib"

        # R26: System-name library → static-only (build only libudev.a)
        # R9: Always use -j1
        self.run(f"make CC={cc} AR={ar} RANLIB={ranlib} libudev.a -j1", cwd=self.source_folder)

    def package(self):
        # Use make install-static to install libudev.a, libudev.h, libudev.pc
        self.run(f"make install-static DESTDIR= PREFIX={self.package_folder}", cwd=self.source_folder)

    def package_info(self):
        # Library name is "udev" (libudev.a → -ludev)
        self.cpp_info.libs = ["udev"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
