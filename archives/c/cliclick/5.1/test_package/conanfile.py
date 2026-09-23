#!/usr/bin/env python3
"""Consumer test for the packaged cliclick executable (OHOS port)."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run


class CliclickTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test.sh"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dependency = self.dependencies[self.tested_reference_str]
        if not dependency.cpp_info.bindirs:
            raise ConanInvalidConfiguration(
                "Packaged executable directory is not declared"
            )
        binary = os.path.join(
            dependency.package_folder,
            dependency.cpp_info.bindirs[0],
            "cliclick",
        )
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration(
                f"Packaged executable is missing: {binary}"
            )

        if not can_run(self):
            self.output.info("cross-building: packaged CLI checks require target execution")
            return

        script = os.path.join(self.source_folder, "test.sh")
        self.run(
            shlex.join(["sh", script, binary, str(dependency.ref.version)]),
            env="conanrun",
        )
