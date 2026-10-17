#!/usr/bin/env python3
"""Conan recipe for MBROLA 3.3 - diphone-concatenation speech synthesizer.

Upstream is a plain-Makefile C project that builds a single command line
executable (``Bin/mbrola``).  The upstream Makefile already carries the safe
portability defaults for the supported platforms (LITTLE_ENDIAN, ROM database
support, signal handling, include paths), so the recipe only:

* feeds the C compiler coming from the Conan profile (R33) instead of the
  upstream ``gcc`` default, and
* packages the produced CLI executable, license and documentation.

No source patches are required for OHOS: the code base is portable C89 and
the OHOS clang toolchain compiles it unmodified.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MbrolaConan(ConanFile):
    name = "mbrola"
    version = "3.3"
    description = "Speech synthesizer based on the concatenation of diphones"
    license = "AGPL-3.0-or-later"
    homepage = "https://github.com/numediart/MBROLA"
    url = "https://github.com/numediart/MBROLA"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} only supports Linux/OHOS (got {self.settings.os})"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload URLs end in the tag name (".../tar.gz/refs/tags/3.3") which has
        # no file extension; Conan's get() then derives filename "3.3" and falls
        # back to the zip decoder (BadZipFile).  Pin an explicit tarball name.
        get(
            self,
            **self.conan_data["sources"],
            strip_root=True,
            filename="mbrola-3.3.tar.gz",
        )

    def _cc(self):
        # R33: the compiler comes from the Conan profile, never from shell env.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        return compilers.get("c") or "clang"

    def _sign_binary(self, binary_path):
        # OHOS CI workers need signed ELF binaries to execute them; the device
        # and local runs simply skip this step when the tool is absent.
        if self.settings.os != "OHOS" or not os.path.isfile(binary_path):
            return
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(sign_tool):
            return
        if os.path.isfile(objcopy):
            self.run(f'"{objcopy}" --remove-section .codesign "{binary_path}" 2>/dev/null || true')
        signed_path = f"{binary_path}.signed"
        self.run(
            f'"{sign_tool}" sign -inFile "{binary_path}" '
            f'-outFile "{signed_path}" -selfSign 1',
            quiet=True,
        )
        if os.path.isfile(signed_path):
            os.replace(signed_path, binary_path)
            os.chmod(binary_path, 0o755)

    def build(self):
        apply_conandata_patches(self)
        # R9: -j1; the upstream Makefile keeps its own portability defines.
        self.run(f'make -j1 SHELL=sh CC="{self._cc()}"', cwd=self.source_folder)
        self._sign_binary(os.path.join(self.source_folder, "Bin", "mbrola"))

    def package(self):
        copy(
            self,
            "mbrola",
            src=os.path.join(self.source_folder, "Bin"),
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "README.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "doc", "mbrola"),
            keep_path=False,
        )
        self._sign_binary(os.path.join(self.package_folder, "bin", "mbrola"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
