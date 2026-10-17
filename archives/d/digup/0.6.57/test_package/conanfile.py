#!/usr/bin/env python3
"""Consumer test for the packaged digup executable."""

import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class DigupTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self, src_folder=".")

    def test(self):
        if not can_run(self):
            self.output.warning("Skipping execution because the target cannot run here")
            return

        # OHOS /system/bin/sh cannot be assumed to run the packaged ELF; the
        # profile injects CONFIG_SHELL pointing at the device bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f"{shlex.quote(bash)} {shlex.quote(script)}", env="conanrun")
