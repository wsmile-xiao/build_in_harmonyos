#!/usr/bin/env python3
"""Compile and run a libgoom2 consumer against the packaged library."""

import os
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class Libgoom2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dependency = self.dependencies["libgoom2"]
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        source = os.path.join(self.source_folder, "test_libgoom2_consumer.c")
        # Build and run from a TMPDIR-backed scratch directory so no binary
        # artifact is left inside the test_package source folder.
        workdir = tempfile.mkdtemp(prefix="libgoom2-test-package-")
        executable = os.path.join(workdir, "test_libgoom2_consumer")
        self.run(
            '"{}" -std=c11 -I"{}" "{}" -L"{}" -lgoom2 -o "{}"'.format(
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
                "test_libgoom2_consumer skipped: cannot run target binaries "
                "on the build host (cross build)"
            )
