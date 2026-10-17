#!/usr/bin/env python3
"""Runtime consumer test for the packaged GROMACS command-line tool."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class GromacsTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        gmx = os.path.join(
            self.dependencies["gromacs"].package_folder, "bin", "gmx"
        )
        if not os.path.isfile(gmx):
            raise RuntimeError(f"Missing packaged gmx executable: {gmx}")
        if not can_run(self):
            self.output.info("Cross-building: packaged gmx layout check passed")
            return
        python = shutil.which("python3") or "python3"
        script = os.path.join(self.source_folder, "test.py")
        self.run(
            f"{shlex.quote(python)} {shlex.quote(script)} {shlex.quote(gmx)}",
            env="conanrun",
        )
