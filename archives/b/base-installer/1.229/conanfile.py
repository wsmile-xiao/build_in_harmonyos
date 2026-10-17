#!/usr/bin/env python3
"""Conan recipe for base-installer 1.229 — OHOS (OpenHarmony) aarch64 adaptation.

base-installer is the Debian installer's base system installation framework.
Source: https://salsa.debian.org/installer-team/base-installer (official, 1.229).

OHOS adaptation scope:
- pkgdetails: standalone C utility (parses Debian Packages files for
  dependencies) — builds cleanly with the OHOS clang toolchain (pure libc).
- kernel/<arch>.sh: per-architecture kernel selection scripts + regression test
  suite (make test) — installed as data; suite passes on all 21 arches.
- library.sh: debconf-based base-installation shell framework — installed as
  data (its Debian/udpkg runtime dependency is unavailable on OHOS).
- run-debootstrap: requires Debian-installer-only external libraries
  (cdebconf, libdebian-installer) that do not exist in the OHOS ecosystem
  (verified: 0 recipes in ohpcd registry) — excluded from the OHOS build;
  recorded as an external dependency block, see notes.md.

Build system: plain Makefile (TARGETS=pkgdetails).
No --build=missing; no external conan requirements.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BaseInstallerConan(ConanFile):
    name = "base-installer"
    version = "1.229"
    description = "Debian installer base system installation framework (pkgdetails + kernel selection)"
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/installer-team/base-installer"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # pkgdetails is pure libc; no external requirements.
        # run-debootstrap would need cdebconf/libdebian-installer (not in OHOS
        # ecosystem) — recorded as external block in notes.md, script excluded.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler from Conan conf, never from raw shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        # Build only pkgdetails (Makefile: `ifndef TARGETS`); run-debootstrap
        # depends on Debian-installer-only libs and is excluded on OHOS.
        # R9: -j1. basic_layout() separates build/source folders, so run
        # make -C against the source folder (Makefile lives there).
        self.run(
            f"make -C {self.source_folder} -j1 TARGETS=pkgdetails CC={cc}"
            f" CFLAGS='-Wall -O2 -D_GNU_SOURCE'"
        )

    def package(self):
        # R38: executable → bin/
        copy(self, "pkgdetails",
             src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        # Shell framework + per-arch kernel selection scripts → share data
        copy(self, "library.sh",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "base-installer"))
        copy(self, "*.sh",
             src=os.path.join(self.source_folder, "kernel"),
             dst=os.path.join(self.package_folder, "share", "base-installer", "kernel"))

        # R7: self-sign ELF binary on OHOS for local execution
        if self.settings.os in ("Linux", "OHOS"):
            pkg_path = os.path.join(self.package_folder, "bin", "pkgdetails")
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            if os.path.isfile(sign_tool) and os.path.isfile(pkg_path):
                signed_path = f"{pkg_path}.signed"
                self.run(
                    f'{sign_tool} sign -inFile "{pkg_path}"'
                    f' -outFile "{signed_path}"'
                    f' -selfSign 1 -signAlg SHA256withECDSA',
                    quiet=True
                )
                if os.path.isfile(signed_path):
                    os.replace(signed_path, pkg_path)
                    os.chmod(pkg_path, 0o755)

    def package_info(self):
        # command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]