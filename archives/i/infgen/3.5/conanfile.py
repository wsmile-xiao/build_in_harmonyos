#!/usr/bin/env python3
"""Conan recipe for infgen 3.5 — DEFLATE (RFC 1951) stream disassembler.

infgen is a single-file C command-line tool by Mark Adler (zlib author). It
reads a gzip, zlib, PNG, or raw deflate stream and writes a readable
description of its contents. It is built by directly compiling infgen.c and
linking zlib (crc32()/get_crc_table(), used for PNG input chunk CRCs).

Upstream publishes no git tags; version 3.5 corresponds to commit c6fe0c3
("Update version to 3.5.", 2024-12-26).

License: zlib.
"""
import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class InfgenConan(ConanFile):
    name = "infgen"
    version = "3.5"
    description = "DEFLATE (RFC 1951) stream disassembler"
    license = "Zlib"
    homepage = "https://github.com/madler/infgen"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # zlib is statically embedded into the executable (crc32 for PNG input).
        self.requires("zlib/1.3.1")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS"), never == "Linux".
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"infgen only supports Linux/OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        # R33: compiler from Conan conf, never from bare shell env vars.
        comps = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return comps.get("c") or "clang"

    def _sign_elf(self, path):
        """Sign the ELF binary so it is executable on HarmonyOS (E077).

        binary-sign-tool only exists on OHOS; on Linux build hosts this is a
        no-op, leaving CI's release sign.sh to do the final signing.
        """
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if Path(sign_tool).exists():
            self.run(f"{objcopy} --remove-section .codesign {path} || true")
            self.run(
                f"{sign_tool} sign -inFile {path} -outFile {path}.signed -selfSign 1"
            )
            shutil.move(f"{path}.signed", path)
        os.chmod(path, 0o755)

    def build(self):
        cc = self._cc()
        zlib = self.dependencies["zlib"]
        cflags = " ".join(f"-I{d}" for d in zlib.cpp_info.includedirs)
        ldflags = " ".join(f"-L{d}" for d in zlib.cpp_info.libdirs)
        # Upstream ships no Makefile; compile the single-file program directly.
        self.run(
            f'cd "{self.source_folder}" && '
            f"{cc} -O2 -Wall {cflags} {ldflags} -o infgen infgen.c -lz"
        )
        if self.settings.os == "OHOS":
            self._sign_elf(os.path.join(self.source_folder, "infgen"))

    def package(self):
        copy(self, "infgen", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder,
             os.path.join(self.package_folder, "share", "infgen", "doc"))

    def package_info(self):
        # CLI tool — no public library interface; zlib is statically embedded.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
