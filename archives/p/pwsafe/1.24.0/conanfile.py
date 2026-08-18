#!/usr/bin/env python3
"""Conan recipe for pwsafe 1.24.0 — CMake build system.

Password Safe is a password management utility based on Bruce Schneier's
Blowfish algorithm. This recipe builds the CLI tool (pwsafe-cli) for
HarmonyOS PC (aarch64, musl/clang).

Key build options:
* NO_WX=ON      — CLI-only build, skip wxWidgets GUI
* NO_GTEST=ON   — Skip googletest unit tests
* NO_YUBI=ON    — Disable YubiKey support
* HARDEN_USE_SAFE_STACK=OFF — Workaround clang-15 ICE on AArch64

Dependencies: openssl, uuid, curl. libmagic is optional (auto-detected).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PwsafeConan(ConanFile):
    name = "pwsafe"
    version = "1.24.0"
    description = "Password management utility based on Bruce Schneier's Blowfish algorithm"
    license = "Artistic-2.0"
    homepage = "https://pwsafe.org/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6.1")
        self.requires("uuid/2.40.1")
        self.requires("curl/8.15.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["NO_WX"] = "ON"
        tc.variables["NO_GTEST"] = "ON"
        tc.variables["NO_YUBI"] = "ON"
        tc.variables["HARDEN_USE_SAFE_STACK"] = "OFF"
        tc.variables["USE_INTERPROCEDURAL_OPTIMIZATION"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
