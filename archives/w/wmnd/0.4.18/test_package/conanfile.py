#!/usr/bin/env python3
"""Consumer test for the packaged wmnd executable.

Upstream 0.4.18 ships no automated test suite, so this test drives the
installed binary from a consumer's point of view instead of linking a library:
see test_wmnd.sh (scenarios and assertions) and MANIFEST.yml (upstream test
audit).
"""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class WmndTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "test_wmnd.sh"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning("Cannot run wmnd in this environment")
            return

        executable = os.path.join(
            self.dependencies["wmnd"].package_folder, "bin", "wmnd"
        )
        script = os.path.join(self.source_folder, "test_wmnd.sh")
        shell = shutil.which("sh") or "/system/bin/sh"
        self.run(f'"{shell}" "{script}" "{executable}"', env="conanrun")
