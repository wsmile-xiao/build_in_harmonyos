#!/usr/bin/env python3
"""Conan test_package for cinatra/0.8.9 — consumer smoke test.

Builds a program against the installed cinatra headers, runs it on the
OHOS target (this host is an OHOS PC): starts a coro_http_server,
performs coro_http_client GET/POST loopback round trips and checks
status code + body.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CinatraTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # cinatra requires C++20 coroutines; CI profile defaults to cppstd=17
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # L0d/R34: run the consumer test binary on the target (OHOS PC host).
        # musl ld.so needs /system/lib64 for libc++_shared.so (scnlib pattern).
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_package")
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        self.run(
            f'{bash} -c "LD_LIBRARY_PATH=/system/lib64 {test_bin}"',
            env="conanrun",
        )
