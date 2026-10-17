#!/usr/bin/env python3
"""Consumer test for nagios-plugins 2.5."""

import os
import shlex
import shutil

from conan import ConanFile


class NagiosPluginsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["nagios-plugins"]
        bin_dir = os.path.join(package.package_folder, "bin")
        script = os.path.join(self.recipe_folder, "test.sh")

        shell = (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or shutil.which("sh")
            or "/system/bin/sh"
        )
        self.run(
            "{} {} {}".format(
                shlex.quote(shell),
                shlex.quote(script),
                shlex.quote(bin_dir),
            ),
            env="conanrun",
        )
