#!/usr/bin/env python3
"""Conan recipe — glaze 8.3.0 (C++23 header-only JSON/BEVE serialization).

Glaze is a very fast, dependency-free, header-only serialization and
reflection library (JSON, BEVE, CSV, TOML, and more formats). The recipe
installs the public headers together with the upstream CMake package config
via the upstream INTERFACE target, mirroring the 7bitdi header-only variant.

OHOS notes:
- OHOS toolchain is clang 15 with libc++ 15. Portability patches restore
  upstream's own historical code paths (util/expected fallback, non-static
  constexpr locals) and replace C++20/23 algorithms missing from libc++ 15.
  All patches are guarded by feature macros or equivalent portable syntax;
  none contain platform conditionals.
- Upstream requires C++23 (target_compile_features cxx_std_23). The OHOS
  profile pins cppstd=17, so the package declares the requirement to
  consumers via cpp_info.cxxflags (see package_info) and the downstream
  minimum standard is documented in manifest.yaml and notes.md.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class GlazeConan(ConanFile):
    name = "glaze"
    version = "8.3.0"
    description = "Very fast, dependency-free, header-only C++23 serialization and reflection library (JSON, BEVE, CSV and more)"
    license = "MIT"
    homepage = "https://github.com/stephenberry/glaze"
    url = "https://github.com/stephenberry/glaze"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Glaze depends only on the C++ standard library; no Conan dependencies.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R32: keep the recipe valid for Linux and OHOS profiles. The OHOS
        # CMake platform module expects the aarch64 processor spelling.
        if self.settings.os in ("Linux", "OHOS"):
            tc.blocks["generic_system"].values["cmake_system_name"] = str(
                self.settings.os
            )
            if self.settings.os == "OHOS":
                tc.blocks["generic_system"].values["cmake_system_processor"] = (
                    "aarch64"
                )
        # Upstream defaults glaze_DEVELOPER_MODE to ON for top-level projects
        # (cmake/variables.cmake), which pulls tests/ (FetchContent ut) and
        # fuzzing/ into every consumer configure. As a package we only build
        # the INTERFACE library, so turn developer extras off explicitly.
        tc.cache_variables["glaze_DEVELOPER_MODE"] = "OFF"
        tc.cache_variables["glaze_ENABLE_FUZZING"] = "OFF"
        tc.cache_variables["glaze_BUILD_EXAMPLES"] = "OFF"
        tc.generate()

    def build(self):
        # Header-only INTERFACE target: configure + build validate the
        # upstream CMake package (no translation units are compiled).
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Header-only: headers installed by the upstream CMake install rules.
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "glaze")
        self.cpp_info.set_property("cmake_target_name", "glaze::glaze")
        # Upstream's installed config carries
        # target_compile_features(glaze::glaze INTERFACE cxx_std_23). Conan
        # CMakeDeps consumers do not read that config, so propagate the
        # requirement here; otherwise a cppstd=17 profile builds consumers
        # as C++17 and the headers fail to compile. -std=c++2b is accepted
        # by clang 12+ and gcc 11+ (c++23 alias).
        self.cpp_info.cxxflags = ["-std=c++2b"]
