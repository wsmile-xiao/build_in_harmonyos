#!/usr/bin/env python3
"""Conan consumer test for the packaged Stalwart CLI."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class StalwartTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            self.output.info("Cross-built executable; runtime requires an OHOS runner")
            return
        executable = os.path.join(
            self.dependencies["stalwart"].package_folder, "bin", "stalwart-cli"
        )
        if not os.path.isfile(executable):
            raise RuntimeError(f"Packaged executable is missing: {executable}")
        script = os.path.join(self.source_folder, "test_stalwart.py")
        python = os.environ.get("PYTHON") or shutil.which("python3")
        if not python:
            raise RuntimeError("python3 is required to run test_package")
        command = " ".join(
            shlex.quote(argument) for argument in (python, script, executable)
        )
        self.run(command, env="conanrun")
