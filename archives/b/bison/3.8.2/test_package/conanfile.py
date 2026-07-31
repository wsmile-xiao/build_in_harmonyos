#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

Uses direct compilation (like blake3) to keep test simple and portable.
CI L0d requires self.run() in this file.

File location: archives/{letter}/bison/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile


class BisonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # bison is a CLI tool, not a library: test.c uses only standard C
        # headers and invokes the bison binary via system(). No -I/-L/-l
        # flags from cpp_info are needed (they'd reference dirs that don't
        # exist for a tool package and break under strict compilers).
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test.c -o test_bison")

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, so wrap
        # binary execution with bash. Prefer CONFIG_SHELL (set by the build
        # env), then common OHOS/Linux locations, then bare 'bash' (Conan's
        # conanrun env already puts bash on PATH for OHOS toolchain nodes).
        bash = os.environ.get("CONFIG_SHELL") or next(
            (p for p in (
                "/data/service/hnp/bin/bash",
                "/bin/bash",
                "/usr/bin/bash",
            ) if os.path.exists(p)),
            "bash",
        )
        # bison's compiled-in pkgdatadir is /share/bison (from --prefix=),
        # so we must redirect BISON_PKGDATADIR to the actual location
        # inside the Conan package where the share/bison/ data live.
        bison_pkg = self.dependencies["bison"].package_folder
        bison_pkgdatadir = os.path.join(bison_pkg, "share", "bison")
        self.run(
            f"BISON_PKGDATADIR={bison_pkgdatadir} {bash} -c './test_bison'",
            env="conanrun",
        )
