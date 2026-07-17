#!/usr/bin/env python3
"""Conan recipe — showkey 1.10 (Makefile).

showkey is a single-file C utility that echoes raw keystrokes from a tty in
printable form. Plain Makefile build (no configure/autotools/cmake), no
external dependencies (POSIX termios + libc only).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ShowkeyConan(ConanFile):
    name = "showkey"
    version = "1.10"
    description = "Display cooked key sequences from a terminal (keystroke echoer)"
    license = "MIT"
    homepage = "https://gitlab.com/esr/showkey"
    url = "https://gitlab.com/esr/showkey"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: showkey needs a POSIX tty (termios) — Linux/OHOS only.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"showkey requires a POSIX tty (Linux/OHOS), got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: use the OHOS SDK clang declared in the Conan profile
        # (tools.build:compiler_executables). The bare `clang` on PATH is the
        # host (Alpine) compiler and would build a non-OHOS binary.
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc = (compilers or {}).get("c") or "clang"
        # Plain Makefile: `all` builds the `showkey` binary from showkey.c.
        self.run(f'make CC="{cc}" -j1')

    def package(self):
        # Makefile `install` needs asciidoctor to build the man page (unavailable
        # on OHOS), so install just the binary.
        copy(self, "showkey", self.build_folder, os.path.join(self.package_folder, "bin"))
        # HarmonyOS: an ELF must be signed to execute. The signer lives only on
        # the release worker; skip when absent (local musl rootfs runs unsigned
        # binaries fine, so container verification still works).
        bin_path = os.path.join(self.package_folder, "bin", "showkey")
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool) and os.path.exists(objcopy):
            tmp_signed = bin_path + ".signed"
            self.run(f"{objcopy} --remove-section .codesign {bin_path}", quiet=True)
            self.run(
                f"{sign_tool} sign -inFile {bin_path} -outFile {tmp_signed} -selfSign 1",
                quiet=True,
            )
            os.replace(tmp_signed, bin_path)
            os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
