import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run


class AcepackTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        dependency = self.dependencies.host[self.tested_reference_str]
        rbase = self.dependencies.host["r-base"]
        runner = os.path.join(self.source_folder, "run_test.sh")
        test_script = os.path.join(self.source_folder, "test_acepack.R")
        rscript = os.path.join(rbase.package_folder, "bin", "Rscript")
        command = "/system/bin/sh " + " ".join(
            shlex.quote(value)
            for value in (
                runner,
                dependency.package_folder,
                rscript,
                test_script,
            )
        )
        self.run(command, env=None)
