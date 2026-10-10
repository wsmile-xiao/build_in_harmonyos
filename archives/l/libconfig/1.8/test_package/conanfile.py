#!/usr/bin/env python3
"""Upstream and consumer verification for packaged libconfig 1.8."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class LibconfigTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _upstream_source(self):
        return os.path.join(self.source_folder, "upstream")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()

        pkg_folder = self.dependencies["libconfig"].package_folder
        script = os.path.join(self.source_folder, "test.sh")
        work_dir = os.path.join(self.build_folder, "consumer_test_work")
        self.run(f'bash "{script}" "{pkg_folder}" "{work_dir}"', env="conanrun")

        compiler = (
            os.environ.get("CC")
            or shutil.which("clang")
            or "/data/service/hnp/bin/clang"
        )
        upstream_source = self._upstream_source()
        tests_dir = os.path.join(upstream_source, "tests")
        tests_bin = os.path.join(self.build_folder, "libconfig_upstream_tests")
        tests_log = os.path.join(
            self.build_folder, "libconfig_upstream_tests.log"
        )

        # Build the upstream test program against the installed static library.
        self.run(
            f'"{compiler}" -O2 -I"{pkg_folder}/include" '
            f'-I"{upstream_source}/tinytest" '
            f'"{tests_dir}/tests.c" '
            f'"{upstream_source}/tinytest/tinytest.c" '
            f'-L"{pkg_folder}/lib" -lconfig -lm -o "{tests_bin}"',
            env="conanrun",
        )
        self.run(
            f'"{tests_bin}" > "{tests_log}" 2>&1',
            cwd=tests_dir,
            env="conanrun",
        )

        with open(tests_log, encoding="utf-8", errors="replace") as stream:
            result = stream.read()
        expected = "16 tests; 16 passed, 0 failed"
        if expected not in result:
            raise ConanException(
                f"upstream libconfig tests failed: expected {expected!r}, "
                f"got: {result.strip()!r}"
            )
        self.output.info(result.strip())
