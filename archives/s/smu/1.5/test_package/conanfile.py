import os
import shlex
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class SmuTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "functional.py"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            self.output.warning("smu functional tests not run: target is not executable on this host")
            return
        package = self.dependencies["smu"].package_folder
        binary = os.path.join(package, "bin", "smu")
        command = [sys.executable, os.path.join(self.source_folder, "functional.py"), binary,
                   "--report-dir", os.path.join(self.build_folder, "functional-results")]
        self.run(" ".join(shlex.quote(arg) for arg in command), env="conanrun")
