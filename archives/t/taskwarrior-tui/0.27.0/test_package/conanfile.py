#!/usr/bin/env python3
"""Consumer test for taskwarrior-tui — verifies the packaged binary runs."""

from conan import ConanFile
from conan.tools.build import can_run


class TaskwarriorTuiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-build: runtime test deferred to OHOS/shadow CI")
            return
        self.run("taskwarrior-tui --version", env=["conanrun"])
