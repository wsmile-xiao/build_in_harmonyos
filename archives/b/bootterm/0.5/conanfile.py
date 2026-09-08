#!/usr/bin/env python3
"""Conan recipe for bootterm 0.5 — a simple terminal for boot prompts.

bootterm (bt) is a minimal serial-port terminal by Willy Tarreau, used to
watch kernel boot messages and interact with U-Boot. Single C source file
(src/bt.c), plain Makefile, no external library dependencies.

Build system: simple Makefile (no configure). The Makefile fixes its own
CFLAGS assignment and exposes USR_CFLAGS as the user append point.
License: MIT.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class BoottermConan(ConanFile):
    name = "bootterm"
    version = "0.5"
    description = "A simple terminal to watch boot messages and interact with U-Boot over serial ports"
    license = "MIT"
    homepage = "https://github.com/wtarreau/bootterm"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.build = "."
        self.folders.generators = "."

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS {self.settings.os} not supported, requires Linux or OHOS"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, not shell env vars (the Makefile
        # hard-assigns CC := $(CROSS_COMPILE)cc, so it must be overridden on
        # the make command line).
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        # The upstream Makefile includes <asm/termbits.h> on __linux__ (OHOS
        # toolchains define it), which drops the <termios.h> API declarations
        # and still lacks TCGETS2 in the OHOS kernel-uapi headers. Passing the
        # upstream NO_TCGETS2 knob selects <termios.h> instead: identical
        # runtime behavior, zero implicit-declaration warnings.
        self.run(f'make -j1 CC="{cc}" USR_CFLAGS="-DNO_TCGETS2"')

    def package(self):
        # Manual install — the upstream install target runs strip and the
        # system install utility; CI handles ELF signing post-build (E077).
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy2(
            os.path.join(self.source_folder, "bin", "bt"),
            os.path.join(bin_dir, "bt"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
