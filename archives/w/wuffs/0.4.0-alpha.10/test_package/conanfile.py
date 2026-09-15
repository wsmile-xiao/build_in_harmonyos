#!/usr/bin/env python3
"""Conan test_package for wuffs — real consumer build + run.

Builds one consumer program out of three translation units against the packaged
single file C library and runs it:

  test_wuffs.c                 C99, defines WUFFS_IMPLEMENTATION (the one TU
                               that carries the implementation)
  test_wuffs_header_only_tu.c  C99, header mode: opaque types + sizeof__()
                               allocation, linked against the TU above
  test_wuffs_cpp.cpp           C++17, header mode: wuffs_png__decoder::alloc()
                               and the C++ convenience methods

The program asserts the packaged file is the versioned 0.4.0-alpha.10 release,
decodes an embedded 4x4 PNG to 24bpp RGB, and compares CRC-32/adler32 of the
decoded pixels against values computed independently from the known pixel
pattern. See test_wuffs.c for the full check list.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class WuffsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def configure(self):
        # wuffs is header-only with a cleared package_id, so the consumer does
        # not need an os.version-specific test build (repo mdurl/rang pattern).
        self.settings.rm_safe("os.version")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # OHOS clang 15 ships libc++ only.
            tc.extra_cxxflags.append("-stdlib=libc++")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindir = self.cpp.build.bindirs[0]
        # Consumer program (C99 implementation TU + C header-mode TU + C++17 TU).
        self.run(os.path.join(bindir, "test_wuffs"), env="conanrun")
        # HarmonyOS platform program, built twice from one source: the default
        # build (aarch64 NEON fast paths selected) and the
        # WUFFS_CONFIG__AVOID_CPU_ARCH build (portable C only). Each asserts
        # which path it selected and then satisfies the same known-answer
        # assertions, including decoding from 16 unaligned input offsets.
        self.run(os.path.join(bindir, "ohos_platform_test"), env="conanrun")
        self.run(os.path.join(bindir, "ohos_platform_test_portable"),
                 env="conanrun")
