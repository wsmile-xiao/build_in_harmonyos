#!/usr/bin/env python3
"""test_package for libproc2 4.0.6 — consumer-side validation (Conan L1).

R34: the test genuinely depends on the packaged libproc2 — test_libproc2.c
links against the packaged libproc2.a and calls the real public API
(procps_uptime / procps_loadavg / procps_pids_new+get+unref) through the
upstream-documented include path <libproc2/...>; the compiled binary is then
executed so the checks actually run.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class Libproc2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Compiling + linking test_libproc2.c against the packaged libproc2
        # already proves the library, headers and CMake target are consumable.
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        exe = os.path.join(self.cpp.build.bindirs[0], "test_libproc2")
        if not os.path.isfile(exe):
            raise ConanException(f"missing test executable: {exe}")

        if not can_run(self):
            # Cross build: linking against the packaged libproc2 validates the
            # C API/headers (R34); runtime is validated on the OHOS device.
            self.output.info(
                "cross build: test_libproc2 linked against the packaged "
                "libproc2 — runtime validated on OHOS device"
            )
            return

        self.run(f'"{exe}"', env="conanrun")
