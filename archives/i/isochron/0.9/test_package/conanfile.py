import os

from conan import ConanFile


class IsochronTestConan(ConanFile):
    """test_package for isochron — runs test.sh which invokes the packaged
    binary through the conanrun environment (resolves the packaged libmnl
    dependency at runtime)."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
