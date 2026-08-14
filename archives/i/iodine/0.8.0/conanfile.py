#!/usr/bin/env python3
"""Conan recipe — iodine 0.8.0 (Makefile)"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class IodineConan(ConanFile):
    name = "iodine"
    version = "0.8.0"
    description = "IPv4 data over DNS protocol tunneling tool"
    license = "ISC"
    homepage = "https://code.kryo.se/iodine"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan-generated env (profile sets tools.build:compiler_executables)
        cc = os.environ.get("CC", "clang")

        # Get zlib paths from dependency package folder
        zlib = self.dependencies["zlib"]
        zlib_prefix = zlib.package_folder
        include_path = os.path.join(zlib_prefix, "include")
        lib_path = os.path.join(zlib_prefix, "lib")

        # Build via top-level Makefile, which delegates to src/
        # TARGETOS=Linux: osflags script doesn't recognize HarmonyOS uname output
        # CFLAGS/LDFLAGS set as env vars so Makefile's += appends correctly
        # -DHAVE_DAEMON: musl libc provides daemon(3), skip static fallback (R8 compliance)
        os.environ["CFLAGS"] = f"-fPIC -O2 -DHAVE_DAEMON -I{include_path}"
        os.environ["LDFLAGS"] = f"-L{lib_path}"
        self.run(f"make CC={cc} TARGETOS=Linux -j1", cwd=self.source_folder)

    def package(self):
        # Binaries are in bin/, man page in man/
        copy(self, "iodine", os.path.join(self.source_folder, "bin"),
             os.path.join(self.package_folder, "sbin"))
        copy(self, "iodined", os.path.join(self.source_folder, "bin"),
             os.path.join(self.package_folder, "sbin"))
        copy(self, "iodine.8", os.path.join(self.source_folder, "man"),
             os.path.join(self.package_folder, "share", "man", "man8"))

    def package_info(self):
        self.cpp_info.bindirs = ["sbin"]
