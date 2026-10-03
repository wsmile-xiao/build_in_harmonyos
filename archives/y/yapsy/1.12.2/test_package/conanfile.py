"""Run Yapsy's upstream suite against the packaged Python modules."""

import os
import shlex
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class YapsyTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "functional.py", "upstream_tests/**"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            raise ConanException("the target Python runtime is unavailable")
        package_folder = self.dependencies["yapsy"].package_folder
        upstream_tests = os.path.join(self.source_folder, "upstream_tests")
        report = os.path.join(self.build_folder, "functional-results.json")
        command = [sys.executable, os.path.join(self.source_folder, "functional.py"),
                   package_folder, upstream_tests, report]
        quoted = (subprocess.list2cmdline(command) if os.name == "nt"
                  else shlex.join(command))
        self.run(quoted, env="conanrun")
