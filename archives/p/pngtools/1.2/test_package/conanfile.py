#!/usr/bin/env python3
"""Consumer test for the installed pngtools command-line tools."""

import os

from conan import ConanFile


class PngtoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    exports_sources = ("test_smoke.py",)
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["pngtools"].package_folder
        bindir = os.path.join(package_folder, "bin")
        test_script = os.path.join(self.source_folder, "test_smoke.py")
        # conanrun supplies LD_LIBRARY_PATH for the libpng dependency, the
        # same way the repo's other application test packages do.
        self.run(
            'python3 "%s" "%s"' % (test_script, bindir),
            env="conanrun",
        )
