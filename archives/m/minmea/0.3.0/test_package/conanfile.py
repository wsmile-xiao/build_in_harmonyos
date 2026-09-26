#!/usr/bin/env python3
"""Conan test_package — consumer test for minmea 0.3.0 (Makefile).

Compiles a consumer translation unit against the packaged header/library and
runs it: checksum validation, sentence classification, RMC parsing and the
fixed-point/coordinate helpers.  CI runs it automatically via `conan create`.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class MinmeaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        configured = executables.get("c")
        if configured:
            candidate = str(configured).split()[0].strip("\"'")
            if os.path.isfile(candidate):
                return candidate
        resolved = shutil.which("clang") or shutil.which("cc")
        if not resolved:
            raise RuntimeError("cannot find a C compiler")
        return resolved

    def build(self):
        dependency = self.dependencies["minmea"]
        include_dir = os.path.join(dependency.package_folder, "include")
        lib_dir = os.path.join(dependency.package_folder, "lib")
        source = os.path.join(self.source_folder, "test.c")

        # Compile straight against the packaged artifacts instead of the build
        # tree, so a missing header or library fails here.
        command = (
            f"{shlex.quote(self._compiler())} -std=c99 -Wall -Wextra "
            f"-I{shlex.quote(include_dir)} "
            f"{shlex.quote(source)} -o test_minmea "
            f"-L{shlex.quote(lib_dir)} -lminmea"
        )
        self.run(command)

    def test(self):
        if can_run(self):
            self.run(os.path.join(self.build_folder, "test_minmea"), env="conanrun")
        else:
            self.output.info("cross-building: compile/link test completed")
