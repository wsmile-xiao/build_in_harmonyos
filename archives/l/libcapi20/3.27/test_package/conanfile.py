#!/usr/bin/env python3
"""Conan test_package for libcapi20 — consumer-side verification.

Builds and runs two executables against the packaged library: ``test.c``
(CAPI 2.0 codec and library accessors) and ``test_ohos.c`` (HarmonyOS
specific driver-plugin relocation through the platform loader).  Upstream
ships no test suite, so both are added by this adaptation.
"""
from __future__ import annotations

import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class Libcapi20TestConan(ConanFile):
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
        # The test executables are launched through subprocess (and not with
        # self.run()) because the platform shell wrapper aborts with SIGSEGV
        # when it is used from inside the conan test() sandbox.
        dep = self.dependencies[self.tested_reference_str]
        libdir = os.path.join(dep.package_folder, "lib")
        module_dir = os.path.join(libdir, "capi")

        env = os.environ.copy()
        env["CAPI_TEST_LIBDIR"] = libdir
        env["CAPI20_MODULE_DIR"] = module_dir
        old_ld_path = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = (
            libdir + os.pathsep + old_ld_path if old_ld_path else libdir
        )

        bindir = self.cpp.build.bindirs[0]
        failed = []
        for name in ("test_libcapi20", "test_libcapi20_ohos"):
            executable = os.path.join(bindir, name)
            self.output.info(f"running adaptation tests: {executable}")
            result = subprocess.run(
                [executable],
                cwd=self.build_folder,
                env=env,
                capture_output=True,
                text=True,
            )
            self.output.info(result.stdout)
            if result.stderr:
                self.output.info(result.stderr)
            if result.returncode != 0:
                failed.append(f"{name} (exit {result.returncode})")

        if failed:
            raise ConanException(
                "libcapi20 test package failed: " + ", ".join(failed)
            )
