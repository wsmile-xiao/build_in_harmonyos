#!/usr/bin/env python3
"""Consumer test for slugify: both drivers run under bash/5.3 (the OHOS bash)
inside the conanrun environment and rename real files in a scratch directory
below the test build folder."""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class SlugifyTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("bash/5.3")

    def layout(self):
        basic_layout(self)

    def test(self):
        # No can_run() early return: a machine that cannot run bash/5.3 must
        # fail here rather than report a pass without executing anything.
        bash = os.path.join(self.dependencies["bash"].package_folder, "bin", "bash")
        slugify = os.path.join(self.dependencies["slugify"].package_folder,
                               "bin", "slugify")
        for driver in ("test_slugify.sh", "test_slugify_ohos.sh"):
            script = os.path.join(self.source_folder, driver)
            self.run(f'"{bash}" "{script}" "{slugify}"', env="conanrun",
                     cwd=self.build_folder)
