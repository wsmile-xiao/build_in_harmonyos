#!/usr/bin/env python3
"""Conan test_package — libzen consumer-side functional test.

Builds test.cpp against the installed libzen package and runs it on the
OHOS device: the binary exercises Ztring (Unicode/UTF-8/number/
operators), ZtringListList, File, FileName and the Thread::ForceTerminate()
path patched for OHOS (weak-symbol probe of pthread_cancel), printing one
[ok]/[fail] line per check (23 assertions). Upstream ZenLib ships no test
framework (the
only demo, Source/Example/ZenLib_Test.cpp, is not built by any upstream
build system and ends with an interactive system("PAUSE")); see
test_package/MANIFEST.yml for the upstream-test rationale.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibzenTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS: run via the build shell (CONFIG_SHELL) like libmediainfo,
        # with TMPDIR pointing at a writable sandbox dir (the test writes
        # its probe file under argv[1]). The binary links the C++ runtime
        # dynamically: the OHOS SDK aarch64 libc++_shared.so must be on
        # LD_LIBRARY_PATH (the conanrun env of a static package does not
        # carry it).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        tmp = os.environ.get("TMPDIR") or "/data/storage/el2/base/cache"
        libcxx = ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native"
                  "/llvm/lib/aarch64-linux-ohos/c++")
        self.run(f"{bash} -c 'TMPDIR={tmp} LD_LIBRARY_PATH={libcxx} "
                 f"./libzen_test {tmp}'", env="conanrun")
