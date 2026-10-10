"""Exercise the installed pwnat executable without opening raw sockets."""

import os
import shlex

from conan import ConanFile


class PwnatTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies[self.tested_reference_str].package_folder
        verifier = os.path.join(self.source_folder, "verify_help.py")
        self.run(" ".join(shlex.quote(arg) for arg in (
            "python3", verifier, package,
        )), env="conanrun")
