import os

from conan import ConanFile


class BashdbTestConan(ConanFile):
    """test_package for bashdb — runs test.sh which invokes the real bashdb
    debugger on a sample bash script (not a hollow print test)."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Run the actual smoke test via bash (explicit interpreter)
        self.run("bash test.sh", env="conanrun")
