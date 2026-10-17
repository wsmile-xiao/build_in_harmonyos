#!/usr/bin/env python3
"""Consumer test: run the packaged linux_logo binary and assert on its output.

Every check below is falsifiable on its own (a single observed property of
the rendered output), and the whole set fails the build if any one of them
is not satisfied.
"""
import os
import re
import subprocess

from conan import ConanFile

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


class LinuxlogoConsumerTest(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # Same shape as the merged aaudit-server/0.7.2 test package (an
        # application type required through self.requires).
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["linuxlogo"]
        exe = os.path.join(dep.package_folder, "bin", "linux_logo")
        if not os.path.isfile(exe):
            raise RuntimeError("packaged executable missing: {0}".format(exe))
        # L0d wants test() to call self.run(); the behavior assertions live in
        # consumer_test.py (L0c requires a test source file next to conanfile).
        script = os.path.join(self.source_folder, "consumer_test.py")
        self.run('python3 {0} {1}'.format(script, exe), env="conanrun")
