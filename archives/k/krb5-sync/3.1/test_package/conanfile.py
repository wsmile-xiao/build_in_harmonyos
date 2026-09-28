#!/usr/bin/env python3
"""L1 consumer test for krb5-sync (conan test_package)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Krb5SyncTestConan(ConanFile):
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
        package = self.dependencies["krb5-sync"].package_folder
        # bin/, not sbin/: the Conan autotools toolchain installs sbin into
        # /bin (see package_info comment), so sbin/krb5-sync never exists
        # and access(KRBSYNC_BIN, X_OK) in test.c would fail the consumer test.
        binary = os.path.join(package, "bin", "krb5-sync")
        exe = os.path.join(self.cpp.build.bindirs[0], "test_krb5-sync")
        # Substantive dependency on the tested package (R34): the consumer
        # driver runs the installed krb5-sync command and checks it is execable.
        self.run('KRBSYNC_BIN="{}" "{}"'.format(binary, exe), env="conanrun")
