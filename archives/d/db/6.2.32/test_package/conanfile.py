#!/usr/bin/env python3
"""Conan test_package for db (Berkeley DB classic) 6.2.32.

L1 consumer test: builds test.c against the packaged headers/libs and
runs it. The test program genuinely exercises the C API
(db_create/open/put/get/cursor/close/reopen) — see test.c.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class DbTestConan(ConanFile):
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
        # Run the consumer test binary built from test.c. It links
        # against the packaged libdb-6.2 (static by default). The conanrun
        # env on OHOS/HMDFS does not propagate libdirs into
        # LD_LIBRARY_PATH, so inject it explicitly (same pattern as the
        # berkeley-db5 archive). libdb_cxx-6.2.so DT_NEEDs libc++_shared.so
        # which is not in the default loader search path on OHOS, so the
        # toolchain's c++ lib dir is added as well.
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_db")
        dep = self.dependencies["db"]
        lib_dir = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
        libcxx_dir = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos/c++"
        extra = f":{libcxx_dir}" if os.path.isdir(libcxx_dir) else ""
        self.run(
            f'export LD_LIBRARY_PATH="{lib_dir}{extra}:$LD_LIBRARY_PATH"; "{bin_path}"',
            env="conanrun",
        )
