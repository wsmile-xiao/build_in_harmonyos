import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run


class RBaseTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        dependency = self.dependencies.host[self.tested_reference_str]
        package_folder = dependency.package_folder
        runner = os.path.join(self.source_folder, "run_test.sh")
        script = os.path.join(self.source_folder, "test_r.R")
        moved = os.path.join(self.build_folder, "moved-r-base")
        command = "/system/bin/sh " + " ".join(
            shlex.quote(value)
            for value in (runner, package_folder, moved, script)
        )
        self.run(command, env=None)
