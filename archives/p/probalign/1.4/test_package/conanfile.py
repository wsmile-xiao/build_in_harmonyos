#!/usr/bin/env python3
"""Conan test_package for probalign 1.4.

This is the L1 consumer test: `conan create` runs it against the freshly
installed package, so it proves the signed binary in the package folder is
the tool that actually performs the alignment.
"""
import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class ProbalignTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # No can_run() guard here on purpose.  CI's L1e destructive check
        # re-runs `conan test` with the host profile only, so the cached build
        # profile (os=Linux) makes conan report a cross build and can_run()
        # turns False.  Returning quietly would print a green test that never
        # consumed the package, which is exactly the fake R34/L1e is looking
        # for.  probalign is an application package whose only consumable
        # artifact is bin/probalign: if it cannot be executed, that is a
        # failure, not a skip.
        package = self.dependencies["probalign"].package_folder
        bin_dir = os.path.join(package, "bin")
        script = os.path.join(self.recipe_folder, "test_probalign.py")
        # The generators folder always exists and is writable, while /tmp is
        # read-only on the target.
        work_dir = os.path.join(self.generators_folder, "probalign-consumer")
        self.run(f'"{sys.executable}" "{script}" "{bin_dir}" "{work_dir}"',
                 env="conanrun")
