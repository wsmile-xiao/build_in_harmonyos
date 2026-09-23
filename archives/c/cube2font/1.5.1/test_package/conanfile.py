import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class Cube2fontTestConan(ConanFile):
    """test_package for cube2font — drives real font conversions via test.sh."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_script = os.path.join(self.recipe_folder, "test.sh")
        # Conversion artifacts go to build_folder (no build residue in the
        # package source dir).
        self.run(f'"{bash}" "{test_script}" "{self.build_folder}"', env="conanrun")
