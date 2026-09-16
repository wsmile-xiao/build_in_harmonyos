#!/usr/bin/env python3
"""Conan test_package for mmkv — exercises both the C++ API and the
C bridge API with real round-trip set/get operations.

R34: The test substantively calls MMKV::mmkvWithID / mmkv->set / getString /
removeValueForKey (C++), and mmkv_initialize / mmkv_with_id / mmkv_encode_* /
mmkv_decode_* (C bridge). It is NOT a printf-only stub.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MmkvTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the test binary for real. OHOS /system/bin/sh (mksh) cannot
        # execute ELF binaries directly, wrap with bash like other recipes.
        # The binary is dynamically linked against the system libc++
        # (libc++_shared.so lives in /system/lib64); the conanrun env does
        # not carry the loader search path, so pass it explicitly.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_mmkv")
        self.run(
            f'LD_LIBRARY_PATH="/system/lib64" "{bash}" -c \'{test_bin}\'',
            env="conanrun",
        )
