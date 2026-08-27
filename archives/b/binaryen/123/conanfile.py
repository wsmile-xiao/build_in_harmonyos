#!/usr/bin/env python3
"""Conan recipe for binaryen 123 — WebAssembly compiler toolchain and optimizer.

binaryen provides both a static library (libbinaryen.a) and command-line tools
(wasm-opt, wasm-as, wasm-dis, wasm2js, etc.).

Key adaptation: BUILD_STATIC_LIB=ON avoids CMake RPATH issues on OHOS.
BUILD_TESTS=OFF avoids missing googletest submodule in source tarball.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class BinaryenConan(ConanFile):
    name = "binaryen"
    version = "123"
    description = "Compiler infrastructure and toolchain for WebAssembly"
    license = "Apache-2.0"
    homepage = "https://github.com/WebAssembly/binaryen"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: static build to avoid OHOS RPATH issues
        tc.variables["BUILD_STATIC_LIB"] = "ON"
        # Disable tests: googletest submodule not included in source tarball
        tc.variables["BUILD_TESTS"] = "OFF"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        tc.generate()

        # Fix: lld linker from OHOS SDK requires libxml2.so.16
        # The library is in the SDK lib dir but not in the default search path on CI
        env = Environment()
        sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        env.define("LD_LIBRARY_PATH", sdk_lib)
        envvars = env.vars(self)
        envvars.save_script("binaryen_ld_path")

    def build(self):
        # Ensure lld can find libxml2.so.16 during cmake compiler check
        sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        current_ld = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = sdk_lib + (":" + current_ld if current_ld else "")

        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["binaryen"]
        self.cpp_info.includedirs = ["include"]
        # libbinaryen.a is C++ — consumers need libc++ to link
        self.cpp_info.system_libs = ["c++_shared"]
        # binaryen also installs command-line tools to bin/
        self.cpp_info.bindirs = ["bin"]
