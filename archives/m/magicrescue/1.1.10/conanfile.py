#!/usr/bin/env python3
"""Conan recipe for magicrescue 1.1.10 — data recovery tool (CLI, autotools).

Build: configure && make && make install. Produces 5 executables
(magicrescue, dupemap, tools/inputseek, tools/safecat, tools/textextract)
plus the perl helper scripts (magicsort, tools/*.pl) and recipe files.
Adapted for HarmonyOS OHOS (aarch64-unknown-linux-ohos).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MagicrescueConan(ConanFile):
    name = "magicrescue"
    version = "1.1.10"
    description = "magicrescue 1.1.10 — data recovery tool: scans devices for known file types and extracts them"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/jbj/magicrescue"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # magicrescue ships a custom `configure` (not autoconf) that requires
        # the source root as CWD (it checks `./config.d` and `./config.config`),
        # so build in-source from the source folder.
        self.run("./configure --prefix=/", cwd=self.source_folder, env="conanbuild")
        # R9: -j1
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        # Makefile install honors $(DESTDIR)$(PREFIX); prefix=/ → package_folder/bin
        self.run(f"make install DESTDIR={self.package_folder}",
                 cwd=self.source_folder, env="conanbuild")

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
