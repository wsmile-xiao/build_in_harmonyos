#!/usr/bin/env python3
"""Conan recipe for unshield 1.6.2 on HarmonyOS PC (aarch64).

unshield is a tool and library to extract files from InstallShield CAB files.
It uses CMake build system and requires zlib for decompression.
zlib/1.3.1.1 (-fPIC variant) is required because libunshield.so links
against the static libz.a and aarch64 requires position-independent code.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches


class UnshieldConan(ConanFile):
    name = "unshield"
    version = "1.6.2"
    package_type = "library"
    description = "Tool to extract InstallShield CAB files"
    license = "MIT"
    homepage = "https://github.com/twogood/unshield"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # zlib is required for CAB file decompression.
        # Use 1.3.1.1 (-fPIC static lib): static libz.a links into
        # libunshield.so; 1.3.1 would cause R_AARCH64 relocation errors.
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Use own MD5 implementation to avoid OpenSSL dependency
        tc.variables["USE_OUR_OWN_MD5"] = "ON"
        # Disable OpenSSL auto-detection
        tc.variables["OPENSSL_ROOT_DIR"] = ""
        # Use link path in RPATH so $ORIGIN/../lib resolves correctly
        tc.variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # unshield-deobfuscate has no install() target in upstream CMakeLists.txt,
        # so copy it manually. The binary is at build_folder/src/unshield-deobfuscate.
        deobf_src = os.path.join(self.build_folder, "src", "unshield-deobfuscate")
        if os.path.exists(deobf_src):
            copy(self, "unshield-deobfuscate",
                 src=os.path.dirname(deobf_src),
                 dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["unshield"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]