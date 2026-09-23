#!/usr/bin/env python3
"""Conan recipe for chordii 4.5.3b — ChordPro text formatter (PostScript).

chordii builds two command-line tools (chordii, a2crd) with modern automake.
Upstream ships a real test suite (src/Makefile.am TESTS = above.sh below.sh
passthrough.sh, run via `make check`).

E011: the HMDFS filesystem cannot write into the `umask 077` temp dirs the
configure script creates; configure is patched to umask 022 (patches/).
clang >= 10 defaults to -fno-common; chordii.h defines global variables
(dummy_kcs / dummy_chord_struct) in a header, so -fcommon is injected via
extra_cflags (E163 family issue; same approach as alex4/arpalert recipes).
"""
import os

from conan import ConanFile
from conan.tools.files import (
    copy,
    get,
    apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ChordiiConan(ConanFile):
    name = "chordii"
    version = "4.5.3b"
    description = "Chordii — ChordPro text formatter producing guitar music sheets in PostScript"
    license = "GPL-3.0-or-later"
    homepage = "https://sourceforge.net/projects/chordii/"
    url = ""  # CI fills this

    package_type = "application"

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
        # chordii.h defines dummy_kcs/dummy_chord_struct globals in a header;
        # clang >= 10 (-fno-common) fails to link with duplicate symbols.
        tc.extra_cflags.append("-fcommon")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E386: modern autoconf adopts CONFIG_SHELL from the profile
        # [buildenv] (/data/service/hnp/bin/bash); that bash's getcwd()
        # intermittently fails on HMDFS dirs ("working directory cannot be
        # determined"), and profile buildenv overrides toolchain-level env —
        # so the shell must be pinned inline on the configure invocation.
        configure = os.path.join(self.source_folder, "configure")
        self.run(
            f'cd "{self.build_folder}" && CONFIG_SHELL=/bin/sh SHELL=/bin/sh '
            f'/bin/sh "{configure}" --prefix="{self.package_folder}"'
        )
        autotools = Autotools(self)
        autotools.make(args=["-j1"])
        # Run the official upstream test suite (src/Makefile.am TESTS =
        # test/above.sh, test/below.sh, test/passthrough.sh via `make check`),
        # covering a2crd chord-above/chords-below conversions and directive
        # passthrough. Executed here so CI L1c can verify real upstream test
        # execution from the conan create log.
        autotools.make(args=["check"])

    def package(self):
        # Manual staging mirroring the upstream install rules (bin + man1);
        # avoids depending on install-sh/DESTDIR behaviour of the automake
        # wrapper. Same approach as the other OHOS tool packages.
        src = self.source_folder
        bld = os.path.join(self.build_folder, "src")
        copy(self, "chordii", src=bld, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "a2crd", src=bld, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "*.1", src=os.path.join(src, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "COPYING", src=src,
             dst=os.path.join(self.package_folder, "licenses"))
        for exe in ("chordii", "a2crd"):
            exe_path = os.path.join(self.package_folder, "bin", exe)
            if os.path.exists(exe_path):
                os.chmod(exe_path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
