#!/usr/bin/env python3
"""Conan recipe — bossa 1.9.1 (Makefile)

BOSSA (Basic Open Source SAM-BA Application) — Flash programmer for
Atmel SAM microcontrollers. Provides CLI tool bossac.
GUI tool bossa requires wxWidgets (unavailable on OHOS), not built.
bossash (interactive shell) is not built — it requires readline headers
not available on all CI workers.

Build system: pure Makefile (no configure).
The Makefile detects OS via `uname -s | cut -c -7`. On OHOS this returns
"Harmony" which matches no platform rule, so we override OS=Linux to get
PosixSerialPort.cpp and LinuxPortFactory.cpp (OHOS is POSIX-compatible).
Make targets are path-based: bin/bossac (not bare names).
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BossaConan(ConanFile):
    name = "bossa"
    version = "1.9.1"
    description = "Flash programmer for Atmel SAM microcontrollers (bossac CLI tool)"
    license = "BSD-3-Clause"
    homepage = "https://www.shumatech.com/forum/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS platform compatibility
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self, build_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, never from shell env vars
        # Conan 2.29.1: tools.build:compiler_executables is a dict, not individual keys
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"

        # E120/E132: OHOS SDK lld linker depends on libxml2.so.16 from SDK's llvm/lib
        sdk_lib_dirs = glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")
        if sdk_lib_dirs:
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = f"{sdk_lib_dirs[0]}:{existing}" if existing else sdk_lib_dirs[0]

        # Build only CLI tool: bin/bossac (not bossash which requires readline,
        # not GUI bossa which needs wxWidgets)
        # OS=Linux: OHOS uname returns "Harmony" which matches no Makefile platform rule;
        #   overriding to Linux activates PosixSerialPort.cpp + LinuxPortFactory.cpp (OHOS is POSIX)
        # VERSION=1.9.1 overrides `git describe` which fails in non-git source dir
        # R9: Always use -j1
        self.run(
            f'make OS=Linux CXX={cxx} VERSION=1.9.1 '
            f'CXXFLAGS="-fPIC -O2 -Wno-error" '
            f'bin/bossac -j1'
        )

    def package(self):
        # Copy built binary from source bin/ to package bin/
        copy(self, "bossac", os.path.join(self.source_folder, "bin"),
             os.path.join(self.package_folder, "bin"))

        # OHOS: ELF binaries must be signed to be executable
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        bin_name = "bossac"
        bin_path = os.path.join(self.package_folder, "bin", bin_name)
        if os.path.exists(sign_tool) and os.path.exists(bin_path):
            signed_path = bin_path + ".signed"
            self.run(
                f"{sign_tool} sign -selfSign 1 "
                f"-inFile {bin_path} -outFile {signed_path} "
                f"-signAlg SHA256withECDSA -keyAlias {bin_name}"
            )
            os.replace(signed_path, bin_path)
            os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
