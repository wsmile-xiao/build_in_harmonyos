"""Test the installed mboxgrep executable outside its source tree."""

import os
import shlex

from conan import ConanFile


class MboxgrepTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "test_mailbox.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        binary = os.path.join(
            self.dependencies["mboxgrep"].package_folder, "bin", "mboxgrep"
        )
        script = os.path.join(self.source_folder, "test_mailbox.py")
        self.run(
            "python3 {} {}".format(shlex.quote(script), shlex.quote(binary)),
            cwd=self.build_folder,
        )
