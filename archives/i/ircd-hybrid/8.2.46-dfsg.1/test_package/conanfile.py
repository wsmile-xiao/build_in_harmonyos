#!/usr/bin/env python3
"""Consumer-side tests for the packaged ircd-hybrid daemon."""

import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class IrCdHybridTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration(
                "ircd-hybrid's consumer runtime test must run on HarmonyOS"
            )

        package = self.dependencies["ircd-hybrid"].package_folder
        binary = os.path.join(package, "bin", "ircd")
        modules = os.path.join(package, "lib", "ircd-hybrid", "modules")
        script = os.path.join(self.source_folder, "test_harmonyos_runtime.py")
        command = "%s %s %s %s" % (
            shlex.quote(sys.executable),
            shlex.quote(script),
            shlex.quote(binary),
            shlex.quote(modules),
        )
        self.run(command, cwd=self.source_folder, env="conanrun")
