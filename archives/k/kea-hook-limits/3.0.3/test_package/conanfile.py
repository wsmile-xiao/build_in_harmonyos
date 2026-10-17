#!/usr/bin/env python3
"""Conan test_package — kea-hook-limits 3.0.3 (consumer view).

Three checks run against the packaged plug-in:

* ``test_limits_hook``   — loads it with dlopen() the way the Kea server does
  and verifies the hook contract (version/load/unload, hook ABI 30003);
* ``test_ohos_platform`` — HarmonyOS-specific: the artefact carries the OHOS
  aarch64 / musl / libc++ platform ABI signature;
* ``test_ohos_runtime``  — HarmonyOS-specific: the packaged Kea runtime closure
  (20 libraries) is resolvable by the OHOS loader at run time.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class KeaHookLimitsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: hook load test skipped")
            return
        hook = os.path.join(self.dependencies[self.tested_reference_str].package_folder,
                            "lib", "kea", "hooks", "libdhcp_limits.so")
        bindir = self.cpp.build.bindirs[0]
        self.run('"{}/test_limits_hook" "{}"'.format(bindir, hook), env="conanrun")
        self.run('"{}/test_ohos_platform" "{}"'.format(bindir, hook), env="conanrun")
        self.run('"{}/test_ohos_runtime" "{}"'.format(bindir, hook), env="conanrun")
