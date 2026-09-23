#!/usr/bin/env python3
"""Conan recipe for fdk-aac-encoder 1.0.9 — fdkaac CLI encoder.

fdkaac is nu774's command-line AAC encoder front-end for the
Fraunhofer FDK-AAC codec library. Products: fdkaac (CLI binary).

Build system: CMake (upstream primary; configure.ac exists but CMake is
the officially maintained path — see notes.md).

Dependencies:
  - fdk-aac: the codec library (found via pkg_check_modules(fdk-aac))
  - libsndfile: declared for the toolchain family; upstream CMakeLists
    does not link it (WAV parsing is built-in) but it is part of the
    audio toolchain this encoder belongs to.

R32: settings.os check uses in ("Linux", "OHOS").
R33: No hardcoded shell env vars — flags come from CMakeToolchain.
R34: test_package encodes real PCM and inspects the M4A output.
R38: CLI binary product → commands.json at software level.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class FdkAacEncoderConan(ConanFile):
    name = "fdk-aac-encoder"
    version = "1.0.9"
    description = (
        "fdkaac — command-line AAC encoder front-end for the "
        "Fraunhofer FDK-AAC codec library"
    )
    license = "Zlib"
    homepage = "https://github.com/nu774/fdkaac"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"fdk-aac-encoder is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("fdk-aac/2.0.3")
        self.requires("libsndfile/1.2.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Upstream CMakeLists.txt locates libfdk-aac via
        # pkg_check_modules(FDK_AAC REQUIRED fdk-aac), so PkgConfigDeps
        # must provide fdk-aac.pc (default .pc name == package name).
        pkg = PkgConfigDeps(self)
        pkg.generate()
        # Minimal CMake parameters (R1): prefix/install handled by Conan.
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # fdk-aac-encoder is a CLI application, not a library.
        self.cpp_info.bindirs = ["bin"]
