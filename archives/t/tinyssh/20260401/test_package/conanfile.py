import os

from conan import ConanFile
from conan.tools.build import can_run


class TinysshTestConan(ConanFile):
    """test_package for tinyssh — CLI tool, runs tinysshd to verify it works."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f"{bash} test.sh", env="conanrun")
