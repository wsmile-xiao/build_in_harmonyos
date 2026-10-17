#!/usr/bin/env python3
"""Consumer test for the Alejandra executable package."""
import os
import shlex

from conan import ConanFile


class AlejandraTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = shlex.quote(os.environ.get("CONFIG_SHELL", "bash"))
        script = shlex.quote(os.path.join(self.source_folder, "test.sh"))
        self.run(f"{shell} {script}", env="conanrun")
