import os

from conan import ConanFile


class EdlinTestConan(ConanFile):
    """test_package for the edlin executable — runs test.sh which drives the
    editor through stdin (insert lines, save with E, verify file contents)."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # E087: HMDFS strips the exec bit from the checked-out script; run it
        # through /system/bin/sh (absolute path: conanrun PATH has no shell).
        self.run("/system/bin/sh ./test.sh", env="conanrun")
