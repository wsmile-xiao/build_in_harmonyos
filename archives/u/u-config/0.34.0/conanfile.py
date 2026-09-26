#!/usr/bin/env python3
"""Conan recipe for u-config 0.34.0 — a small, simple, portable pkg-config clone.

Upstream ships no configure step for packagers: every build is one
translation unit compiled from a platform layer (README "Build"). For
POSIX-like targets (Linux/OHOS) that file is main_posix.c, which includes
src/u-config.c. The Makefile targets are development-only and the
"pkg-config" target embeds the *host* search path, so it is unsuitable for
cross builds; we invoke the compiler directly instead.

The upstream test suite (main_test.c) is a libc-based platform layer that
runs the entry point over a virtual filesystem, so it executes natively on
the target and needs no test data.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class UConfigConan(ConanFile):
    name = "u-config"
    version = "0.34.0"
    description = "Small, simple, portable pkg-config and pkgconf clone (single translation unit)"
    license = "Unlicense"
    homepage = "https://github.com/skeeto/u-config"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("u-config is packaged through its POSIX platform layer (Linux/OHOS)")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "cc")
        self.run(f"{cc} -Os -o pkg-config main_posix.c", cwd=self.source_folder)
        # Upstream suite under the README's debugging flags; UBSan trap mode
        # needs no runtime library, so it links with plain musl.
        self.run(f"{cc} -g3 -Wall -Wextra -Wconversion -Wno-clobbered"
                 " -fsanitize=undefined -fsanitize-undefined-trap-on-error"
                 " -o tests main_test.c", cwd=self.source_folder)
        self.run("./tests", cwd=self.source_folder)

    def package(self):
        copy(self, "UNLICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "pkg-config", self.source_folder, bindir)
        # Drop-in replacement is the whole point, so the tool is installed
        # as pkg-config; keep the upstream name as a second entry point.
        shutil.copyfile(os.path.join(bindir, "pkg-config"), os.path.join(bindir, "u-config"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
