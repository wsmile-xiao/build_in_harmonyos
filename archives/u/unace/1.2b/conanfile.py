#!/usr/bin/env python3
"""Conan recipe for unace 1.2b — command-line ACE archive extractor.

unace 1.2b is the GPL public UNACE (1998/2004). The unix build is a raw
make over 7 C sources (make -f unix/makefile): no configure script, no
upstream test suite, no external dependencies.

OHOS specifics:
- The shipped makefile hardcodes `gcc` on the link line; patches/0003 switches
  it to $(CC) and the recipe passes CC= from Conan conf (R33).
- LP64: declare.h typedefs ULONG/LONG as (unsigned) long, while the ACE
  on-disk structures are 32-bit; patches/0002 pins them to int width.
- read_header skips a file-header ADDSIZE field without advancing the parse
  pointer, shifting every later field by one slot; patches/0001 fixes it.
- aarch64 is little-endian: os.h leaves both byte-order macros undefined
  for UNIX and portable.h then reads host-order directly, which is correct;
  no byte-order define is injected.
- HMDFS is case-insensitive, so -DCASEINSENSE (the upstream default for
  such filesystems) is kept.
- ELF signing follows the unzip/6.0 recipe pattern.
"""
import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class UnaceConan(ConanFile):
    name = "unace"
    version = "1.2b"
    description = "Command-line tool for extracting ACE archives"
    license = "GPL-2.0"
    homepage = "https://deb.debian.org/debian/pool/main/u/unace/"
    url = "https://deb.debian.org/debian/pool/main/u/unace/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # unace has no external dependencies

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_cc(self):
        # R33: get compiler from Conan conf, never from undefined shell env vars
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp_execs.get("c") or "clang"

    def _needs_ohos_workarounds(self):
        # R32: settings.os check must include both Linux and OHOS
        return self.settings.os in ("Linux", "OHOS")

    def _sign_elf(self, path, src):
        """Sign ELF binary on OHOS for execution on HarmonyOS."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if Path(sign_tool).exists():
            self.run(f"{objcopy} --remove-section .codesign {path} || true", cwd=src)
            self.run(f"{sign_tool} sign -inFile {path} "
                     f"-outFile {path}.signed -selfSign 1", cwd=src)
            shutil.move(f"{path}.signed", path)
        else:
            self.output.warn(
                f"binary-sign-tool not found at {sign_tool}; "
                f"skipping ELF signing for {path}. "
                f"Binary may not be executable on OHOS target."
            )
        os.chmod(path, 0o755)

    def build(self):
        apply_conandata_patches(self)

        cc = self._get_cc()
        # -f unix/makefile: sources live in the archive root, the makefile in unix/.
        # CC= overrides the makefile's `CC = gcc` (a plain assignment); the makefile's
        # own ifeq branches add -DUNIX -DCASEINSENSE to CFLAGS for non-DOS shells.
        # R9: -j1, never -j$(nproc).
        self.run(f"make -f unix/makefile CC={cc} -j1", cwd=self.source_folder)

        if self._needs_ohos_workarounds():
            binpath = os.path.join(self.source_folder, "unace")
            if os.path.exists(binpath):
                self._sign_elf(binpath, self.source_folder)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "unace", self.source_folder, bindir)
        exe = os.path.join(bindir, "unace")
        if os.path.exists(exe):
            os.chmod(exe, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
