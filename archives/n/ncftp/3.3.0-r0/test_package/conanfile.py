#!/usr/bin/env python3
"""Conan test_package — ncftp 3.3.0-r0.

Compiles test.c (which uses system() to verify ncftp --version works)
and runs it. Also smoke-tests the installed ncftp binary directly.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class NcftpTestConan(ConanFile):
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
        # R32: only meaningful on Linux/OHOS.
        if self.settings.os not in ("Linux", "OHOS"):
            return

        # Add ncftp bin/ to PATH so test.c's system() calls find it
        pkg = self.dependencies["ncftp"].package_folder
        bindir = os.path.join(pkg, "bin")
        os.environ["PATH"] = bindir + ":" + os.environ.get("PATH", "")

        # 1) Run the compiled test (uses system() to verify ncftp --version)
        cmake = CMake(self)
        cmake.test()

        # 2) Smoke-test the installed ncftp binary directly
        ncftp_bin = os.path.join(bindir, "ncftp")
        assert os.path.isfile(ncftp_bin), f"ncftp binary missing: {ncftp_bin}"
        self.run(f'"{ncftp_bin}" --version 2>&1 | grep -iq "NcFTP"',
                 env="conanrun")
