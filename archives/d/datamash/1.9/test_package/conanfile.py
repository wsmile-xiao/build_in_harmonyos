#!/usr/bin/env python3
"""Consumer tests for the packaged GNU datamash commands."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run


class DatamashTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Skipping runtime tests while cross-building")
            return

        package = self.dependencies["datamash"].package_folder
        datamash = os.path.join(package, "bin", "datamash")
        decorate = os.path.join(package, "bin", "decorate")
        test_script = os.path.join(self.source_folder, "test.sh")
        requested_shell = os.environ.get("CONFIG_SHELL", "bash")
        shell = shutil.which(requested_shell)
        if shell is None:
            raise ConanInvalidConfiguration(
                f"Unable to locate bash executable: {requested_shell}"
            )
        self.run(
            f"{shlex.quote(shell)} {shlex.quote(test_script)} "
            f"{shlex.quote(datamash)} {shlex.quote(decorate)}",
            env="conanrun",
        )
