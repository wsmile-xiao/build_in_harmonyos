#!/usr/bin/env python3
"""Conan test_package for pick 2.0.2."""
from pathlib import Path
import shlex
import sys

from conan import ConanFile
from conan.tools.build import cross_building


class PickTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        exe = Path(self.dependencies["pick"].package_folder) / "bin" / "pick"
        if not exe.is_file():
            raise RuntimeError(f"missing pick executable: {exe}")
        if cross_building(self):
            self.output.info("cross-building: verified package executable exists")
            return
        test_script = Path(self.source_folder) / "test_pick.py"
        self.run(
            "{} {} {}".format(
                shlex.quote(sys.executable),
                shlex.quote(str(test_script)),
                shlex.quote(str(exe)),
            ),
            env="conanrun",
        )
