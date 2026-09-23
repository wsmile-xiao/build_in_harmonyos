#!/usr/bin/env python3
"""Conan recipe for zsign 1.1.1 — cross-platform iOS code signing tool (raw Makefile).

Upstream layout: pure Makefile at build/linux/Makefile (no configure/cmake).
It builds vendored zlib + minizip in-tree and links only libcrypto from the
external OpenSSL dependency (CMS/PKCS12/OCSP/X.509 paths; zsign never uses
libssl). The OpenSSL 3.x line is a hard requirement: src/signing.cpp calls
OSSL_PROVIDER_load() unconditionally.

Produces the `zsign` executable. Adapted for HarmonyOS OHOS (aarch64-linux-ohos).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ZsignConan(ConanFile):
    name = "zsign"
    version = "1.1.1"
    description = "zsign — fast cross-platform iOS code signing tool (re-sign IPA/Mach-O without Xcode)"
    license = "MIT"
    homepage = "https://github.com/zhlynn/zsign"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libcrypto only (CMS/PKCS12/OCSP/X.509); OpenSSL 3.x required for
        # the unconditional OSSL_PROVIDER_load() in src/signing.cpp.
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: get compilers from Conan conf, never from bare shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"

        openssl = self.dependencies["openssl"].cpp_info
        openssl_include = " ".join(f"-I{d}" for d in openssl.includedirs)
        openssl_libdirs = " ".join(f"-L{d}" for d in openssl.libdirs)

        makefile_dir = os.path.join(self.source_folder, "build", "linux")
        # R9: -j1 only. The upstream Makefile also hardcodes -std=c++11 -O3 in
        # CXXFLAGS and resolves sources/outputs via ../../ relative paths, so it
        # must be invoked from build/linux/ (make -C).
        # VERSION must be passed explicitly: the release tarball carries no .git,
        # and the Makefile otherwise embeds "0.0.0-dev" (zsign -v would misreport).
        self.run(
            f'make -C "{makefile_dir}" CC={cc} CXX={cxx} VERSION={self.version} '
            f'OPENSSL_INCLUDE="{openssl_include}" '
            f'OPENSSL_LIB="{openssl_libdirs} -lcrypto" -j1',
            cwd=self.source_folder,
        )

    def package(self):
        # The Makefile writes the binary to <src>/bin/zsign (BINDIR=../../bin).
        copy(self, "zsign", os.path.join(self.source_folder, "bin"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
