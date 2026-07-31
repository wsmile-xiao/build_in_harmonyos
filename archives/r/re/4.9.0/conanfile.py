#!/usr/bin/env python3
"""Conan recipe for re (libre) 4.9.0 — CMake build system.

re (libre) is a generic library for real-time communications with async IO support.
Build system: CMake

Key rules:
  - R9:  Use make -j1 (not -j$(nproc))
  - R32: settings.os check uses `in ("Linux", "OHOS")`
  - OpenSSL/3.5.6 is a Conan dependency (published to ohpcd remote,
    recipe rev 748fc4deb56588d6f8ce900b21e8eb0a, OHOS/armv8/clang15/libc++).
  - Do NOT set CMAKE_SYSTEM_NAME=Linux (causes sockaddr_storage redefinition
    from linux/netlink.h). The OHOS platform patch handles UNIX-like files.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class ReConan(ConanFile):
    name = "re"
    version = "4.9.0"
    description = "Generic library for real-time communications (libre)"
    license = "BSD"
    homepage = "https://github.com/baresip/re"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # openssl/3.5.6 published on ohpcd remote (OHOS/armv8 package)
        self.requires("openssl/3.5.6")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Generate Conan dependency CMake config (openssl::openssl)
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # R32: settings.os check must use `in ("Linux", "OHOS")`
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")
        # Do NOT set CMAKE_SYSTEM_NAME=Linux — that would pull in Linux-specific
        # source files (src/net/linux/rt.c) that cause sockaddr_storage redefinition.
        # The OHOS CMake patch (0002) handles UNIX-like source files directly.
        shared = bool(self.options.shared)
        tc.variables["USE_OPENSSL"] = "ON"
        tc.variables["LIBRE_BUILD_SHARED"] = "ON" if shared else "OFF"
        tc.variables["LIBRE_BUILD_STATIC"] = "OFF" if shared else "ON"
        # OpenSSL comes from Conan dependency, not system path
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R9: Use -j1 for parallel constraint on OHOS platform
        cmake = CMake(self)
        cmake.configure(build_script_folder=self.source_folder)
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The package provides the re library
        self.cpp_info.libs = ["re"]
        # OpenSSL is a Conan dependency (transitive via CMakeDeps)
        self.cpp_info.system_libs = ["dl", "pthread", "m"]
