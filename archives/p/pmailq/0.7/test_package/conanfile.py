#!/usr/bin/env python3
"""Conan test_package for pmailq 0.7.

Exercises the packaged `pmailq` script as a consumer would: artifact checks,
syntax validation, CLI smoke (--help/--version), and a full functional flow
(list/parse/del + email/msg/size filters) against PATH shims that stub
postqueue/postsuper with a realistic two-entry fixture. Every case asserts on
real output content; an empty or broken package fails.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class PmailqTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["pmailq"].package_folder
        script = os.path.join(self.source_folder, "test_pmailq.py")
        pmailq = os.path.join(pkg, "bin", "pmailq")
        self.run('python3 "{}" "{}"'.format(script, pmailq), env="conanrun")
