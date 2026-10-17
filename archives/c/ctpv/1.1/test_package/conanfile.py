#!/usr/bin/env python3
"""Consumer tests for the packaged ctpv command suite."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run


class CtpvTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            raise ConanInvalidConfiguration(
                "ctpv target execution is mandatory; configure an OHOS AArch64 runner"
            )

        package = self.dependencies["ctpv"].package_folder
        script = os.path.join(self.source_folder, "test_ctpv.sh")
        self.run(
            "bash {} {}".format(
                shlex.quote(script), shlex.quote(package)
            ),
            env="conanrun",
        )
