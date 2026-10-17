import os

from conan import ConanFile


class LighterTestConan(ConanFile):
    """test_package for the lighter executable - runs test.sh against the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, so bash wraps it.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(bash + " test.sh", env="conanrun")
