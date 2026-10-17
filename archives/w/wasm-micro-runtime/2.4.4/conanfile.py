#!/usr/bin/env python3
"""Conan recipe - wasm-micro-runtime 2.4.4."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, replace_in_file
import os


class WasmMicroRuntimeConan(ConanFile):
    name = "wasm-micro-runtime"
    version = "2.4.4"
    description = "WebAssembly Micro Runtime (WAMR) - a lightweight, standalone WebAssembly runtime"
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://github.com/bytecodealliance/wasm-micro-runtime"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # WAMR platform: HarmonyOS is not natively supported, use Linux platform
        tc.variables["WAMR_BUILD_PLATFORM"] = "linux"
        # WAMR target: explicitly set AARCH64 for armv8 (avoid auto-detect issues)
        tc.variables["WAMR_BUILD_TARGET"] = "AARCH64"
        tc.generate()

    def build(self):
        # Patch simde FetchContent to use URL download instead of git clone
        # (GitHub may not be directly accessible in some build environments)
        simde_cmake = os.path.join(self.source_folder,
                                   "core/iwasm/libraries/simde/simde.cmake")
        if os.path.exists(simde_cmake):
            replace_in_file(self, simde_cmake,
                            "GIT_REPOSITORY  https://github.com/simd-everywhere/simde\n    GIT_TAG v0.8.2",
                            "URL https://gh-proxy.com/https://github.com/simd-everywhere/simde/archive/refs/tags/v0.8.2.tar.gz")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["iwasm"]
        self.cpp_info.set_property("cmake_file_name", "iwasm")
        self.cpp_info.set_property("cmake_target_name", "iwasm::iwasm")
        self.cpp_info.system_libs = ["m", "dl", "pthread"]
