#!/usr/bin/env python3
"""Conan recipe for dcraw 9.28.0.

The upstream release contains one ANSI C source file and an installer script,
but no configure script or Makefile.  The recipe therefore compiles the
self-contained ``-DNODEPS`` variant directly and installs the two useful
artifacts without invoking the upstream shell installer.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class DcrawConan(ConanFile):
    name = "dcraw"
    version = "9.28.0"
    description = "Command-line decoder for raw digital photos"
    license = "LicenseRef-dcraw-custom"
    homepage = "https://www.dechifro.org/dcraw/"
    url = "https://www.dechifro.org/dcraw/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"dcraw supports Linux and OHOS only, got {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # Keep both transport security and archive integrity verification
        # enabled.  The SHA-256 is supplied by conandata.yml.
        get(self, **self.conan_data["sources"], strip_root=True, verify=True)

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get("c") or "clang"

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler()
        flags = (
            "-O2 -DNODEPS -Wall -Wno-unused-result "
            "-Wno-array-bounds -Wno-unused-but-set-variable"
        )
        self.run(
            f'"{cc}" {flags} "dcraw.c" -o "dcraw" -lm -s',
            cwd=self.source_folder,
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        copy(self, "dcraw", src=self.source_folder, dst=bin_dir, keep_path=False)
        copy(self, "dcraw.1", src=self.source_folder, dst=man_dir, keep_path=False)

        binary = os.path.join(bin_dir, "dcraw")
        if str(self.settings.os) == "OHOS":
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            signed = binary + ".signed"
            self.run(
                f'"{objcopy}" --remove-section .codesign "{binary}" '
                "2>/dev/null || true",
                cwd=self.package_folder,
            )
            self.run(
                f'"{sign_tool}" sign -inFile "{binary}" '
                f'-outFile "{signed}" -selfSign 1',
                cwd=self.package_folder,
                quiet=True,
            )
            os.replace(signed, binary)
        if os.path.exists(binary):
            os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
