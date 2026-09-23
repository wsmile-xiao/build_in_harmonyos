#!/usr/bin/env python3
"""Conan recipe for GNU termutils 2.0 — terminal utilities (tput, tabs).

The 1995 tree predates DESTDIR and the modern --bindir/--libdir configure
argument set, so build() invokes `sh configure --prefix=...` directly and
package() ships the two built tools. The bundled termcap/tparam sources
need -std=gnu89 under clang >= 15 (K&R definitions).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain


class TermutilsConan(ConanFile):
    name = "termutils"
    version = "2.0"
    description = ("GNU termutils: terminal utilities — tput (termcap "
                   "capability query) and tabs (tab stop control)")
    license = "GPL-2.0-or-later"
    homepage = "https://ftp.gnu.org/gnu/termutils/"
    url = "https://ftp.gnu.org/gnu/termutils/termutils-2.0.tar.gz"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "termutils is supported only on Linux/OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # clang >= 15 rejects the 1995 K&R definitions (tparam.c, tcutil.c)
        tc.extra_cflags = ["-std=gnu89"]
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # 1995 configure only understands --prefix; sh invocation sidesteps
        # exec-bit loss on HMDFS (E490)
        configure = os.path.join(self.source_folder, "configure")
        self.run(f'sh "{configure}" --prefix="{self.package_folder}"')
        autotools = Autotools(self)
        autotools.make(args=["-j1"])

    def package(self):
        # Upstream Makefile (1995) has no DESTDIR support. libutil.a is an
        # internal helper archive; the shippable products are the two tools.
        copy(self, "tput", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "tabs", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
