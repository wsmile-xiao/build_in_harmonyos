#!/usr/bin/env python3
"""Consumer test for the packaged ncmpc executable."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class NcmpcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info(
                "Skipping ncmpc consumer execution during cross build"
            )
            return

        shell = os.environ.get("CONFIG_SHELL")
        if not shell or not os.path.isfile(shell):
            shell = "/data/service/hnp/bin/bash"
        if not os.path.isfile(shell):
            shell = "bash" if os.name == "posix" else "sh"
        self.run(f'"{shell}" test_ncmpc.sh', env="conanrun")
