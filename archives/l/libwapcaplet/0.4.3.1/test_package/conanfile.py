#!/usr/bin/env python3
"""Conan test_package for libwapcaplet 0.4.3.1 — L1 smoke test.

CI runs this automatically via `conan create` (which invokes test_package).
test.c exercises the real lwc_string_* API of the package (R34).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibwapcapletTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # E120: OHOS SDK lld links libxml2.so.16; inject its lib dir into
        # LD_LIBRARY_PATH so CMake's configure/link step finds it on CI workers.
        llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        if os.path.isdir(llvm_lib):
            os.environ["LD_LIBRARY_PATH"] = llvm_lib + ":" + os.environ.get("LD_LIBRARY_PATH", "")

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Alternatively, run the binary directly:
        # self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_libwapcaplet')}", env="conanrun")
