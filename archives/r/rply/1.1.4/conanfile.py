#!/usr/bin/env python3
"""Conan recipe for rply 1.1.4 - ANSI C library for PLY file I/O.

Upstream ships no build system at all (just ``rply.c`` + ``rply.h`` +
``rplyfile.h``), so the recipe compiles a static ``librply.a`` directly and
installs the two public headers.  The library has no third-party dependencies
and does not use libm.

The upstream examples under ``etc/`` are not tests, so the recipe relies on the
C consumer program in ``test_package/`` (create/read round-trip through the
public API).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class RplyConan(ConanFile):
    name = "rply"
    version = "1.1.4"
    description = "ANSI C library for PLY file format input and output"
    license = "MIT"
    homepage = "https://w3.impa.br/~diego/software/rply/"
    url = ""

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "rply OHOS adaptation is validated on Linux/OHOS, not "
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
        ar = os.path.join(os.path.dirname(cc), "llvm-ar")
        if not os.path.isfile(ar):
            ar = "ar"
        self.run('"{}" -O2 -fPIC -Wall -c rply.c -o rply.o'.format(cc),
                 cwd=self.source_folder)
        self.run('"{}" rcs librply.a rply.o'.format(ar),
                 cwd=self.source_folder)

    def package(self):
        copy(self, "rply.h", self.source_folder,
             os.path.join(self.package_folder, "include"))
        copy(self, "rplyfile.h", self.source_folder,
             os.path.join(self.package_folder, "include"))
        copy(self, "librply.a", self.source_folder,
             os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["rply"]
