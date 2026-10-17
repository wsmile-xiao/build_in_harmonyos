import os

from conan import ConanFile


class CheckinstallTestConan(ConanFile):
    """test_package for checkinstall — runs --version smoke tests for the tool
    and verifies the installwatch LD_PRELOAD library loads (dlopen)."""
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
