#!/usr/bin/env python3
"""Conan test_package — kea-hook-pgsql 3.0.3 (consumer view).

Two checks run against the packaged plug-in:

* ``test_pgsql_hook``      — loads it with dlopen() the way the Kea server does
  and verifies the hook contract (version/load/unload plus the
  dhcp4_srv_configured and dhcp6_srv_configured server callouts, hook ABI
  30003).  No PostgreSQL server is required: load() only registers the
  PostgreSQL back-end factories;
* ``test_ohos_platform``   — HarmonyOS-specific check that the artefact carries
  the OHOS aarch64 / musl / libc++ platform ABI signature and links libpq.so.5,
  can be mapped by the OHOS loader and exposes the pgsql hook callouts through
  it.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class KeaHookPgsqlTestConan(ConanFile):
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
                            "lib", "kea", "hooks", "libdhcp_pgsql.so")
        bindir = self.cpp.build.bindirs[0]
        self.run('"{}/test_pgsql_hook" "{}"'.format(bindir, hook), env="conanrun")
        self.run('"{}/test_ohos_platform" "{}"'.format(bindir, hook), env="conanrun")
