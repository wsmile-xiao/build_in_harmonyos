#!/usr/bin/env python3
"""Conan test_package for libgringotts 1.2.1.

Consumer-side test: links against libgringotts and exercises the real
encrypt/decrypt round-trip API, satisfying PF3 / R34 (non-empty API test).
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibgringottsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # OHOS worker buffers self.run stdout -> bind build output to a log file
        # so the real clang diagnostic is never silently lost (memory: silent-fail).
        log = os.path.expanduser("~/tmp/testpkg_build.log")
        build_dir = self.build_folder
        with open(log, "w") as fh:
            rc = subprocess.run(
                ["cmake", "--build", ".", "--", "-j1", "VERBOSE=1"],
                cwd=build_dir, stdout=fh, stderr=subprocess.STDOUT, env=os.environ,
            ).returncode
        if rc != 0:
            tail = []
            try:
                with open(log) as fh:
                    tail = fh.read().splitlines()[-50:]
            except OSError:
                pass
            raise ConanException(
                "test_package build failed (rc=%d); tail of %s:\n%s"
                % (rc, log, "\n".join(tail))
            )

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: test binary was built but not executed")
            return
        exe = os.path.join(self.cpp.build.bindirs[0], "test_libgringotts")
        self.run(f'"{exe}"', env="conanrun")
