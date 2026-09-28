import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run


class SchedtoolTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def configure(self):
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def test(self):
        if not can_run(self):
            raise ConanInvalidConfiguration("schedtool functional tests must run on the target")
        dependency = self.dependencies["schedtool"]
        binary = os.path.join(dependency.package_folder, "bin", "schedtool")
        test = os.path.join(self.source_folder, "test_schedtool.py")
        report = os.path.join(self.build_folder, "schedtool-test-results.json")
        command = [sys.executable, test, "--binary", binary, "--report", report]
        self.run(" ".join(shlex.quote(arg) for arg in command), env="conanrun")
