#!/usr/bin/env python3
"""Conan test_package for minised 1.16 — real sed functional verification.

minised is a CLI sed interpreter, so the test runs the packaged binary
directly (no library linking). It exercises three core sed features the
upstream test-suite also covers: substitution (s///), line deletion (d), and
a simple regular expression match with grouping. The required example from
the task — turning `hello world` into `hello OpenHarmony` via
`s/world/OpenHarmony/` — is run first and is the primary assertion.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class MinisedTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            minised = os.path.join(
                self.dependencies["minised"].cpp_info.bindirs[0], "minised"
            )
            test_script = os.path.join(self.source_folder, "test_minised.sh")
            self.run(f'sh "{test_script}" "{minised}"', env="conanrun")
