#!/usr/bin/env python3
"""Conan test_package for qbe 1.2.

Consumer-side end-to-end check of the packaged compiler backend:
SSA -> arm64 assembly (qbe) -> executable (C compiler) -> native run ->
output comparison.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class QbeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _c_compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get("c") or os.environ.get("CC") or "cc"

    def test(self):
        if not can_run(self):
            return

        qbe_bin = os.path.join(self.dependencies["qbe"].package_folder, "bin", "qbe")
        script = os.path.join(self.source_folder, "test_qbe.sh")
        # The consumer test compiles the generated assembly, so it must run
        # with the build-tool environment: the profile [buildenv] provides the
        # OHOS SDK clang on PATH and its LLVM lib dir on LD_LIBRARY_PATH
        # (without the latter, lld cannot load libxml2 on CI workers).
        shell = (
            os.environ.get("CONFIG_SHELL")
            or os.environ.get("SHELL")
            or "/bin/sh"
        )
        self.run(
            f'QBE_BIN="{qbe_bin}" QBE_TEST_CC="{self._c_compiler()}" "{shell}" "{script}"',
            env="conanbuild",
        )
