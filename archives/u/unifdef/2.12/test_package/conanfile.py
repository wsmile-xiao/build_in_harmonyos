#!/usr/bin/env python3
"""test_package for unifdef — exercises the packaged binaries (R34).

test_unifdef.sh really runs the installed `unifdef` against freshly created C
samples and asserts on its output and documented exit statuses; it fails if the
binary is missing or broken (CI L1e sabotages bin/ to prove this dependency).
"""
import os

from conan import ConanFile


class UnifdefTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        self.run("{0} test_unifdef.sh".format(shell), env="conanrun")
