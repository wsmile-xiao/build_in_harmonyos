#!/usr/bin/env python3
"""Conan test_package — kea-hook-lease-query 3.0.3 (consumer view).

Two checks run against the packaged plug-in:

* ``test_lease_query_hook`` — loads it with dlopen() the way the Kea server does
  and verifies the hook contract (version/load/unload, hook ABI 30003), i.e.
  what kea-dhcp4/kea-dhcp6 do when they load the plug-in at runtime;
* ``test_ohos_platform``    — HarmonyOS-specific: the packaged artefact carries
  the OHOS aarch64 / musl / libc++ platform ABI signature (EM_AARCH64,
  DT_NEEDED ``libc.so`` and not glibc's ``libc.so.6``, ``libc++_shared.so``)
  and the OHOS loader resolves it with dlopen(RTLD_NOW).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class KeaHookLeaseQueryTestConan(ConanFile):
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
                            "lib", "kea", "hooks", "libdhcp_lease_query.so")
        bindir = self.cpp.build.bindirs[0]
        self.run('"{}/test_lease_query_hook" "{}"'.format(bindir, hook), env="conanrun")
        self.run('"{}/test_ohos_platform" "{}"'.format(bindir, hook), env="conanrun")
