import os

from conan import ConanFile


class Mp3wrapTestConan(ConanFile):
    """test_package for mp3wrap executable — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # test.sh is POSIX sh compatible (no bashisms).
        # On OHOS /bin/sh is mksh which handles this test script correctly.
        self.run("/bin/sh test.sh", env="conanrun")
