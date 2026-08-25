#!/usr/bin/env python3
"""Conan recipe for astc-encoder 5.7.0 — ARM ASTC texture compression codec.

Builds a static library (astcenc-neon-static on aarch64) and CLI tool (astcenc-neon).
GoogleTest is downloaded in source() to enable upstream unit tests (ctest).
No external dependencies; entirely self-contained C++14 codebase.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class AstcEncoderConan(ConanFile):
    name = "astc-encoder"
    version = "5.7.0"
    description = "ARM ASTC texture compression encoder and decoder library and CLI"
    license = "Apache-2.0"
    homepage = "https://github.com/ARM-software/astc-encoder"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def configure(self):
        # OHOS profile defines os.version but this recipe doesn't use it
        self.settings.rm_safe("os.version")

    def validate(self):
        # R32: settings.os must be Linux or OHOS
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"astc-encoder 5.7.0 only supports Linux and OHOS, "
                f"got os={self.settings.os}"
            )

    def source(self):
        # Download main source
        get(self, **self.conan_data["sources"], strip_root=True)

        # Download GoogleTest submodule (Source/GoogleTest)
        # GitHub tarball does not include submodules; we fetch v1.14.0 manually.
        gtest_dir = os.path.join(self.source_folder, "Source", "GoogleTest")
        os.makedirs(gtest_dir, exist_ok=True)
        get(self, **self.conan_data["googletest"],
            destination=gtest_dir, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS/aarch64 -> NEON SIMD
        if self.settings.arch in ("armv8", "armv8.3", "aarch64"):
            tc.variables["ASTCENC_ISA_NEON"] = True
            tc.variables["ASTCENC_ISA_SSE2"] = False
            tc.variables["ASTCENC_ISA_SSE41"] = False
            tc.variables["ASTCENC_ISA_AVX2"] = False
            tc.variables["ASTCENC_ISA_NATIVE"] = False
        # Build the CLI tool
        tc.variables["ASTCENC_CLI"] = True
        # Static library by default (avoid system .so pollution)
        tc.variables["ASTCENC_SHAREDLIB"] = self.options.shared
        # Enable unit tests (GoogleTest downloaded in source())
        tc.variables["ASTCENC_UNITTEST"] = True
        # Avoid clang 15 warnings-as-errors differences
        tc.variables["ASTCENC_WERROR"] = False
        # Floating point invariance
        tc.variables["ASTCENC_INVARIANCE"] = True
        tc.generate()

    def _build_environment(self):
        """Set LD_LIBRARY_PATH so lld can find libxml2.so.16 from OHOS SDK."""
        env = Environment()
        sdk_llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        if os.path.isdir(sdk_llvm_lib):
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        return env

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._build_environment().vars(self).apply():
            cmake.configure()
            cmake.build()
            # Run upstream unit tests (ctest)
            self.output.info("Running upstream ctest...")
            self.run("ctest --output-on-failure", env="conanrun")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream CMake only installs the CLI binary; manually add lib + headers
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Static library — cmake build output is in build/Source/
        lib_src = os.path.join(self.build_folder, "Source")
        copy(self, "libastcenc-neon-static.a",
             src=lib_src,
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        # CLI binary
        copy(self, "astcenc-neon",
             src=lib_src,
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)
        # Public header
        copy(self, "astcenc.h",
             src=os.path.join(self.source_folder, "Source"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["astcenc-neon-static"]
        self.cpp_info.set_property("cmake_file_name", "astc-encoder")
        self.cpp_info.set_property("cmake_target_name", "astc-encoder::astc-encoder")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
