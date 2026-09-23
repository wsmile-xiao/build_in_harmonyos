#!/usr/bin/env python3
"""Consumer-side functional tests for PLOD 1.9."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class PlodTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        plod_dependency = self.dependencies["plod"]
        plod = os.path.join(plod_dependency.package_folder, "bin", "plod")
        test_script = os.path.join(self.source_folder, "test_plod.sh")

        for label, path in (("plod", plod), ("test script", test_script)):
            if not os.path.isfile(path):
                raise ConanException(f"{label} not found: {path}")

        if not can_run(self):
            raise ConanException(
                "Run test_package directly on the HarmonyOS computer. "
                "Host-only packaging does not validate target runtime tests."
            )
        perl_dependency = self.dependencies["perl"]
        perl = os.path.join(perl_dependency.package_folder, "bin", "perl")
        if not os.path.isfile(perl):
            raise ConanException(f"perl not found: {perl}")
        self.run(f'sh "{test_script}" "{perl}" "{plod}"', env="conanrun")
