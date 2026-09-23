import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class CeccompTestConan(ConanFile):
    """test_package for ceccomp — runs test.sh which invokes the binary."""
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
        # Roundtrip artifacts go to build_folder (workflow 5.3: no build
        # residue in the package source dir).
        self.run(f'"{bash}" "{test_script}" "{self.build_folder}"',
                 env="conanrun")
