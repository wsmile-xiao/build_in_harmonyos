import os

from conan import ConanFile


class ApiSanityCheckerTestConan(ConanFile):
    """test_package for api-sanity-checker — runs --version to verify the tool."""
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
