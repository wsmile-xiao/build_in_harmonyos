#!/usr/bin/env python3
"""Consumer test for iverilog: compiles and simulates a tiny Verilog design."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class IverilogTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Cross builds cannot execute aarch64 binaries; the WSL profile also sets
        # tools.build:skip_test=True. Native CI runs the real end-to-end test.
        if not can_run(self) or self.conf.get("tools.build:skip_test", default=False):
            self.output.info("skip consumer run: cross build / tools.build:skip_test")
            return
        root = (self.dependencies[self.tested_reference_str].package_folder or "").replace("\\", "/")
        script = os.path.join(self.recipe_folder, "test.sh")
        self.run('bash "%s" "%s"' % (script, root), env="conanrun")
