#!/usr/bin/env python3
"""Consumer test for the packaged djstub 0.7 commands."""

import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run


class DjstubTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            script = os.path.join(self.source_folder, "test.sh")
            default_shell = (
                "/data/service/hnp/bin/bash"
                if str(self.settings.os) == "OHOS"
                else "bash"
            )
            shell = os.environ.get("CONFIG_SHELL", default_shell)
            self.run(
                f"{shlex.quote(shell)} {shlex.quote(script)}", env="conanrun"
            )
