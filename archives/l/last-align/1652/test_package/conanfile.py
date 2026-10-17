import os

from conan import ConanFile


class LastAlignTestConan(ConanFile):
    """test_package for last-align — runs lastdb+lastal end-to-end smoke test."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    exports_sources = "test.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
