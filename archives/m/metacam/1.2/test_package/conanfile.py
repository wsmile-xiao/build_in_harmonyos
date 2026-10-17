"""Exercise the installed metacam executable with deterministic EXIF data."""

import os
import shlex
import sys

from conan import ConanFile


class MetacamTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "test_metacam.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        binary = os.path.join(
            self.dependencies["metacam"].package_folder, "bin", "metacam"
        )
        script = os.path.join(self.source_folder, "test_metacam.py")
        self.run(
            "{} {} {}".format(
                shlex.quote(sys.executable),
                shlex.quote(script),
                shlex.quote(binary),
            ),
            cwd=self.build_folder,
        )
