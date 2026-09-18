#!/usr/bin/env python3
"""Conan recipe for lief 1.0.0 — CMake project (HarmonyOS PC aarch64).

- Builds the official release tarball from github.com/lief-project/LIEF (tag 1.0.0).
- Static library by default (BUILD_SHARED_LIBS=OFF), library package type.
- LIEF bundles its own third-party deps (mbedtls, spdlog, json, frozen, ...)
  via FetchContent from the shipped tarball; no external Conan requirements.
- Tests are enabled (LIEF_TESTS=ON) during adaptation and exercised via the
  upstream "unittests" target; tests disabled by default in the recipe.
- LIEF_DISABLE_EXCEPTIONS is ON by default upstream (exceptions disabled in
  the core library), which matches the OHOS toolchain without extra flags.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LiefConan(ConanFile):
    name = "lief"
    version = "1.0.0"
    description = "LIEF 1.0.0 — cross-platform library to parse, modify and abstract ELF, PE and MachO formats"
    license = "Apache-2.0"
    homepage = "https://lief.re"
    url = "https://github.com/lief-project/LIEF"

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
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["LIEF_PYTHON_API"] = "OFF"
        tc.variables["LIEF_EXAMPLES"] = "OFF"
        tc.variables["LIEF_C_API"] = "ON"
        tc.variables["LIEF_TESTS"] = "OFF"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["LIEF"]