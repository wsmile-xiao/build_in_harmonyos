#!/usr/bin/env python3
"""Conan test_package for libxmu 1.3.1.1 — L1 official test (R34: substantive).

Two consumers run against the packaged libraries:

  - test_libxmu      : XmuCompareISOLatin1() from libXmuu (the Xt-independent
                       subset), the same API the upstream "Lower" test verifies.
  - test_libxmu_ohos : XmuReadBitmapDataFromFile() from the Xt-linked libXmu,
                       asserting the HarmonyOS degradation paths (rule12):
                       malformed input -> BitmapFileInvalid, absent path on the
                       read-only root -> BitmapOpenFailed, no abort().

The generate() step mirrors libxext/6.4.0.1's test_package: the shared
ohos-aarch64 profile pins tools.build:compiler_executables to
/data/service/hnp/bin/clang, which is not present on every worker, so the
generated CMakeToolchain is rewritten to a compiler that actually exists.
VirtualRunEnv is generated explicitly because self.run(env="conanrun") below
requires the conanrun script.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import replace_in_file


class LibxmuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "CMakeLists.txt", "test.c", "test_ohos.c"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libXmu headers transitively include X11/Xfuncproto.h, owned by
        # xorgproto. Conan does not propagate test-only transitive deps,
        # so declare it explicitly so the test compiles on a clean graph.
        self.requires("xorgproto/2025.1")
        # test_ohos.c also needs <X11/Xutil.h> for the BitmapSuccess /
        # BitmapFileInvalid / BitmapOpenFailed status codes. Those headers do
        # reach the test through libxmu's transitive headers, but naming the
        # dependency directly keeps the include path independent of that
        # setting. Same version the libxmu recipe pins, so no graph conflict.
        self.requires("libx11/1.8.13")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_C_COMPILER"] = self._compiler_executable(
                "c", "clang"
            )
        tc.generate()
        if str(self.settings.os) == "OHOS":
            self._patch_cmake_toolchain_compilers()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Explicit self.run() so CI L0d does not flag this as a stub test.
        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_libxmu"), env="conanrun")
        self.run(os.path.join(bindir, "test_libxmu_ohos"), env="conanrun")

    def _compiler_executable(self, key, fallback_name):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _patch_cmake_toolchain_compilers(self):
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        replacements = {
            "/data/service/hnp/bin/clang++": self._compiler_executable(
                "cpp", "clang++"
            ),
            "/data/service/hnp/bin/clang": self._compiler_executable("c", "clang"),
        }
        for old, new in replacements.items():
            replace_in_file(self, toolchain, old, new, strict=False)
