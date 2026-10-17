#!/usr/bin/env python3
"""Conan recipe for adacgi 1.6 — Ada 95 Common Gateway Interface library.

AdaCGI is distributed as Ada source units (``CGI`` and ``Ustrings``) rather
than precompiled libraries.  Consumers compile the units with the packaged
``gcc-ada/9.5.0`` GNAT toolchain via ``gnatmake -I<adainclude>``.  This recipe
downloads the authoritative Debian mirror of the upstream ``1.6`` source
archive, validates the sources by compiling both units, and packages the
unmodified source files plus their LGPL license text.
"""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


_SOURCE_URL = (
    "https://deb.debian.org/debian/pool/main/a/adacgi/adacgi_1.6.orig.tar.gz"
)
_SOURCE_SHA256 = "6a417f4936a362c1d3d85b8331c26be4ef381ce152cf03c39ac1d5c86fdb884c"

_LIBRARY_UNITS = ("cgi.ads", "cgi.adb", "ustrings.ads", "ustrings.adb")
_LICENSE_FILES = ("COPYING", "lesser.txt")


class AdacgiConan(ConanFile):
    name = "adacgi"
    version = "1.6"
    # AdaCGI ships Ada source units (like a header-only library), so there is
    # no precompiled binary and no shared/static distinction.  header-library
    # expresses "source-only distribution" without requiring a shared option.
    package_type = "header-library"

    description = "Ada 95 interface to the Common Gateway Interface (CGI)"
    license = "LGPL-2.1-or-later"
    homepage = "http://www.dwheeler.com/adacgi"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "The OHOS adacgi package supports AArch64/armv8 only"
            )

    def build_requirements(self):
        self.tool_requires("gcc-ada/9.5.0")

    def generate(self):
        env = Environment()
        if str(self.settings.os) == "OHOS":
            # gcc-ada's GNAT driver resolves `as`/`ld` via execvp on PATH.
            # The device's GNU binutils live in /data/service/hnp/bin, while
            # /usr/bin/as is SELinux-protected (Permission denied).  Prepend
            # the HNP binutils directory so gnatmake can assemble and link.
            env.prepend_path("PATH", "/data/service/hnp/bin")
        env.vars(self).save_script("adacgi_binutils_env")

    def source(self):
        get(
            self,
            url=_SOURCE_URL,
            sha256=_SOURCE_SHA256,
            strip_root=True,
        )

    def _build_tool(self, name):
        dependency = self.dependencies.build["gcc-ada"]
        bindirs = dependency.cpp_info.bindirs or ["bin"]
        executable = os.path.join(
            dependency.package_folder, bindirs[0], name
        )
        if not os.path.isfile(executable):
            raise ConanInvalidConfiguration(
                "The gcc-ada build requirement does not provide {}: {}".format(
                    name, executable
                )
            )
        return executable

    def build(self):
        gnatmake = self._build_tool("gnatmake")
        source_root = self.source_folder
        work = os.path.join(self.build_folder, "compile-check")
        os.makedirs(work, exist_ok=True)
        for unit in ("cgi.adb", "ustrings.adb"):
            self.run(
                "{} -q -gnat95 -c -I{} {}".format(
                    shlex.quote(gnatmake),
                    shlex.quote(source_root),
                    shlex.quote(os.path.join(source_root, unit)),
                ),
                cwd=work,
                env=["conanbuild", "adacgi_binutils_env"],
            )

    def package(self):
        adainclude = os.path.join(self.package_folder, "adainclude")
        for unit in _LIBRARY_UNITS:
            copy(
                self,
                unit,
                src=self.source_folder,
                dst=adainclude,
                keep_path=False,
            )
        licenses = os.path.join(self.package_folder, "licenses")
        for license_file in _LICENSE_FILES:
            copy(
                self,
                license_file,
                src=self.source_folder,
                dst=licenses,
                keep_path=False,
            )

    def package_info(self):
        self.cpp_info.includedirs = ["adainclude"]
        self.cpp_info.libs = []
