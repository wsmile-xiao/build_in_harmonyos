#!/usr/bin/env python3
"""Conan test_package — consumer test for plusaes 1.0.0 (header-only).

Compiles example.cpp against the *packaged* header only (find_package(plusaes)
→ plusaes::plusaes) and runs it on the device: 25 checks covering the ECB /
CBC / CTR / GCM known-answer vectors, round trips with PKCS padding
bookkeeping and the error paths.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class PlusaesTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # L0d: run the consumer binary itself (cmake.test() would be a stub),
        # under the conanrun environment so the packaged header is consumed.
        exe = os.path.join(self.build_folder, "bin", "test_package")
        if not os.path.isfile(exe):
            raise ConanException("consumer binary missing: %s" % exe)
        self.run('"%s"' % exe, env="conanrun")
        self.output.success(
            "plusaes 1.0.0 test_package: 25 consumer checks passed"
        )
