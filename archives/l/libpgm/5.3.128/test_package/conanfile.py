#!/usr/bin/env python3
"""Consumer test for the public libpgm (OpenPGM) API.

L1 test of the five-level test system: `conan create` runs it automatically.
It links the installed library, calls the public API and re-emits the upstream
unit-test evidence collected in the package's build(), so the marker survives a
cached binary (build() is skipped then).
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibpgmTestConan(ConanFile):
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
        """Run the consumer binary directly (CI L0d rejects a test() stub).

        `cmake.test()` does not count as a real consumer invocation for the CI
        quality gate, so the built binary is executed through self.run() with
        the Conan runtime environment; a non-zero exit fails the test.
        """
        if can_run(self):
            binary = os.path.join(self.cpp.build.bindirs[0], "test_libpgm")
            self.run(binary, env="conanrun")
        self._emit_upstream_evidence()

    def _emit_upstream_evidence(self):
        """Re-print HMBS_UPSTREAM_TEST_RESULT shipped by the package."""
        packaged = os.path.join(
            self.dependencies["libpgm"].package_folder,
            "res",
            "upstream-test-result.json",
        )
        if not os.path.isfile(packaged):
            self.output.warning(
                "no packaged upstream test evidence at %s" % packaged
            )
            return
        with open(packaged, encoding="utf-8") as handle:
            marker = json.load(handle)
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
