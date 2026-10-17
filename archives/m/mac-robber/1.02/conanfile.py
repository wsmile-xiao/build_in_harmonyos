#!/usr/bin/env python3
"""Conan recipe for mac-robber 1.02 — filesystem MAC-times forensics CLI.

mac-robber collects Modified/Access/Change times from allocated files in a
mounted filesystem and prints them in 'time machine' (body file) format to
STDOUT, the same format the mactime tool from The Sleuth Kit reads. It is a
single-file C program (~369 lines) built with a hand-written Makefile.

OHOS adaptive build:
  - Compiler CC comes from Conan conf tools.build:compiler_executables
    (R33), never a bare shell var or hardcoded path.
  - The upstream Makefile hardcodes `CC = gcc` and `-static` in the default
    target, but provides a `linux_notstatic` target (non-static, with
    -D_FILE_OFFSET_BITS=64) that we use; CC is overridable on the make
    command line (assignment in file is overridden by command-line vars).
  - One minimal source patch (0001-maxnamlen-musl.patch) defines MAXNAMLEN
    for musl <dirent.h> which does not ship the BSD/glibc macro; no logic
    is changed.
  - No run-time dependencies (single C file, stdlib only).

Upstream tests: mac-robber 1.02 has NO test suite — no tests/ dir, no
check/test Makefile target, no TESTS/check_PROGRAMS in any build file.
The GitHub autotools port (maintainer Brian Carrier) likewise declares no
check_PROGRAMS/TESTS and its CI only runs configure+make. See
test_package/MANIFEST.yml for the full audit.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MacRobberConan(ConanFile):
    name = "mac-robber"
    version = "1.02"
    package_type = "application"

    description = "Collects MAC times from allocated files in mounted filesystems (forensics CLI)"
    license = "GPL-2.0"
    homepage = "https://sleuthkit.org/mac-robber/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("forensics", "mac-times", "filesystem", "cli", "sleuthkit")

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, not shell env vars.
        # Profile sets tools.build:compiler_executables to the OHOS clang.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        # If the configured path exists, use it directly; otherwise fall back
        # to basename lookup via shutil.which (portable, no hardcoded paths).
        if os.path.isfile(cc):
            cc_bin = cc
        else:
            cc_bin = shutil.which(os.path.basename(cc)) or cc

        # Verify the compiler target triple is OHOS aarch64.
        triple = self._target_triple(cc_bin)
        if triple and "ohos" not in triple:
            self.output.warn(f"compiler triple '{triple}' is not an OHOS target")
        self.output.info(f"using CC: {cc_bin} (triple: {triple or 'unknown'})")

        # Use the linux_notstatic target: non-static + -D_FILE_OFFSET_BITS=64.
        # CC is overridden on the make command line (overrides the file-level
        # `CC = gcc`). No Makefile patch is needed for CC or flags.
        self.run(f'make CC="{cc_bin}" linux_notstatic -j1', cwd=self.source_folder)

    @staticmethod
    def _target_triple(cc):
        import subprocess
        for flag in ("-print-target-triple", "-dumpmachine"):
            try:
                out = subprocess.run(
                    [cc, flag], capture_output=True, text=True, timeout=10)
                if out.returncode == 0 and out.stdout.strip():
                    return out.stdout.strip()
            except Exception:
                continue
        return ""

    def package(self):
        copy(self, "mac-robber", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
