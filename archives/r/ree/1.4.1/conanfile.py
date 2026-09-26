#!/usr/bin/env python3
"""Conan recipe for ree 1.4.1 - BIOS ROM extension / VGA font extractor.

Builds the two upstream programs with the hand-written ``makefile``:

* ``ree``      - scans /dev/mem (0xc0000-0xf0000) for ROM extensions (55 aa)
* ``fontdump`` - extracts 8x8/8x14/8x16 VGA fonts from a ROM image

No third-party dependencies.  ``ree`` needs read access to ``/dev/mem`` at
runtime (usually root only); ``fontdump`` operates on a ROM file and is fully
testable without any privileges, which is what ``test_package`` does.

Note: ``make`` prefers the lower-case ``makefile`` over a ``Makefile``, so the
hand-written build file is used (upstream also commits a CMake-generated
``Makefile`` from a different tree; it is not used here).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class ReeConan(ConanFile):
    name = "ree"
    version = "1.4.1"
    description = "Extract BIOS ROM extensions (ree) and VGA fonts (fontdump)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/alexmyczko/ree"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ree OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler("c", "clang")
        self.run('make -f makefile CC="{}" CFLAGS="-O2 -Wall" -j1'.format(cc),
                 cwd=self.source_folder)
        for prog in ("ree", "fontdump"):
            if not os.path.isfile(os.path.join(self.source_folder, prog)):
                raise ConanInvalidConfiguration(
                    "build did not produce the '{}' program".format(prog))

    def package(self):
        copy(self, "ree", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "fontdump", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "ree.8", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man8"))
        copy(self, "fontdump.1", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "README.md", self.source_folder,
             os.path.join(self.package_folder, "share", "doc", "ree"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
