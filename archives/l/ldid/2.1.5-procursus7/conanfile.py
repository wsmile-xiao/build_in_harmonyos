#!/usr/bin/env python3
"""Conan recipe — ldid 2.1.5-procursus7 (Link Identity Editor).

ldid is a Mach-O pseudo-codesigning tool from the Procursus project.
It manipulates code signatures, entitlements, and requirements on
Mach-O binaries. On HarmonyOS it serves as a supplementary tool for
Mach-O format processing.

Build system: plain Makefile (no configure script).
Dependencies: libplist-2.0 (plist parsing), openssl/libcrypto (crypto).
License: AGPL-3.0-only
Homepage: https://github.com/ProcursusTeam/ldid

OHOS adaptations:
  - PkgConfigDeps generates .pc files for libplist-2.0 and openssl.
  - libcrypto.pc wrapper: ldid Makefile uses `pkg-config --cflags libcrypto`
    but Conan's openssl recipe generates openssl.pc (not libcrypto.pc).
    We create a libcrypto.pc in generate() to bridge this gap.
  - CC/CXX passed from Conan conf (R33: never use bare shell env vars).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout


class LdidConan(ConanFile):
    name = "ldid"
    version = "2.1.5-procursus7"
    description = "Link Identity Editor — Mach-O pseudo-codesigning tool"
    license = "AGPL-3.0-only"
    homepage = "https://github.com/ProcursusTeam/ldid"
    url = "https://github.com/ProcursusTeam/ldid"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ldid is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("libplist/2.3.0")
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        pc = PkgConfigDeps(self)
        pc.generate()

        # ldid Makefile uses `pkg-config --cflags libcrypto` but Conan's
        # openssl recipe generates openssl.pc (not libcrypto.pc).
        # Create a libcrypto.pc wrapper that mirrors openssl.pc but only
        # links -lcrypto (drops -lssl which ldid doesn't need).
        gen_dir = self.generators_folder
        openssl_pc = os.path.join(gen_dir, "openssl.pc")
        if os.path.exists(openssl_pc):
            with open(openssl_pc, "r") as f:
                content = f.read()
            content = content.replace("Name: openssl", "Name: libcrypto")
            content = content.replace(
                "Description: Conan package: openssl",
                "Description: libcrypto (from openssl)",
            )
            content = content.replace("-lssl -lcrypto", "-lcrypto")
            libcrypto_pc = os.path.join(gen_dir, "libcrypto.pc")
            with open(libcrypto_pc, "w") as f:
                f.write(content)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan settings (never bare shell env vars)
        cc = "clang" if str(self.settings.compiler) == "clang" else "gcc"
        cxx = "clang++" if str(self.settings.compiler) == "clang" else "g++"

        # R9: Always use -j1
        # The Makefile uses pkg-config internally to find libplist-2.0 and
        # libcrypto. PkgConfigDeps generates .pc files in the generators
        # folder; we set PKG_CONFIG_PATH explicitly to ensure make's
        # $(shell pkg-config ...) calls find them.
        gen_dir = self.generators_folder
        self.run(
            f'PKG_CONFIG_PATH={gen_dir} make CC="{cc}" CXX="{cxx}" -j1',
            cwd=self.source_folder,
        )

    def package(self):
        bin_dst = os.path.join(self.package_folder, "bin")
        # Install ldid binary
        copy(self, "ldid", src=self.source_folder, dst=bin_dst)
        # Create ldid2 as a copy of ldid (symlinks are unreliable on HMDFS)
        ldid_path = os.path.join(bin_dst, "ldid")
        ldid2_path = os.path.join(bin_dst, "ldid2")
        if os.path.exists(ldid_path) and not os.path.exists(ldid2_path):
            shutil.copy2(ldid_path, ldid2_path)
        # Install man pages
        copy(self, "ldid.1", src=os.path.join(self.source_folder, "docs"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
