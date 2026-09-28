"""Exercise the packaged tinyirc against a local IRC protocol stub."""

import os
import shlex

from conan import ConanFile


class TinyircTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    exports_sources = "test_fake_irc.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        binary = os.path.join(
            self.dependencies["tinyirc"].package_folder, "bin", "tinyirc"
        )
        script = os.path.join(self.source_folder, "test_fake_irc.py")
        self.run(
            "python3 {} {}".format(shlex.quote(script), shlex.quote(binary)),
            env="conanrun",
        )
