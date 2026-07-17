#!/usr/bin/env python3
"""Conan recipe for GNU enscript 1.6.6 — Autotools project.

enscript converts ASCII text files to PostScript (and other formats).
It is a CLI tool suite (enscript / mkafmmap / states), not a library.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class EnscriptConan(ConanFile):
    name = "enscript"
    version = "1.6.6"
    description = "GNU enscript — convert ASCII text to PostScript and other formats"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/enscript/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R5: OHOS has no /bin/sh; configure and libtool need bash.
        if self.settings.os in ("Linux", "OHOS"):
            bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
            tc.configure_args.append(f"SHELL={bash}")
        # Drop NLS: libintl/gettext is not part of the OHOS musl sysroot,
        # and enscript's CLI output does not need localization for validation.
        tc.configure_args.append("--disable-nls")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # enscript hardcodes its data/config dir at compile time (SYSCONFDIR).
        # After Conan relocates the package, point ENSCRIPT_LIBRARY at the
        # bundled fonts/afm dir; enscript resolves enscript.cfg via its
        # "<library>/../../etc" fallback, keeping the package relocatable.
        self.runenv_info.define_path(
            "ENSCRIPT_LIBRARY", os.path.join(self.package_folder, "share", "enscript")
        )
