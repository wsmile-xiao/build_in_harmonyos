import os

from conan import ConanFile


class SedTestConan(ConanFile):
    """test_package for GNU sed 4.9 — verifies binary runs and works correctly."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the absolute path to the packaged sed binary
        # This ensures the L1e negative test (R34) genuinely detects
        # dependency on the package — system toybox sed won't be used.
        sed_bin = os.path.join(self.dependencies["sed"].package_folder,
                                "bin", "sed")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'export SED_BIN="{sed_bin}" && {bash} test.sh',
                 env="conanrun")
