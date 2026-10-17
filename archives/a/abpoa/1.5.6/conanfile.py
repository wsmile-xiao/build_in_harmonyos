#!/usr/bin/env python3
"""Conan recipe for abpoa — CMake-based build with SIMDE for cross-platform SIMD support."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, mkdir
import os, shutil


class AbpoaConan(ConanFile):
    name = "abpoa"
    version = "1.5.6"
    description = "abPOA: an SIMD-based C library for fast partial order alignment using adaptive band"
    license = "MIT"
    homepage = "https://github.com/yangao07/abpoa"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Download simde (git submodule) headers for cross-platform SIMD support
        simde_dir = os.path.join(self.source_folder, "include", "simde")
        if not os.path.exists(os.path.join(simde_dir, "simde", "x86", "sse2.h")):
            mkdir(self, simde_dir)
            simde_url = "https://github.com/simd-everywhere/simde/archive/refs/tags/v0.8.2.tar.gz"
            get(self, simde_url, destination=simde_dir, strip_root=True,
                sha256="ed2a3268658f2f2a9b5367628a85ccd4cf9516460ed8604eed369653d49b25fb")

    def generate(self):
        tc = CMakeToolchain(self)
        # Note: SIMDE flags (-DUSE_SIMDE -DSIMDE_ENABLE_NATIVE_ALIASES) are set
        # in CMakeLists.txt via patch, guarded to aarch64/arm64 only.
        # The OHOS cross toolchain leaves CMAKE_SYSTEM_PROCESSOR empty, so pass
        # the arch from conan settings explicitly for a reliable guard.
        arch = str(self.settings.arch)
        if arch in ("armv8", "armv8.1", "armv8.2", "armv8.3", "aarch64", "arm64"):
            tc.variables["ABPOA_ARM64"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Remove .git and test data from simde installation
        simde_inc = os.path.join(self.package_folder, "include", "simde")
        excluded_dirs = {".git", "test", "docker", ".circleci", ".github",
                         ".packit", ".no-test"}
        for root, dirs, files in os.walk(simde_inc, topdown=True):
            for d in list(dirs):
                if d in excluded_dirs:
                    shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                    dirs.remove(d)
        # Also copy the abpoa.pc.in for pkg-config
        copy(self, "abpoa-1.pc",
             src=os.path.join(self.build_folder),
             dst=os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["abpoa"]
        self.cpp_info.requires = ["zlib::zlib"]
        # simd_instruction.h includes x86-only <immintrin.h> unless USE_SIMDE
        # is defined; propagate the SIMDE macros so consumers (test_package)
        # compile with the SIMDe emulation layer on non-x86 (aarch64/OHOS) only.
        # On x86_64 the library uses native SSE/AVX, so the SIMDE defines must
        # NOT be propagated (they would shadow native SIMD with emulation).
        arch = str(self.settings.arch)
        if arch in ("armv8", "armv8.1", "armv8.2", "armv8.3", "aarch64", "arm64"):
            self.cpp_info.defines = ["USE_SIMDE", "SIMDE_ENABLE_NATIVE_ALIASES"]