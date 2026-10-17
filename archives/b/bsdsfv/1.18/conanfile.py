#!/usr/bin/env python3
"""Conan recipe — bsdsfv 1.18.

bsdsfv: command-line SFV (Simple File Verification) checksum utility.
Pure Makefile project (single C file), no configure script, no external deps.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BsdsfvConan(ConanFile):
    name = "bsdsfv"
    version = "1.18"
    description = "bsdsfv: command-line SFV (Simple File Verification) checksum utility"
    license = "BSD-2-Clause"
    homepage = "https://sourceforge.net/projects/bsdsfv/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: resolve the compiler from the Conan profile conf, never shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(compilers, dict):
            cc = compilers.get("c", "clang")
        else:
            cc = "clang"

        # Single-file C project: make CC=clang CFLAGS="-Wall -O2"
        self.run(
            f"make CC={cc} CFLAGS='-Wall -O2' -j1",
            cwd=self.source_folder,
            env="conanbuild")

    def package(self):
        # Executable goes to bin/
        copy(self, "bsdsfv", self.source_folder, os.path.join(self.package_folder, "bin"))
        # Upstream MANUAL is a plain-text document, not a man page
        copy(self, "MANUAL", self.source_folder, os.path.join(self.package_folder, "share", "doc", "bsdsfv"))

        # R7/OHOS: Self-sign ELF binary for local execution
        # OHOS requires ELF signatures; unsigned binaries get "Operation not permitted".
        # binary-sign-tool cannot overwrite an existing .codesign section (E077), so
        # remove the section first, then sign, then restore exec permission.
        if self.settings.os == "OHOS":
            bin_path = os.path.join(self.package_folder, "bin", "bsdsfv")
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            if os.path.isfile(sign_tool) and os.path.isfile(bin_path):
                # Step 1: remove existing .codesign section (must come first)
                self.run(
                    f'{objcopy} --remove-section .codesign "{bin_path}"',
                    quiet=True)
                # Step 2: re-sign
                signed_path = f"{bin_path}.signed"
                self.run(
                    f'{sign_tool} sign -inFile "{bin_path}"'
                    f' -outFile "{signed_path}"'
                    f' -selfSign 1 -signAlg SHA256withECDSA',
                    quiet=True
                )
                # Step 3: replace and restore exec permission
                if os.path.isfile(signed_path):
                    os.replace(signed_path, bin_path)
                    os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
