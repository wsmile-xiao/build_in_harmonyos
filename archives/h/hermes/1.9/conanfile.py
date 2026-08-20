#!/usr/bin/env python3
"""Conan recipe — Hermes JavaScript Engine (Facebook/Meta).

Build system: CMake
Source: github.com/facebook/hermes (tag hermes-v260318099.0.1, CMake VERSION 1.0.0)
License: MIT

Key OHOS adaptations:
  - HERMES_UNICODE_LITE=ON: skip ICU dependency (same as Android/Emscripten builds)
  - BOOST_CONTEXT_ARCHITECTURE=arm64 + BOOST_CONTEXT_ABI=aapcs: fix wrong arch detection
  - Patch 0001: add HarmonyOS platform detection in LLVM host triple + LLVM_ON_UNIX
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class HermesConan(ConanFile):
    name = "hermes"
    version = "1.9"
    description = "Hermes is a JavaScript engine optimized for fast start-up and performance on React Native"
    license = "MIT"
    homepage = "https://github.com/facebook/hermes"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS: skip ICU dependency (same approach as Android/Emscripten)
        tc.variables["HERMES_UNICODE_LITE"] = "ON"
        tc.variables["HERMES_ENABLE_WIN10_ICU_FALLBACK"] = "OFF"
        # OHOS: fix Boost.Context architecture detection (CMAKE_SYSTEM_PROCESSOR empty on OHOS)
        tc.variables["BOOST_CONTEXT_ARCHITECTURE"] = "arm64"
        tc.variables["BOOST_CONTEXT_ABI"] = "aapcs"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
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
        self.cpp_info.libs = ["hermes"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
