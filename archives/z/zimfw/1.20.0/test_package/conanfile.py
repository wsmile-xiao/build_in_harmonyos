import os

from conan import ConanFile


class ZimfwTestConan(ConanFile):
    """test_package for zimfw — runs test.sh which verifies the package."""
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: test.sh substantively tests the package (file existence,
        # content checks, zsh -n syntax validation)
        dep = self.dependencies["zimfw"]
        os.environ["PACKAGE_ROOT"] = dep.package_folder
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
