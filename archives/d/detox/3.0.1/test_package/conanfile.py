#!/usr/bin/env python3
"""Consumer tests for the packaged detox commands."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run


class DetoxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _bash(self):
        requested = os.environ.get("CONFIG_SHELL", "bash")
        shell = shutil.which(requested)
        if shell is None and os.path.isfile(requested):
            shell = requested
        if shell is None:
            raise ConanInvalidConfiguration(
                f"Unable to locate bash executable: {requested}"
            )
        return shell

    def test(self):
        if not can_run(self):
            self.output.info("Skipping runtime tests while cross-building")
            return

        package = self.dependencies["detox"].package_folder
        detox = os.path.join(package, "bin", "detox")
        inline_detox = os.path.join(package, "bin", "inline-detox")
        shell = self._bash()

        general_test = os.path.join(self.source_folder, "test_detox.sh")
        self.run(
            f"{shlex.quote(shell)} {shlex.quote(general_test)} "
            f"{shlex.quote(detox)} {shlex.quote(inline_detox)}",
            env="conanrun",
        )

        if str(self.settings.os) == "OHOS":
            ohos_test = os.path.join(self.source_folder, "test_ohos_tmpdir.sh")
            self.run(
                f"{shlex.quote(shell)} {shlex.quote(ohos_test)} "
                f"{shlex.quote(detox)}",
                env="conanrun",
            )
