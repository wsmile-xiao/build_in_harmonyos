#!/usr/bin/env python3
"""Conan recipe for bc — GNU arbitrary precision calculator.

Autotools project producing two CLI executables: bc and dc.
"""
import os
from conan import ConanFile
from conan.tools.files import get, replace_in_file, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BcConan(ConanFile):
    name = "bc"
    version = "1.07.1"
    description = "GNU bc arbitrary precision calculator language"
    license = "GPL-3.0-or-later"
    homepage = "https://ftp.gnu.org/gnu/bc/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder

        # Fix 1: Change umask 077 to umask 002 in configure script.
        # On HarmonyOS, mktemp -d with umask 077 creates temp dirs
        # owned by a different uid, causing Permission denied errors.
        replace_in_file(self, os.path.join(src, "configure"),
                        "umask 077", "umask 002")

        # Fix 2: Replace ed-based fix-libmath_h with sed-based approach.
        # The 'ed' line editor is not available on HarmonyOS.
        fix_path = os.path.join(src, "bc", "fix-libmath_h")
        sed_script = (
            "#!/bin/sh\n"
            "sed -i '1s/^/{\"/' libmath.h\n"
            "sed -i 's/$/\",/' libmath.h\n"
            "sed -i '2,$s/^/\"/' libmath.h\n"
            "sed -i '$d' libmath.h\n"
            "echo '0}' >> libmath.h\n"
        )
        with open(fix_path, "w") as f:
            f.write(sed_script)

        # Fix 3: Skip doc subdirectory (makeinfo not available on HarmonyOS).
        # Modify Makefile.in BEFORE configure so the generated Makefile
        # won't include the doc subdirectory.
        replace_in_file(self, os.path.join(src, "Makefile.in"),
                        "SUBDIRS = lib bc dc doc", "SUBDIRS = lib bc dc")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
