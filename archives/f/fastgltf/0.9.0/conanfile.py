#!/usr/bin/env python3
"""Conan recipe — fastgltf 0.9.0 (CMake project).

fastgltf is a glTF 2.0 loader written in C++17, built via CMake.
Upstream dependency: simdjson (bundled/downloaded via FetchContent if not found).
Recipe follows the skill CMake template (R26: BUILD_SHARED_LIBS=OFF for static).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class FastgltfConan(ConanFile):
    name = "fastgltf"
    version = "0.9.0"
    description = "A speed and usability focused glTF 2.0 library written in modern C++17"
    license = "MIT"
    homepage = "https://github.com/spnda/fastgltf"
    url = "https://github.com/spnda/fastgltf/archive/refs/tags/v0.9.0.tar.gz"

    package_type = "library"
    generators = "CMakeDeps"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # simdjson is a hard runtime dependency of fastgltf (parsing engine).
        # The upstream CMake falls back to downloading singleheader simdjson;
        # using the published conan package keeps the build reproducible and
        # satisfies R36 (dependencies published before consumers).
        self.requires("simdjson/4.6.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: static linking default
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Do not build tests/examples/docs inside the recipe build.
        tc.variables["FASTGLTF_ENABLE_TESTS"] = "OFF"
        tc.variables["FASTGLTF_ENABLE_EXAMPLES"] = "OFF"
        tc.variables["FASTGLTF_ENABLE_DOCS"] = "OFF"
        # Depend on the conan-provided simdjson so the upstream CMake does not
        # try to download the singleheader bundle at configure time.
        tc.variables["SIMDJSON_TARGET_VERSION"] = "4.6.3"
        # fastgltf uses ARMv8 CRC32 intrinsics (__crc32cd/...) on aarch64. The
        # OHOS clang 15 toolchain only exposes them when the crc feature is
        # enabled for the whole TU (arm_acle.h declares them under
        # __ARM_FEATURE_CRC32). Guard by os+arch so non-AArch64 targets are
        # not affected (R32/R33: no unconditional hardcoded flags).
        if self.settings.os in ("Linux", "OHOS") and str(self.settings.arch).startswith("armv8"):
            tc.extra_cflags.append("-march=armv8.2-a+crc")
            tc.extra_cxxflags.append("-march=armv8.2-a+crc")
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
        self.cpp_info.libs = ["fastgltf"]
