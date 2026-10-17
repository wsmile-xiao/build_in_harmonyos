import os

from conan import ConanFile


class CatdocTestConan(ConanFile):
    """test_package for catdoc executables — runs test.sh which invokes the binaries."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Use sh (POSIX) to run the test script; avoid hardcoded bash path.
        # The script uses #!/bin/sh and only POSIX features.
        self.run("sh test.sh", env="conanrun")
