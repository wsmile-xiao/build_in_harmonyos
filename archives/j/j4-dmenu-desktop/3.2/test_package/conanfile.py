#!/usr/bin/env python3
"""Consumer-side verification for the installed j4-dmenu-desktop command."""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class J4DmenuDesktopTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            script = os.path.join(self.source_folder, "test.sh")
            bash = (os.environ.get("CONFIG_SHELL") or shutil.which("bash") or
                    "/storage/Users/currentUser/usr/local/bin/bash")
            self.run(f'"{bash}" "{script}"', env="conanrun")
