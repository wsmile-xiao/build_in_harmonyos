#!/usr/bin/env python3
"""test_package for lwtools 4.25 — exercises the packaged binaries (R34).

test_lwtools.sh really runs every installed program: it assembles 6809 source
to golden machine-code bytes, links and dumps an object, round-trips an lwar
archive, checks the documented failure behaviour of the assembler, and drives
the lwcc preprocessor (the regression test for the packaged sysmacrolist
patch). It fails when a binary is missing or broken, which is what CI L1e
relies on by sabotaging bin/.
"""
import os

from conan import ConanFile


class LwtoolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["lwtools"].package_folder
        script = os.path.join(self.source_folder, "test_lwtools.sh")
        # Plain `sh`, not an ambient $CONFIG_SHELL: the script is POSIX-only and
        # must run identically under the device's ash and the worker's bash.
        command = 'sh "{0}" "{1}" "{2}"'.format(
            script, os.path.join(package_folder, "bin"), package_folder
        )
        self.run(command, env="conanrun")
