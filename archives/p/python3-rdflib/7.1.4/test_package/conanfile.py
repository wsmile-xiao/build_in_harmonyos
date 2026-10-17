#!/usr/bin/env python3
"""Consumer test for the rdflib Python import used by libzeitgeist."""

import os
import sys

from conan import ConanFile


class RdflibTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # test_rdflib.py holds the assertions so the test source is visible
        # to the consumer-test gate; the interpreter running Conan is the
        # one the recipe staged the package for, so it resolves the
        # PYTHONPATH exported by package_info wherever Python lives.
        test_script = os.path.join(self.source_folder, "test_rdflib.py")
        self.run(
            f'env -u LD_LIBRARY_PATH {sys.executable} "{test_script}"',
            env="conanrun",
        )
