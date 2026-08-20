#!/usr/bin/env python3
"""Conan test_package for cweb 4.12.2 — functional smoke test.

Verifies that ctangle and cweave work correctly after installation by
processing a minimal CWEB source file (hello.w) and checking the outputs:
  - ctangle hello.w → hello.c (C source extraction)
  - cweave hello.w  → hello.tex (TeX documentation extraction)
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class CwebTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f'{bash} test.sh', env="conanrun")
