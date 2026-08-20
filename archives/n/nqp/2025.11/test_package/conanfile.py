#!/usr/bin/env python3
"""Consumer test for NQP 2025.11."""

import os

from conan import ConanFile


class NqpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_nqp.py", "test.nqp"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        runner = os.path.join(self.source_folder, "test_nqp.py")
        script = os.path.join(self.source_folder, "test.nqp")
        nqp = os.path.join(self.dependencies["nqp"].package_folder, "bin", "nqp")
        if not os.path.isfile(nqp) or not os.access(nqp, os.X_OK):
            raise RuntimeError(f"packaged NQP executable is unavailable: {nqp}")
        self.run(f'python3 "{runner}" "{nqp}" "{script}"', env="conanrun")
