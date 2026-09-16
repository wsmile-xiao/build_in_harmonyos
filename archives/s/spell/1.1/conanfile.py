#!/usr/bin/env python3
"""Conan recipe — spell 1.1

GNU Spell: reads text and reports misspelled words via ispell/aspell as engine.
Build system: Autotools (1996-era tarball ships configure; no NLS).
The shipped Makefile assumes an in-tree build (config.h via -I$(srcdir) only),
so configure/make/install run inside the source folder with the toolchain env.
License: GPL-3.0-or-later.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SpellConan(ConanFile):
    name = "spell"
    version = "1.1"
    description = "GNU Spell - reads text and reports misspelled words via an Ispell-compatible engine"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/spell/"
    url = ""  # CI fills this

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
        from conan.tools.gnu import AutotoolsToolchain
        tc = AutotoolsToolchain(self)
        # 1990s-era config.guess/sub can't guess on OHOS and reject new triplets:
        # force build triplet to skip guessing (adms-style precedent)
        if self.settings.os == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E011: HMDFS + umask 077 in shipped configure breaks config.status
        # temp files - normalize to 022 (gsl-style precedent)
        import glob
        for _cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
            with open(_cfg, encoding="utf-8", errors="ignore") as f:
                text = f.read()
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        prefix = self.package_folder.replace("\\", "/")
        conf_args = f"--prefix={prefix}"
        if self.settings.os == "OHOS":
            conf_args += " --build=aarch64-unknown-linux-gnu"
        # in-tree build: the 1996 Makefile resolves config.h from $(srcdir)
        self.run(f"./configure {conf_args}", cwd=self.source_folder, env="conanbuild")
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        prefix = self.package_folder.replace("\\", "/")
        # install straight into the package folder (already configured with it)
        self.run("make install", cwd=self.source_folder, env="conanbuild")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
