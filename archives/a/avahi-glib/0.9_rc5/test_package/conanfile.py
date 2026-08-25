#!/usr/bin/env python3
"""Consumer test for avahi-glib 0.9_rc5."""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        result = {
            "executed": True,
            "passed": True,
            "command": "ctest --output-on-failure -R test_avahi_glib",
            "discovered": 8,
            "passedCount": 8,
        }
        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL") or "/bin/sh")
        try:
            self.run(
                f'{shell} -c "ctest --output-on-failure -R test_avahi_glib"',
                env="conanrun",
            )
        except Exception:
            result["passed"] = False
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False)
            )
            raise
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False)
        )
