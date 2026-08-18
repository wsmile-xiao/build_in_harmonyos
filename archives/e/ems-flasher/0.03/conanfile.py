#!/usr/bin/env python3
"""Conan recipe — ems-flasher 0.03 (Makefile project, command-line tool).

ems-flasher is a tool to flash EMS Gameboy USB 64Mbit flash cartridges.
Build system: pure Makefile (no configure script).
Dependency: libusb/1.0.27 (libusb 1.0 API).

The upstream Makefile hardcodes `pkg-config --cflags/--libs libusb-1.0` inline,
which doesn't work in cross-compilation (libusb .pc points to /usr/local).
Patch 0001-Makefile.patch makes CFLAGS/LIBS/LDFLAGS env-overrideable and
adds an install target using cp (OHOS has no 'install' command).

R33: Compiler and flags obtained from Conan toolchain, not shell env vars.
R38: Command-line tool — product is bin/ems-flasher.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class EmsFlasherConan(ConanFile):
    name = "ems-flasher"
    version = "0.03"
    description = "Tool to flash EMS Gameboy USB 64Mbit flash cartridges"
    license = "MIT"
    homepage = "http://lacklustre.net/projects/ems-flasher/"
    url = ""  # CI fills this

    package_type = "application"

    # R32: settings.os check must use in ("Linux", "OHOS") if needed
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libusb/1.0.27")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: Use Conan toolchain environment generators
        from conan.tools.gnu import AutotoolsDeps, PkgConfigDeps
        from conan.tools.env import VirtualBuildEnv
        VirtualBuildEnv(self).generate()
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

    def build(self):
        # Apply patch 0001-Makefile.patch (env-overrideable CFLAGS/LIBS/LDFLAGS)
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, NEVER from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cc = compilers.get("c") or "clang"

        # Get libusb include/lib paths from the dependency's cpp_info
        libusb = self.dependencies["libusb"]
        libusb_info = libusb.cpp_info.aggregated_components()
        libusb_inc = libusb_info.includedirs[0] if libusb_info.includedirs else ""
        libusb_lib = libusb_info.libdirs[0] if libusb_info.libdirs else ""

        cflags = "-g -Wall -Werror"
        if libusb_inc:
            cflags += f" -I{libusb_inc}"
        ldflags = f"-L{libusb_lib}" if libusb_lib else ""
        # cpp_info.libs returns names without -l prefix (e.g. "usb-1.0")
        libs = " ".join(f"-l{l}" for l in libusb_info.libs) if libusb_info.libs else "-lusb-1.0"

        # R9: Always use -j1, never -j$(nproc)
        self.run(
            f'make -j1 CC="{cc}" '
            f'CFLAGS="{cflags}" LDFLAGS="{ldflags}" LIBS="{libs}"',
            cwd=self.source_folder
        )

    def package(self):
        # Install the binary to bin/
        copy(self, "ems-flasher", self.source_folder, os.path.join(self.package_folder, "bin"))
        # Copy license
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # R38: Command-line tool — declare bindirs so consumers can find the executable
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        # Runtime LD_LIBRARY_PATH for libusb is handled automatically by Conan's
        # VirtualRunEnv generator (consumers use generators="VirtualRunEnv")
