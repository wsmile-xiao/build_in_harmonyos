#!/usr/bin/env python3
"""test_package/conanfile.py — libblastrampoline 5.15.0 consumer test

Builds three controlled fake BLAS backends (MODULE libraries, dlopened by
libblastrampoline at runtime) and a consumer test that verifies:
  1. lbt_get_config(): DEEPBINDLESS build flags (musl/OHOS), symbol count
  2. Error path: lbt_forward() on a nonexistent library returns 0
  3. LP64 backend forwarding: suffix "" autodetected, dgemm_/daxpy_/sdot_
     trampolines compute deterministic values through the backend
  4. Backend switching: clear+forward swaps backends and results change
  5. lbt_get_forward() unknown-symbol sentinel ((void*)-1)
  6. deepbindless conflict semantics: LP64 + unsuffixed ILP64 refused,
     LP64 + suffixed (64_) ILP64 allowed

No real BLAS is involved: backends are deterministic fakes, so assertions
are exact. A separate OHOS platform test (test_ohos.sh) verifies ELF
properties: AArch64 machine, musl NEEDED entries, SONAME, .codesign
section, and real dlopen-based loading through lbt_forward().
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibblastrampolineTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        # ctest wraps test_consumer with LD_LIBRARY_PATH (OHOS clang embeds
        # no rpath), covering symbol forwarding, backend switching, interface
        # autodetection, error paths, deepbindless conflict semantics.
        cmake.test()

        # Explicit run for CI L0d stub check + OHOS platform invariants
        backends = os.path.join(self.build_folder, "backends")
        self.run(
            f'"{os.path.join(self.build_folder, "test_consumer")}"'
            f' "{os.path.join(backends, "fakeblas_lp64.so")}"'
            f' "{os.path.join(backends, "fakeblas_ilp64.so")}"'
            f' "{os.path.join(backends, "fakeblas_ilp64_nosuffix.so")}"',
            env="conanrun")

        # OHOS platform invariants (ELF + real dynamic loading), on-device.
        # Point the checker at the packaged library inside the conan cache.
        if self.settings.os == "OHOS":
            dep = self.dependencies["libblastrampoline"]
            lbt_dir = dep.cpp_info.aggregated_components().libdirs[0]
            self.run(f'bash "{os.path.join(self.source_folder, "test_ohos.sh")}" "{lbt_dir}"',
                     cwd=self.build_folder)
