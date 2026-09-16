#!/usr/bin/env python3
"""Conan recipe for GNU trueprint 5.3 — C source pretty-printer (PostScript).

The 2001 tree predates DESTDIR and aborts configuration without an lpr/lp
command, so build() prepends a private stub print-spool directory to PATH
(the runtime print command stays user-selectable via -P / TP_PRINT_CMD)
and links the bundled gettext replacement (OHOS libc has no gettext).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain


class TrueprintConan(ConanFile):
    name = "trueprint"
    version = "5.3"
    description = ("GNU trueprint: pretty-prints C/C++/Java/... source code "
                   "to PostScript with diffs, indices and headers")
    license = "GPL-2.0-or-later"
    homepage = "https://www.gnu.org/software/trueprint/"
    url = "https://ftp.gnu.org/gnu/trueprint/trueprint-5.3.tar.gz"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "trueprint is supported only on Linux/OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # configure aborts when neither lpr nor lp is found (AC_MSG_ERROR);
        # supply a private stub spool dir so detection succeeds. The stub
        # never ships: printing at runtime goes through -P/TP_PRINT_CMD.
        stub = os.path.join(self.build_folder, "stubbin")
        os.makedirs(stub, exist_ok=True)
        for tool in ("lpr", "lp"):
            stub_tool = os.path.join(stub, tool)
            with open(stub_tool, "w") as f:
                f.write("#!/bin/sh\ncat >/dev/null\nexit 0\n")
            os.chmod(stub_tool, 0o755)
        path = stub + os.pathsep + os.environ.get("PATH", "")
        # 2001 configure predates --bindir style args; sh invocation
        # sidesteps exec-bit loss on HMDFS (E490). PATH is prepended inside
        # the shell command so the toolchain env (CC/CFLAGS) stays intact.
        configure = os.path.join(self.source_folder, "configure")
        self.run(f'PATH="{path}" sh "{configure}" '
                 f'--prefix="{self.package_folder}"')
        autotools = Autotools(self)
        # MAKEINFO=true: no makeinfo on builders (doc/trueprint.info is
        # pre-touched by configure). LDADD: OHOS libc has no gettext, so
        # link the bundled replace/libreplace.a into src/trueprint.
        autotools.make(args=["-j1", "MAKEINFO=true",
                             "LDADD=../replace/libreplace.a"])

    def package(self):
        # Upstream Makefile has no DESTDIR support; ship the built tool.
        copy(self, "src/trueprint", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
