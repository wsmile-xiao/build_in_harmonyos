#!/usr/bin/env python3
"""Conan recipe for LE 1.16.8 — text editor with block and binary operations.

LE builds with autotools and the release tarball already ships a generated
``configure``/``Makefile.in``, so no autoreconf (and therefore none of the
perl/gettext bootstrap issues) is involved.  The only dependency is curses:
the ohpcd ncurses package is a *wide-character, static* build
(``libncursesw.a``) and LE's bundled ``LE_PATH_CURSES_DIRECT`` macro looks for
curses only under hard-coded ``/usr/include`` paths, so the recipe passes
``--with-curses-include``; LE's own wide-character detection then links
``-lncursesw`` (the macro appends the "w"), with no source patch needed.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LeConan(ConanFile):
    name = "le"
    version = "1.16.8"
    description = "LE text editor: block/binary operations, hex mode, large files, syntax highlighting"
    license = "GPL-3.0-or-later"
    homepage = "http://lav.yar.ru/programs.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("le is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        # wide-character static build; see the header comment
        self.requires("ncurses/6.5")

    def layout(self):
        basic_layout(self)
        # LE builds in-source: config.h and the Makefiles are produced next to
        # the sources and the sub-makefiles extend CFLAGS in place.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # LE_PATH_CURSES_DIRECT only searches hard-coded /usr/include-style
        # directories, so the Conan-provided headers have to be pointed at.
        ncurses = self.dependencies["ncurses"]
        tc.configure_args.extend([
            "--with-ncurses=yes",
            "--with-curses-include=%s" % os.path.join(ncurses.package_folder, "include"),
        ])
        if self.settings.os == "OHOS":
            # config.guess cannot run its probe on HarmonyOS (the sandbox only
            # executes signed binaries), so declare the triple explicitly.
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        tc.generate()
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS: the ephemeral Conan build directory cannot always be used as a
        # process working directory (getcwd() fails there).
        os.environ["PWD"] = self.build_folder
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        self._audit_upstream_tests()

    def _audit_upstream_tests(self):
        # The release ships no test suite at all (no tests/ directory, no
        # check_PROGRAMS/TESTS, no check target).
        self.run("grep -nE 'check_PROGRAMS|^TESTS|check-local|^check:' Makefile.in "
                 "lib/Makefile.in src/Makefile.in misc/Makefile.in doc/Makefile.in || true")
        self.run("find . -maxdepth 2 -iname '*test*' | head || true")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
