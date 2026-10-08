#!/usr/bin/env python3
"""Run a consumer against the packaged yattag modules."""

import os
import shlex
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class YattagTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "functional.py", "ohos_document_roundtrip.py"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            raise ConanException("yattag target Python runtime is unavailable")
        package_folder = self.dependencies["yattag"].package_folder
        scripts = [("functional.py", [package_folder])]
        if str(self.settings.os) == "OHOS":
            self.output.info("Running the OHOS document consumer")
            os.makedirs(self.build_folder, exist_ok=True)
            scripts.append(("ohos_document_roundtrip.py",
                            [package_folder, self.build_folder]))
        for name, arguments in scripts:
            script = os.path.join(self.source_folder, name)
            command = [sys.executable, script, *arguments]
            quoted = (subprocess.list2cmdline(command) if os.name == "nt"
                      else shlex.join(command))
            self.run(quoted, env="conanrun")
