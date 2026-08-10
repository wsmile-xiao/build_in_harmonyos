#!/usr/bin/env python3
"""Compile and run a talloc hierarchy consumer."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class TallocTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dependency = self.dependencies["talloc"]
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        source = os.path.join(self.source_folder, "test_talloc.c")
        executable = os.path.join(self.build_folder, "test_talloc")
        self.run(
            '"{}" -std=c11 -I"{}" "{}" -L"{}" -ltalloc -o "{}"'.format(
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
