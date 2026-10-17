#!/usr/bin/env python3
"""Compile and run a tslib consumer against the packaged library."""

import os
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class TslibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dependency = self.dependencies["tslib"]
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        source = os.path.join(self.source_folder, "test_tslib_consumer.c")
        # Build and run from a TMPDIR-backed scratch directory so no binary
        # artifact is left inside the test_package source folder.
        workdir = tempfile.mkdtemp(prefix="tslib-test-package-")
        executable = os.path.join(workdir, "test_tslib_consumer")
        self.run(
            '"{}" -std=c11 -I"{}" "{}" -L"{}" -lts -o "{}"'.format(
                cc,
                os.path.join(dependency.package_folder, "include"),
                source,
                os.path.join(dependency.package_folder, "lib"),
                executable,
            ),
            env="conanbuild",
        )
        if can_run(self):
            self.run('"{}"'.format(executable), env="conanrun")
        else:
            self.output.info(
                "test_tslib_consumer skipped: cannot run target binaries "
                "on the build host (cross build)"
            )
