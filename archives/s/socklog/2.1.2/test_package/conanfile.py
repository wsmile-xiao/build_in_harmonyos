#!/usr/bin/env python3
"""Conan test_package for socklog 2.1.2."""
import os
from pathlib import Path

from conan import ConanFile
from conan.tools.build import cross_building


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    commands = ("socklog", "socklog-check", "socklog-conf", "tryto", "uncat")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # cpp_info.bindirs is already resolved to an absolute path by Conan, so
        # the packaged programs are addressed directly. VirtualRunEnv is not
        # used: on this platform it emits an env script with no PATH export, so
        # a PATH lookup would report every program missing (seen in verify v2).
        bindirs = self.dependencies["socklog"].cpp_info.bindirs
        if not bindirs:
            raise RuntimeError("package declares no bindirs")
        bindir = Path(bindirs[0])
        for program in self.commands:
            path = bindir / program
            if not path.is_file():
                raise RuntimeError("missing packaged executable: {}".format(path))
        if cross_building(self):
            self.output.info("cross-building: verified package executables exist")
            return
        script = os.path.join(self.recipe_folder, "test_socklog.sh")
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("'{}' '{}' '{}'".format(shell, script, str(bindir)))
