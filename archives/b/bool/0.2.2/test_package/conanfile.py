#!/usr/bin/env python3

import os

from conan import ConanFile
from conan.tools.build import can_run


class BoolTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        dependency = self.dependencies[self.tested_reference_str]
        bool_binary = os.path.join(dependency.package_folder, "bin", "bool")
        test_script = os.path.join(self.source_folder, "test_bool.sh")
        self.run(f'sh "{test_script}" "{bool_binary}"', env="conanrun")
