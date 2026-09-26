#!/usr/bin/env python3
"""Run the shortuuid library and CLI consumers from the Conan package."""

import os
import shlex
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class ShortuuidTestConan(ConanFile):
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
            raise ConanException("shortuuid target runtime is unavailable")
        package_folder = self.dependencies["shortuuid"].package_folder
        script = os.path.join(self.source_folder, "functional.py")
        report = os.path.join(self.build_folder, "functional-results.json")
        command = [sys.executable, script, package_folder, report]
        quoted = (subprocess.list2cmdline(command) if os.name == "nt"
                  else shlex.join(command))
        self.run(quoted, env="conanrun")
