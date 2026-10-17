#!/usr/bin/env python3
"""Conan recipe for motti 3.1.1 — GNU strategy game (autotools, C++).

Upstream builds libmottifram.a (reusable board/game framework library),
the motti terminal binary and the testmotti test driver. Autotools install
puts the library in lib/, headers in include/motti/ and the binaries in
bin/games/ (upstream overrides bindir), so cpp_info mirrors that layout.

E386: the OHOS profile [buildenv] sets CONFIG_SHELL=/data/service/hnp/bin/bash,
whose getcwd() fails on HMDFS trees ("working directory cannot be determined").
Toolchain-level env overrides are themselves overridden by the profile
buildenv, so configure/make are run via self.run with an inline
CONFIG_SHELL=/bin/sh SHELL=/bin/sh prefix, in-source (no separate deep build
directory, which also triggers the getcwd storm).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class MottiConan(ConanFile):
    name = "motti"
    version = "3.1.1"
    description = "GNU Motti - a multiplayer strategy board game for the terminal with a reusable C++ game framework library"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/motti/"
    url = "https://www.gnu.org/software/motti/"
    # Hybrid upstream: libmottifram.a + headers (consumable framework) and
    # the motti/testmotti executables. Declared as "library" so consumers
    # get the framework headers/lib propagated (application packages do not
    # propagate includedirs/libs); the binaries stay in bindirs and are
    # declared by the software-level commands.json.
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    # Upstream only builds the static libmottifram.a; shared is declared
    # (required for package_type=library) and rejected in validate().
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "motti 3.1.1 upstream builds only the static libmottifram.a")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Toolchain env (CC/CXX/CFLAGS from the OHOS profile) lands in
        # conanbuild, which self.run() sources for the build() commands.
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        configure = os.path.join(self.source_folder, "configure")
        # In-source configure/make with a getcwd-safe shell (E386).
        # config.guess cannot classify the HarmonyOS kernel, so the cross
        # triplets are passed explicitly (build_toolchain's gnu triplet is
        # aarch64-unknown-linux-ohos for os=OHOS/arch=armv8).
        self.run(
            f'cd "{self.source_folder}" && '
            f'CONFIG_SHELL=/bin/sh SHELL=/bin/sh /bin/sh "{configure}" '
            f'--prefix="{self.package_folder}" '
            f'--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos'
        )
        self.run(f'cd "{self.source_folder}" && make -j1')

    def package(self):
        self.run(f'cd "{self.source_folder}" && make install')

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # upstream sets bindir=$(exec_prefix)/bin/games
        self.cpp_info.bindirs = ["bin", "bin/games"]
        self.cpp_info.libs = ["mottifram"]
