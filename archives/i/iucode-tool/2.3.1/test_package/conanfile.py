#!/usr/bin/env python3
"""Conan test_package for the iucode-tool executable."""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class IucodeToolTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["iucode-tool"]
        binary = os.path.join(dep.package_folder, "bin", "iucode_tool")
        bash = (
            os.environ.get("CONFIG_SHELL")
            or os.environ.get("SHELL")
            or shutil.which("bash")
            or "/data/service/hnp/bin/bash"
        )
        self.run(
            f'cd "{self.source_folder}" && '
            f'IUCODE_TOOL_BIN="{binary}" "{bash}" test.sh',
            env="conanrun",
        )
