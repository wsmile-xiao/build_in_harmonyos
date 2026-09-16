#!/usr/bin/env python3
"""Conan recipe for GNU termcap 1.3.1 — terminal capability library.

The 1990s tree uses a hand-written configure that predates the standard
--bindir/--libdir argument set (it aborts on them), so build() invokes
`sh configure --prefix=...` directly instead of Autotools.configure().
Its Makefile also predates DESTDIR and `make install` writes /usr/include
unconditionally, so package() copies the two artifacts directly. The build
is static-only (ar/ranlib archive).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain


class TermcapConan(ConanFile):
    name = "termcap"
    version = "1.3.1"
    description = ("GNU termcap: terminal capability database library "
                   "(tgetent/tgetflag/tgetnum/tgetstr/tgoto)")
    license = "GPL-2.0-or-later"
    homepage = "https://www.gnu.org/software/termcap/"
    url = "https://ftp.gnu.org/gnu/termcap/"

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "termcap is supported only on Linux/OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # 1996 hand-written configure only understands --prefix; Conan's
        # Autotools.configure() would pass --bindir/--libdir and it aborts.
        # sh invocation sidesteps exec-bit loss on HMDFS (E490).
        configure = os.path.join(self.source_folder, "configure")
        self.run(f'sh "{configure}" --prefix="{self.package_folder}"')
        autotools = Autotools(self)
        autotools.make(args=["-j1"])

    def package(self):
        # Upstream `make install` has no DESTDIR support and writes
        # /usr/include directly; ship the built archive and header instead.
        copy(self, "libtermcap.a",
             src=self.source_folder, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "termcap.h",
             src=self.source_folder, dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["termcap"]
