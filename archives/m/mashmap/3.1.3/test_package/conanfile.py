#!/usr/bin/env python3
"""Conan test package for mashmap 3.1.3.

MashMap has no library API: the recipe ships two command line tools, so the
consumer test drives the packaged binaries instead of linking a helper against
them.  ``test_mashmap.py`` holds the checks themselves and is invoked through
``self.run()`` so the Conan test stage really executes them.
"""

import os
import platform
import shutil
import sys
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv

_NATIVE_MACHINES = ("aarch64", "arm64")
_COMMANDS = ("mashmap", "mashmap-align")


class MashmapTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _emulation_needed(self):
        """True when the packaged binaries cannot run on this build machine.

        `cross_building()` reports False for this project because the OHOS
        profile is supplied as both -pr:h and -pr:b, so Conan sees identical
        host and build settings.  The build machine CPU is the reliable signal.
        """
        return cross_building(self) or platform.machine().lower() not in _NATIVE_MACHINES

    def _runner_prefix(self):
        if not self._emulation_needed():
            return ""
        qemu = shutil.which("qemu-aarch64")
        if not qemu:
            raise ConanInvalidConfiguration(
                "qemu-aarch64 is required to execute OpenHarmony binaries on this host"
            )
        return qemu

    def test(self):
        # In a test_package self.package_folder is the test package itself, so
        # the dependency's package folder has to be resolved explicitly.
        dependency = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(dependency.package_folder, dependency.cpp_info.bindirs[0])
        for command in _COMMANDS:
            command_path = os.path.join(bindir, command)
            if not os.path.isfile(command_path):
                raise ConanInvalidConfiguration(f"packaged command is missing: {command_path}")

        script = os.path.join(self.recipe_folder, "test_mashmap.py")
        prefix = self._runner_prefix()
        quoted = f'"{prefix}"' if prefix else '""'
        # The generated data set is several megabytes; keep it in the system
        # scratch area (honouring TMPDIR) so nothing lands in the archive tree.
        workdir = tempfile.mkdtemp(prefix="mashmap-test-")
        try:
            self.run(
                f'"{sys.executable}" "{script}" --bindir "{bindir}"'
                f' --workdir "{workdir}" --runner {quoted}',
                env="conanrun",
            )
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
