#!/usr/bin/env python3
"""Consumer test for the ext2fuse application package."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class Ext2fuseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning("Cannot run ext2fuse in this environment")
            return

        package = self.dependencies["ext2fuse"]
        bin_dir = os.path.join(package.package_folder, "bin")
        script = os.path.join(self.source_folder, "test_ext2fuse.sh")
        self.run(
            f'sh "{script}" "{bin_dir}" "{self.build_folder}"',
            env="conanrun",
        )
