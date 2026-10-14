#!/usr/bin/env python3
"""Consumer test for the packaged SciTE application."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class SciteTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        tested_name = self.tested_reference_str.split("/")[0]
        package = self.dependencies[tested_name].package_folder
        run_binary = "1" if can_run(self) else "0"
        shell = os.environ.get("CONFIG_SHELL", "bash")
        script = os.path.join(self.source_folder, "test_scite.sh")
        # The script checks the installed SciTE binary, its component
        # libraries and the global properties file; it executes the
        # binary only when the target is runnable (has a display).
        self.run(
            f'"{shell}" "{script}" "{package}" "{run_binary}"',
            env="conanrun",
        )
