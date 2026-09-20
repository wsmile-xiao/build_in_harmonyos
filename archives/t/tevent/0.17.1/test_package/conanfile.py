#!/usr/bin/env python3
"""Compile and run a tevent event-loop consumer."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class TeventTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dependency = self.dependencies["tevent"]
        talloc = self.dependencies["talloc"]
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        source = os.path.join(self.source_folder, "test_tevent.c")
        executable = os.path.join(self.build_folder, "test_tevent")
        self.run(
            '"{}" -std=gnu11 -D_GNU_SOURCE "{}" '
            '-I"{}" -I"{}" -L"{}" -L"{}" -ltevent -ltalloc -lpthread -o "{}"'.format(
                cc,
                source,
                os.path.join(dependency.package_folder, "include"),
                os.path.join(talloc.package_folder, "include"),
                os.path.join(dependency.package_folder, "lib"),
                os.path.join(talloc.package_folder, "lib"),
                executable,
            ),
            env="conanbuild",
        )
        if can_run(self):
            self.run('"{}"'.format(executable), env="conanrun")
