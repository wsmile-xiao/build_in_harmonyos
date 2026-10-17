#!/usr/bin/env python3
"""Consumer test for the packaged Smaller C toolchain."""

import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run


class SmallerCTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info(
                "cross build: packaged tools exist; functional execution is deferred to OHOS"
            )
            return

        script = os.path.join(self.source_folder, "test.sh")
        default_shell = (
            "/data/service/hnp/bin/bash"
            if str(self.settings.os) == "OHOS"
            else "bash"
        )
        shell = os.environ.get("CONFIG_SHELL", default_shell)
        self.run(f"{shlex.quote(shell)} {shlex.quote(script)}", env="conanrun")
