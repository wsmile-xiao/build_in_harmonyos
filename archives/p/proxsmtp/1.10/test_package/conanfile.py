"""Exercise the installed daemon against a loopback SMTP server."""

import os
import shlex

from conan import ConanFile


class ProxsmtpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "test_smtp.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        binary = os.path.join(
            self.dependencies["proxsmtp"].package_folder, "bin", "proxsmtpd"
        )
        script = os.path.join(self.source_folder, "test_smtp.py")
        self.run(
            "python3 {} {}".format(shlex.quote(script), shlex.quote(binary)),
            cwd=self.build_folder,
        )
